"""Kafka producer for copilot audit events."""

import json
import logging
from datetime import datetime
from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


class AuditEventProducer:
    """Kafka producer for copilot.query_logged events."""

    def __init__(self, bootstrap_servers: str):
        """
        Initialize audit event producer.

        Args:
            bootstrap_servers: Kafka bootstrap servers
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer: AIOKafkaProducer | None = None
        self.topic = "copilot.query_logged"

    async def start(self):
        """Start the Kafka producer."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self.producer.start()
        logger.info(f"Audit event producer started (topic: {self.topic})")

    async def stop(self):
        """Stop the Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("Audit event producer stopped")

    async def emit_query_logged(
        self,
        query_id: str,
        organization_id: str,
        user_id: str,
        intent: str,
        processing_ms: int,
        data_sources_used: list[str],
    ):
        """
        Emit a copilot.query_logged event.

        Args:
            query_id: Unique query identifier
            organization_id: Organization ID
            user_id: User ID
            intent: Detected intent
            processing_ms: Processing time in milliseconds
            data_sources_used: List of data sources queried
        """
        if not self.producer:
            logger.warning("Producer not started, skipping event emission")
            return

        event = {
            "query_id": query_id,
            "organization_id": organization_id,
            "user_id": user_id,
            "intent": intent,
            "processing_ms": processing_ms,
            "data_sources_used": data_sources_used,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            await self.producer.send_and_wait(self.topic, value=event)
            logger.info(f"Emitted copilot.query_logged event: query_id={query_id}")
        except Exception as e:
            logger.error(f"Failed to emit audit event: {e}")
