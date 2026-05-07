"""Kafka consumers for the Alert service.

Consumed topics (per spec §3.5):
  - finding.raw        → deduplicate + enrich + persist + route notifications
  - resource.updated   → check if any open findings for this resource should auto-resolve
  - resource.deleted   → auto-resolve all open findings for deleted resource

Malformed events are forwarded to the dead-letter topic `finding.raw.dlq`.
"""

import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

logger = logging.getLogger(__name__)

# Dead-letter topic for malformed finding.raw events
DLQ_TOPIC = "finding.raw.dlq"


class FindingEventConsumer:
    """
    Consumes finding.raw events from the Policy service.
    Validates schema, deduplicates, enriches, persists, and routes notifications.
    Malformed events are forwarded to finding.raw.dlq (dead-letter queue).
    """

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str = "cloudvisor-alert",
        session_factory: Any = None,
        redis_client: Any = None,
        kafka_producer: Any = None,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._session_factory = session_factory
        self._redis_client = redis_client
        self._kafka_producer = kafka_producer
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            "finding.raw",
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        logger.info("Finding event consumer started")

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
        logger.info("Finding event consumer stopped")

    async def run(self) -> None:
        if not self._consumer:
            return
        try:
            async for message in self._consumer:
                if not self._running:
                    break
                try:
                    await self._process_message(message)
                except Exception as e:
                    logger.error(
                        f"Error processing finding event: {e}",
                        extra={"correlation_id": getattr(message, "key", None)},
                    )
        except Exception as e:
            logger.error(f"Finding consumer error: {e}")

    async def _process_message(self, message: Any) -> None:
        if not self._session_factory:
            return

        event = message.value

        # ── Schema validation — reject malformed events to DLQ ────────────────
        if not self._validate_event(event):
            logger.warning(
                f"Malformed finding.raw event — forwarding to DLQ",
                extra={"raw_event": str(event)[:200]},
            )
            await self._send_to_dlq(message)
            return

        from app.core.database import create_db_session
        from app.services.findings import FindingService
        from app.services.notifications import NotificationService

        async with create_db_session(
            self._session_factory, event.get("organization_id")
        ) as session:
            finding_service = FindingService(session, self._redis_client, self._kafka_producer)
            finding = await finding_service.ingest_finding(event)

            # Send notifications for new (non-suppressed) findings
            if finding and finding.get("status") == "open":
                notif_service = NotificationService(session, self._redis_client, self._kafka_producer)
                await notif_service.send_notification(finding)

    def _validate_event(self, event: Any) -> bool:
        """Validate required fields per the finding.raw schema."""
        if not isinstance(event, dict):
            return False
        required = {"organization_id", "rule_id", "resource_id", "severity", "title"}
        return required.issubset(event.keys())

    async def _send_to_dlq(self, message: Any) -> None:
        """Forward malformed message to the dead-letter topic."""
        if not self._kafka_producer:
            return
        try:
            dlq_payload = {
                "original_topic": "finding.raw",
                "original_key": message.key.decode("utf-8") if message.key else None,
                "original_value": message.value,
                "error": "schema_validation_failed",
            }
            await self._kafka_producer.send_and_wait(
                DLQ_TOPIC,
                value=json.dumps(dlq_payload, default=str).encode("utf-8"),
            )
        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}")


class ResourceEventConsumer:
    """
    Consumes resource.deleted and resource.updated events.

    resource.deleted → auto-resolve all open findings for the deleted resource.
    resource.updated → re-evaluate open findings; if the resource is now compliant,
                       the CSPM module will emit finding.resolved — but we also
                       check here for any stale open findings that should be closed.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str = "cloudvisor-alert-resources",
        session_factory: Any = None,
        kafka_producer: Any = None,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._session_factory = session_factory
        self._kafka_producer = kafka_producer
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            "resource.deleted",
            "resource.updated",
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
        )
        await self._consumer.start()
        self._running = True
        logger.info("Resource event consumer started (topics: resource.deleted, resource.updated)")

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()

    async def run(self) -> None:
        if not self._consumer:
            return
        try:
            async for message in self._consumer:
                if not self._running:
                    break
                try:
                    event_type = message.value.get("event_type", "")
                    if event_type == "resource.deleted":
                        await self._handle_resource_deleted(message.value)
                    elif event_type == "resource.updated":
                        await self._handle_resource_updated(message.value)
                except Exception as e:
                    logger.error(f"Resource consumer error processing message: {e}")
        except Exception as e:
            logger.error(f"Resource consumer error: {e}")

    async def _handle_resource_deleted(self, event: dict) -> None:
        """Auto-resolve all open findings for a deleted resource."""
        cloud_resource_id = event.get("cloud_resource_id") or event.get("resource_id")
        organization_id = event.get("organization_id")
        if not cloud_resource_id or not self._session_factory:
            return

        from sqlalchemy import select, update
        from app.models import FindingModel
        from app.core.database import create_db_session
        from datetime import datetime

        try:
            async with create_db_session(self._session_factory, organization_id) as session:
                stmt = (
                    update(FindingModel)
                    .where(
                        FindingModel.resource_id == cloud_resource_id,
                        FindingModel.status.in_(["open", "in_progress"]),
                    )
                    .values(
                        status="resolved",
                        resolved_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    .returning(FindingModel.id, FindingModel.organization_id, FindingModel.severity)
                )
                result = await session.execute(stmt)
                resolved_rows = result.fetchall()

                if resolved_rows:
                    logger.info(
                        f"Auto-resolved {len(resolved_rows)} findings for deleted resource "
                        f"{cloud_resource_id}",
                        extra={"organization_id": organization_id},
                    )
                    # Emit finding.resolved Kafka events for each resolved finding
                    for row in resolved_rows:
                        await self._emit_resolved(row[0], row[1], row[2])
        except Exception as e:
            logger.error(f"Failed to auto-resolve findings for deleted resource: {e}")

    async def _handle_resource_updated(self, event: dict) -> None:
        """
        On resource.updated: check if any open findings for this resource
        should be auto-resolved (the underlying issue may have been fixed).
        The CSPM module handles re-evaluation and emits finding.resolved when
        a rule no longer fires. This consumer handles the case where the
        resource is marked as no longer public/exposed at the graph level.
        """
        cloud_resource_id = event.get("cloud_resource_id") or event.get("resource_id")
        organization_id = event.get("organization_id")
        if not cloud_resource_id or not self._session_factory:
            return

        # Only auto-resolve if the resource is explicitly marked as fixed
        # (e.g., is_public changed from True to False)
        resource_data = event.get("resource_data", {})
        was_public = event.get("previous_state", {}).get("is_public", False)
        is_now_public = resource_data.get("is_public", True)

        if was_public and not is_now_public:
            # Resource became private — auto-resolve public-access findings
            from sqlalchemy import select, update
            from app.models import FindingModel
            from app.core.database import create_db_session
            from datetime import datetime

            try:
                async with create_db_session(self._session_factory, organization_id) as session:
                    stmt = (
                        update(FindingModel)
                        .where(
                            FindingModel.resource_id == cloud_resource_id,
                            FindingModel.status == "open",
                            FindingModel.rule_id.like("%-public-%"),
                        )
                        .values(
                            status="resolved",
                            resolved_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        .returning(FindingModel.id, FindingModel.organization_id, FindingModel.severity)
                    )
                    result = await session.execute(stmt)
                    resolved_rows = result.fetchall()

                    if resolved_rows:
                        logger.info(
                            f"Auto-resolved {len(resolved_rows)} public-access findings "
                            f"for resource {cloud_resource_id} (now private)",
                            extra={"organization_id": organization_id},
                        )
                        for row in resolved_rows:
                            await self._emit_resolved(row[0], row[1], row[2])
            except Exception as e:
                logger.error(f"Failed to auto-resolve findings on resource.updated: {e}")

    async def _emit_resolved(self, finding_id: str, org_id: str, severity: str) -> None:
        """Emit finding.resolved Kafka event."""
        if not self._kafka_producer:
            return
        try:
            from datetime import datetime
            payload = {
                "event_type": "finding.resolved",
                "finding_id": finding_id,
                "organization_id": org_id,
                "severity": severity,
                "resolution_reason": "resource_deleted_or_fixed",
                "timestamp": datetime.utcnow().isoformat(),
            }
            await self._kafka_producer.send_and_wait(
                "finding.resolved",
                key=finding_id.encode("utf-8"),
                value=json.dumps(payload, default=str).encode("utf-8"),
            )
        except Exception as e:
            logger.error(f"Failed to emit finding.resolved for {finding_id}: {e}")


class AuditEventConsumer:
    """
    GAP 1: Consumes audit.events from Kafka and stores them in the audit_log table.
    This is a pass-through consumer — every audit event is persisted as-is.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str = "cloudvisor-alert-audit",
        session_factory: Any = None,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._session_factory = session_factory
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            "audit.events",
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        logger.info("Audit event consumer started (topic: audit.events)")

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
        logger.info("Audit event consumer stopped")

    async def run(self) -> None:
        if not self._consumer:
            return
        try:
            async for message in self._consumer:
                if not self._running:
                    break
                try:
                    await self._process_message(message)
                except Exception as e:
                    logger.error(f"Error processing audit event: {e}")
        except Exception as e:
            logger.error(f"Audit consumer error: {e}")

    async def _process_message(self, message: Any) -> None:
        """Persist audit event to audit_log table (pass-through)."""
        if not self._session_factory:
            return

        event = message.value
        if not isinstance(event, dict):
            logger.warning("Malformed audit event — not a dict, skipping")
            return

        organization_id = event.get("organization_id")
        if not organization_id:
            logger.warning("Audit event missing organization_id, skipping")
            return

        from app.core.database import create_db_session
        from app.models.alert import AuditLogModel
        import uuid as _uuid
        from datetime import datetime as _dt

        try:
            async with create_db_session(self._session_factory, organization_id) as session:
                audit_entry = AuditLogModel(
                    id=str(_uuid.uuid4()),
                    organization_id=organization_id,
                    user_id=event.get("user_id"),
                    action=event.get("action", "unknown"),
                    resource_type=event.get("resource_type"),
                    resource_id=event.get("resource_id"),
                    ip_address=event.get("ip_address"),
                    user_agent=event.get("user_agent"),
                    event_metadata=event.get("metadata"),
                    created_at=_dt.utcnow(),
                )
                session.add(audit_entry)
                await session.commit()
                logger.debug(
                    f"Audit event stored: action={event.get('action')} "
                    f"org={organization_id}"
                )
        except Exception as e:
            logger.error(f"Failed to persist audit event: {e}")
