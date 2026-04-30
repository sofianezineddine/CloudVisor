"""Kafka consumers for the Alert service."""

import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)


class FindingEventConsumer:
    """Consumes finding.raw events from the Policy service and persists them."""

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
                    logger.error(f"Error processing finding event: {e}")
        except Exception as e:
            logger.error(f"Finding consumer error: {e}")

    async def _process_message(self, message: Any) -> None:
        if not self._session_factory:
            return

        event = message.value
        from app.core.database import create_db_session
        from app.services.findings import FindingService
        from app.services.notifications import NotificationService

        async with create_db_session(self._session_factory) as session:
            finding_service = FindingService(session, self._redis_client, self._kafka_producer)
            finding = await finding_service.ingest_finding(event)

            # Send notifications for new findings
            if finding and finding.get("status") == "open":
                notif_service = NotificationService(session, self._redis_client)
                await notif_service.send_notification(finding)


class ResourceEventConsumer:
    """Consumes resource.deleted events to auto-resolve orphaned findings."""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str = "cloudvisor-alert-resources",
        session_factory: Any = None,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._session_factory = session_factory
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            "resource.deleted",
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
        )
        await self._consumer.start()
        self._running = True

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
                await self._process_resource_event(message.value)
        except Exception as e:
            logger.error(f"Resource consumer error: {e}")

    async def _process_resource_event(self, event: dict) -> None:
        """Auto-resolve findings for deleted resources."""
        if event.get("event_type") != "resource.deleted":
            return

        cloud_resource_id = event.get("cloud_resource_id")
        if not cloud_resource_id or not self._session_factory:
            return

        from sqlalchemy import select, update
        from app.models import FindingModel
        from app.core.database import create_db_session
        from datetime import datetime

        try:
            async with create_db_session(self._session_factory) as session:
                stmt = (
                    update(FindingModel)
                    .where(
                        FindingModel.resource_id == cloud_resource_id,
                        FindingModel.status == "open",
                    )
                    .values(status="resolved", resolved_at=datetime.utcnow())
                )
                result = await session.execute(stmt)
                if result.rowcount > 0:
                    logger.info(
                        f"Auto-resolved {result.rowcount} findings for deleted resource {cloud_resource_id}"
                    )
        except Exception as e:
            logger.error(f"Failed to auto-resolve findings: {e}")
