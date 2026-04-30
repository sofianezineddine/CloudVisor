"""Audit event producer for Kafka — uses aiokafka (async)."""

import json
import logging
from datetime import datetime
from typing import Any

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


class AuditEventProducer:
    """Produces audit and org lifecycle events to Kafka."""

    def __init__(self, bootstrap_servers: str, topic: str = "audit.events"):
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Initialize async Kafka producer."""
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retry_backoff_ms=500,
            )
            await self._producer.start()
            logger.info("Audit Kafka producer started")
        except Exception as e:
            logger.warning(f"Failed to start Kafka producer (non-fatal): {e}")
            self._producer = None

    async def stop(self) -> None:
        """Close async Kafka producer."""
        if self._producer:
            await self._producer.stop()
            self._producer = None

    async def emit_auth_event(
        self,
        organization_id: str,
        user_id: str | None,
        event_type: str,
        success: bool,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = {
            "event_type": event_type,
            "organization_id": organization_id,
            "user_id": user_id,
            "success": success,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send(event, key=user_id or organization_id)

    async def emit_authorization_event(
        self,
        organization_id: str,
        user_id: str,
        action: str,
        resource_type: str | None,
        resource_id: str | None,
        authorized: bool,
    ) -> None:
        event = {
            "event_type": "authorization.check",
            "organization_id": organization_id,
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "authorized": authorized,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send(event, key=user_id)

    async def emit_org_event(
        self,
        organization_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Emit org lifecycle events: org.created, org.plan_changed, org.deleted."""
        event = {
            "event_type": event_type,
            "organization_id": organization_id,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send(event, key=organization_id, topic=event_type)

    async def emit_api_key_event(
        self,
        organization_id: str,
        user_id: str,
        event_type: str,
        key_id: str,
    ) -> None:
        """Emit api_key.created / api_key.rotated / api_key.revoked."""
        event = {
            "event_type": event_type,
            "organization_id": organization_id,
            "user_id": user_id,
            "key_id": key_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send(event, key=user_id)

    async def _send(
        self,
        event: dict[str, Any],
        key: str | None = None,
        topic: str | None = None,
    ) -> None:
        if not self._producer:
            return
        try:
            await self._producer.send_and_wait(
                topic or self._topic,
                key=key,
                value=event,
            )
            logger.debug(f"Audit event published: {event.get('event_type')}")
        except Exception as e:
            logger.debug(f"Audit event publish failed (non-fatal): {e}")
