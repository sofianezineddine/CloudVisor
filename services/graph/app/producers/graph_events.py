"""Kafka producer for graph events."""

import json
import logging
from datetime import datetime
from typing import Any

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


class GraphEventProducer:
    """Produces graph events to Kafka."""

    def __init__(self, bootstrap_servers: str):
        self._bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                acks="all",
                retry_backoff_ms=500,
            )
            await self._producer.start()
            logger.info("Graph Kafka producer started")
        except Exception as e:
            logger.warning(f"Failed to start Graph Kafka producer: {e}")
            self._producer = None

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            self._producer = None

    async def emit_asset_created(self, asset_id: str, organization_id: str, **kwargs) -> None:
        event = {
            "event_type": "asset.created",
            "asset_id": asset_id,
            "organization_id": organization_id,
            **kwargs,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send("asset.created", asset_id, event)

    async def emit_asset_updated(self, asset_id: str, organization_id: str, **kwargs) -> None:
        event = {
            "event_type": "asset.updated",
            "asset_id": asset_id,
            "organization_id": organization_id,
            **kwargs,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send("asset.updated", asset_id, event)

    async def emit_asset_deleted(self, asset_id: str, organization_id: str) -> None:
        event = {
            "event_type": "asset.deleted",
            "asset_id": asset_id,
            "organization_id": organization_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send("asset.deleted", asset_id, event)

    async def emit_risk_score_changed(
        self, asset_id: str, organization_id: str, old_score: int, new_score: int
    ) -> None:
        event = {
            "event_type": "asset.risk_score_changed",
            "asset_id": asset_id,
            "organization_id": organization_id,
            "old_score": old_score,
            "new_score": new_score,
            "delta": new_score - old_score,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send("asset.risk_score_changed", asset_id, event)

    async def emit_relationship_changed(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        organization_id: str,
        action: str,  # "created" or "deleted"
    ) -> None:
        event = {
            "event_type": "asset.relationship_changed",
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": relationship_type,
            "organization_id": organization_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send("asset.relationship_changed", f"{source_id}-{target_id}", event)

    async def _send(self, topic: str, key: str, event: dict[str, Any]) -> None:
        if not self._producer:
            logger.debug(f"Kafka producer not available, skipping: {event.get('event_type')}")
            return
        try:
            await self._producer.send_and_wait(
                topic,
                key=key.encode("utf-8") if key else None,
                value=event,
            )
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
