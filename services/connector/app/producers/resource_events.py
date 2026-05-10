"""Resource event producer — Confluent Avro with JSON fallback.

Serialization strategy:
  1. If Schema Registry is reachable and fastavro is installed:
     → Confluent Avro wire format (magic byte + schema ID + Avro binary)
  2. Otherwise:
     → Plain UTF-8 JSON (development / Schema Registry unavailable)

All events include the mandatory envelope fields required by the spec:
  organization_id, account_id, provider, timestamp, correlation_id
"""

import json
import logging
import uuid
from typing import Any

from aiokafka import AIOKafkaProducer

from cloudvisor_types.models import CloudProvider, CloudResource

from ..core.time_utils import utcnow
from ..metrics.prometheus import ConnectorMetrics

logger = logging.getLogger(__name__)


class ResourceEventProducer:
    """Produces resource discovery events to Kafka with Avro serialization."""

    def __init__(
        self,
        bootstrap_servers: str,
        topic_prefix: str = "resource",
        schema_registry_url: str = "",
    ):
        self._bootstrap_servers = bootstrap_servers
        self._topic_prefix = topic_prefix
        self._schema_registry_url = schema_registry_url
        self._producer: AIOKafkaProducer | None = None
        self._serializer: Any | None = None  # AvroSerializer | None

    async def start(self) -> None:
        """Initialize the Kafka producer and Avro serializer."""
        # ── Avro serializer ───────────────────────────────────────────────────
        if self._schema_registry_url:
            try:
                from .avro_serializer import AvroSerializer
                self._serializer = AvroSerializer(self._schema_registry_url)
                avro_ok = await self._serializer.initialize()
                if avro_ok:
                    logger.info(
                        f"Avro serialization enabled "
                        f"(Schema Registry: {self._schema_registry_url})"
                    )
                else:
                    logger.warning(
                        "Avro serialization unavailable — using JSON fallback"
                    )
                    self._serializer = None
            except Exception as e:
                logger.warning(f"Avro serializer init failed: {e} — using JSON fallback")
                self._serializer = None
        else:
            logger.info(
                "KAFKA_SCHEMA_REGISTRY_URL not set — using JSON serialization. "
                "Set it to enable Avro."
            )

        # ── Kafka producer ────────────────────────────────────────────────────
        # Use raw bytes serializer — we handle serialization ourselves so we can
        # switch between Avro and JSON without changing the producer config.
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=None,   # we serialize manually
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retry_backoff_ms=500,
                request_timeout_ms=30000,
            )
            await self._producer.start()
            mode = "Avro" if self._serializer else "JSON"
            logger.info(f"Kafka producer started (serialization={mode})")
        except Exception as e:
            logger.warning(f"Failed to create Kafka producer: {e}")
            self._producer = None

    async def stop(self) -> None:
        """Close the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            self._producer = None

    # ── Serialization ─────────────────────────────────────────────────────────

    def _serialize(self, topic_suffix: str, event: dict[str, Any]) -> bytes:
        """Serialize an event dict to bytes (Avro or JSON)."""
        if self._serializer is not None:
            try:
                return self._serializer.serialize(topic_suffix, event)
            except Exception as e:
                logger.warning(
                    f"Avro serialization failed for {topic_suffix}: {e} — "
                    "falling back to JSON for this message"
                )
        return json.dumps(event, default=str).encode("utf-8")

    # ── Topic helpers ─────────────────────────────────────────────────────────

    def _get_topic(self, topic_suffix: str) -> str:
        # resource.discovered, resource.updated, resource.deleted
        # connector.sync_started, connector.sync_finished, connector.health_changed
        if topic_suffix in ("sync_started", "sync_finished", "health_changed"):
            return f"connector.{topic_suffix}"
        return f"{self._topic_prefix}.{topic_suffix}"

    # ── Public emit methods ───────────────────────────────────────────────────

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
            "provider": resource.provider.value if hasattr(resource.provider, "value") else str(resource.provider),
            "region": resource.region,
            "resource_type": resource.resource_type,
            "cloud_resource_id": resource.cloud_resource_id,
            "name": resource.name,
            "tags": {str(k): str(v) for k, v in (resource.tags or {}).items()},
            "is_public": bool(resource.is_public),
            "environment": resource.environment.value if hasattr(resource.environment, "value") else str(resource.environment),
            "timestamp": utcnow().isoformat(),
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
            "provider": resource.provider.value if hasattr(resource.provider, "value") else str(resource.provider),
            "region": resource.region,
            "resource_type": resource.resource_type,
            "cloud_resource_id": resource.cloud_resource_id,
            "name": resource.name,
            "tags": {str(k): str(v) for k, v in (resource.tags or {}).items()},
            "is_public": bool(resource.is_public),
            "environment": resource.environment.value if hasattr(resource.environment, "value") else str(resource.environment),
            "timestamp": utcnow().isoformat(),
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
            "timestamp": utcnow().isoformat(),
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
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "discovered": 0,
            "updated": 0,
            "deleted": 0,
            "errors": 0,
            "duration_seconds": 0.0,
            "timestamp": utcnow().isoformat(),
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
            "status": "completed" if errors == 0 else "partial" if discovered > 0 else "failed",
            "correlation_id": correlation_id,
            "discovered": int(discovered),
            "updated": int(updated),
            "deleted": int(deleted),
            "errors": int(errors),
            "duration_seconds": float(duration_seconds),
            "timestamp": utcnow().isoformat(),
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
            "resource_count": int(resource_count),
            "timestamp": utcnow().isoformat(),
        }
        await self._send_event("health_changed", account_id, event)

    # ── Internal send ─────────────────────────────────────────────────────────

    async def _ensure_producer(self) -> bool:
        """Lazily (re)connect the Kafka producer if it's not running."""
        if self._producer is not None:
            return True
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=None,
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retry_backoff_ms=500,
                request_timeout_ms=30000,
            )
            await self._producer.start()
            mode = "Avro" if self._serializer else "JSON"
            logger.info(f"Kafka producer reconnected (serialization={mode})")
            return True
        except Exception as e:
            logger.warning(f"Kafka producer reconnect failed: {e}")
            self._producer = None
            return False

    async def _send_event(
        self, topic_suffix: str, key: str, event: dict[str, Any]
    ) -> None:
        """Serialize and send an event to Kafka, reconnecting if needed."""
        # Try to ensure producer is alive
        if not await self._ensure_producer():
            logger.warning(
                f"Kafka producer unavailable — skipping event: "
                f"{event.get('event_type')}"
            )
            return

        topic = self._get_topic(topic_suffix)
        payload = self._serialize(topic_suffix, event)

        try:
            await self._producer.send_and_wait(
                topic,
                key=key,
                value=payload,
            )
            # Record metric for spec observability requirement (§2.1)
            try:
                ConnectorMetrics.record_event_published(
                    event_type=event.get("event_type", topic_suffix),
                    provider=str(event.get("provider", "unknown")),
                )
            except Exception:
                # Never let metrics fail a publish
                pass
            logger.debug(
                f"Published {event.get('event_type')} to {topic} "
                f"({len(payload)} bytes, "
                f"{'avro' if self._serializer else 'json'})"
            )
        except Exception as e:
            logger.error(f"Failed to publish event to {topic}: {e}")
            # Mark producer as dead so next call reconnects
            try:
                await self._producer.stop()
            except Exception:
                pass
            self._producer = None


class HealthEventProducer:
    """Thin wrapper that delegates health events to ResourceEventProducer."""

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
        await self._producer.emit_health_changed(
            account_id=account_id,
            organization_id=organization_id,
            provider=provider,
            previous_status=previous_status,
            new_status=new_status,
            error_message=error_message,
            resource_count=resource_count,
        )
