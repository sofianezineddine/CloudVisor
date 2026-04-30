"""Resource event producer - sends resource events to Kafka."""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from aiokafka import AIOKafkaProducer

from cloudvisor_types.models import CloudProvider, CloudResource

logger = logging.getLogger(__name__)


class ResourceEventProducer:
    """Produces resource discovery events to Kafka."""

    def __init__(
        self,
        bootstrap_servers: str,
        topic_prefix: str = "resource",
    ):
        self._bootstrap_servers = bootstrap_servers
        self._topic_prefix = topic_prefix
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Initialize the Kafka producer."""
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retry_backoff_ms=500,
                request_timeout_ms=30000,
            )
            await self._producer.start()
            logger.info("Kafka producer started")
        except Exception as e:
            logger.warning(f"Failed to create Kafka producer: {e}")
            self._producer = None

    async def stop(self) -> None:
        """Close the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            self._producer = None

    def _get_topic(self, topic_name: str) -> str:
        return f"{self._topic_prefix}.{topic_name}"

    async def emit_resource_discovered(
        self,
        resource: CloudResource,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a resource.discovered event."""
        event = {
            "event_type": "resource.discovered",
            "organization_id": resource.organization_id,
            "account_id": resource.account_id,
            "provider": resource.provider.value,
            "region": resource.region,
            "resource_type": resource.resource_type,
            "cloud_resource_id": resource.cloud_resource_id,
            "name": resource.name,
            "tags": resource.tags,
            "raw": resource.raw,
            "is_public": resource.is_public,
            "environment": resource.environment.value,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id or str(uuid.uuid4()),
        }
        await self._send_event("discovered", resource.cloud_resource_id, event)

    async def emit_resource_updated(
        self,
        resource: CloudResource,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a resource.updated event."""
        event = {
            "event_type": "resource.updated",
            "organization_id": resource.organization_id,
            "account_id": resource.account_id,
            "provider": resource.provider.value,
            "region": resource.region,
            "resource_type": resource.resource_type,
            "cloud_resource_id": resource.cloud_resource_id,
            "name": resource.name,
            "tags": resource.tags,
            "raw": resource.raw,
            "is_public": resource.is_public,
            "environment": resource.environment.value,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id or str(uuid.uuid4()),
        }
        await self._send_event("updated", resource.cloud_resource_id, event)

    async def emit_resource_deleted(
        self,
        cloud_resource_id: str,
        account_id: str,
        organization_id: str,
        provider: str,
        region: str,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a resource.deleted event."""
        event = {
            "event_type": "resource.deleted",
            "organization_id": organization_id,
            "account_id": account_id,
            "provider": provider,
            "region": region,
            "cloud_resource_id": cloud_resource_id,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id or str(uuid.uuid4()),
        }
        await self._send_event("deleted", cloud_resource_id, event)

    async def emit_sync_started(
        self,
        account_id: str,
        organization_id: str,
        provider: str,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a connector.sync_started event."""
        event = {
            "event_type": "connector.sync_started",
            "organization_id": organization_id,
            "account_id": account_id,
            "provider": provider,
            "status": "started",
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id or str(uuid.uuid4()),
        }
        await self._send_event("sync_started", account_id, event)

    async def emit_sync_finished(
        self,
        account_id: str,
        organization_id: str,
        provider: str,
        correlation_id: str,
        discovered: int = 0,
        updated: int = 0,
        deleted: int = 0,
        errors: int = 0,
        duration_seconds: float = 0.0,
    ) -> None:
        """Emit a connector.sync_finished event."""
        event = {
            "event_type": "connector.sync_finished",
            "organization_id": organization_id,
            "account_id": account_id,
            "provider": provider,
            "status": "completed" if errors == 0 else "failed",
            "correlation_id": correlation_id,
            "discovered": discovered,
            "updated": updated,
            "deleted": deleted,
            "errors": errors,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send_event("sync_finished", account_id, event)

    async def emit_health_changed(
        self,
        account_id: str,
        organization_id: str,
        provider: str,
        previous_status: str,
        new_status: str,
        error_message: str | None = None,
        resource_count: int = 0,
    ) -> None:
        """Emit a connector.health_changed event."""
        event = {
            "event_type": "connector.health_changed",
            "organization_id": organization_id,
            "account_id": account_id,
            "provider": provider,
            "previous_status": previous_status,
            "new_status": new_status,
            "error_message": error_message,
            "resource_count": resource_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._send_event("health_changed", account_id, event)

    async def _send_event(self, topic_suffix: str, key: str, event: dict[str, Any]) -> None:
        """Send an event to Kafka."""
        if not self._producer:
            logger.warning(
                f"Kafka producer not initialized, skipping event: {event.get('event_type')}"
            )
            return

        topic = self._get_topic(topic_suffix)

        try:
            await self._producer.send_and_wait(topic, key=key, value=event)
            logger.debug(f"Published event to {topic}: {event.get('event_type')}")
        except Exception as e:
            logger.error(f"Failed to publish event to {topic}: {e}")


class HealthEventProducer:
    """Produces connector health events to Kafka."""

    def __init__(self, producer: ResourceEventProducer):
        self._producer = producer

    async def emit_status_change(
        self,
        account_id: str,
        organization_id: str,
        provider: str,
        previous_status: str,
        new_status: str,
        error_message: str | None = None,
        resource_count: int = 0,
    ) -> None:
        """Emit health status change event."""
        await self._producer.emit_health_changed(
            account_id=account_id,
            organization_id=organization_id,
            provider=provider,
            previous_status=previous_status,
            new_status=new_status,
            error_message=error_message,
            resource_count=resource_count,
        )
