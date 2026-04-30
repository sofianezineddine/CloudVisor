"""Kafka producer for policy events — uses aiokafka (async)."""

import json
import logging
from datetime import datetime
from typing import Any

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


class PolicyEventProducer:
    """Produces policy evaluation events to Kafka."""

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
            logger.info("Policy Kafka producer started")
        except Exception as e:
            logger.warning(f"Failed to create Policy Kafka producer: {e}")
            self._producer = None

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            self._producer = None

    async def emit_finding(
        self,
        rule_id: str,
        resource_id: str,
        organization_id: str,
        severity: str,
        finding_data: dict[str, Any],
    ) -> None:
        """Emit a finding.raw event to the Alert service."""
        event = {
            "event_type": "finding.raw",
            "rule_id": rule_id,
            "resource_id": resource_id,
            "organization_id": organization_id,
            "severity": severity,
            **finding_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send("finding.raw", resource_id, event)

    async def emit_rule_updated(
        self,
        rule_id: str,
        organization_id: str | None,
        action: str,
    ) -> None:
        """Emit a rule.updated event."""
        event = {
            "event_type": "rule.updated",
            "rule_id": rule_id,
            "organization_id": organization_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send("rule.updated", rule_id, event)

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
