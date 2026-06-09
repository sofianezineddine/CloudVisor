"""
Replay connector resources for a specific org into Kafka so the graph
service can ingest them.

Usage (inside cv-connector container):
  python replay_resources_to_graph.py <org_id>
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone

import asyncpg
from aiokafka import AIOKafkaProducer

ORG_ID = sys.argv[1] if len(sys.argv) > 1 else "df272fe5-a953-4092-8ab5-09762812e00b"
DB_URL = "postgresql://cvadmin:cvpassword@cv-postgres:5432/cloudvisor"
KAFKA = "cv-kafka:9092"
TOPIC = "resource.discovered"
BATCH = 100


async def main() -> None:
    print(f"Replaying resources for org: {ORG_ID}")

    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch(
        """
        SELECT cloud_resource_id, provider, account_id, region,
               resource_type, name, tags, is_public, environment,
               organization_id
        FROM connector_discovered_resources
        WHERE organization_id = $1
          AND freshness_state != 'deleted'
        ORDER BY first_seen_at
        """,
        ORG_ID,
    )
    await conn.close()
    print(f"Found {len(rows)} resources to replay")

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",
    )
    await producer.start()

    sent = 0
    for row in rows:
        tags = row["tags"] or {}
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = {}

        event = {
            "event_type": "resource.discovered",
            "organization_id": row["organization_id"],
            "account_id": row["account_id"],
            "provider": row["provider"],
            "region": row["region"] or "global",
            "resource_type": row["resource_type"],
            "cloud_resource_id": row["cloud_resource_id"],
            "name": row["name"],
            "tags": {str(k): str(v) for k, v in tags.items()},
            "is_public": bool(row["is_public"]),
            "environment": row["environment"] or "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": str(uuid.uuid4()),
        }
        await producer.send_and_wait(
            TOPIC,
            key=row["cloud_resource_id"],
            value=event,
        )
        sent += 1
        if sent % BATCH == 0:
            print(f"  Sent {sent}/{len(rows)}...")

    await producer.stop()
    print(f"Done — published {sent} resource.discovered events to Kafka")


asyncio.run(main())
