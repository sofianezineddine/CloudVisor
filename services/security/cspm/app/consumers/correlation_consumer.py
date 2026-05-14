"""Kafka consumer for event correlation — listens for findings, drift, and anomaly events.

Subscribes to finding.created, drift.detected, and anomaly.detected topics.
Evaluates correlation rules on each event and generates correlated alerts
when rules match.
"""

import asyncio
import json
import logging
from typing import Any, Optional

from ..core.config import get_cspm_settings
from ..producers.alert_producer import AlertProducer

logger = logging.getLogger(__name__)
settings = get_cspm_settings()


class CorrelationEventConsumer:
    """Consumes security events and evaluates correlation rules."""

    def __init__(
        self,
        bootstrap_servers: str,
        kafka_producer=None,
        alert_producer: Optional[AlertProducer] = None,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._kafka_producer = kafka_producer
        self._alert_producer = alert_producer or AlertProducer(kafka_producer)
        self._consumer = None
        # In-memory event buffer for correlation window
        self._event_buffer: list[dict[str, Any]] = []

    async def start(self) -> None:
        """Start the Kafka consumer subscribing to security event topics."""
        try:
            from aiokafka import AIOKafkaConsumer

            self._consumer = AIOKafkaConsumer(
                settings.kafka_topic_finding_created,
                settings.kafka_topic_drift_detected,
                settings.kafka_topic_anomaly_detected,
                bootstrap_servers=self._bootstrap_servers,
                group_id="cspm-correlation-engine",
                auto_offset_reset="earliest",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            )
            await self._consumer.start()
            logger.info("Correlation event consumer started")
        except Exception as e:
            logger.warning(f"Correlation consumer failed to start: {e}")
            self._consumer = None

    async def run(self) -> None:
        """Main consumer loop — evaluate correlation rules on each event."""
        if not self._consumer:
            logger.warning(
                "No Kafka consumer — correlation engine running in degraded mode"
            )
            return

        from ..db_helper import AsyncSessionLocal
        from ..services.correlation_engine import (
            deduplicate_alert,
            evaluate_correlation_rules,
            generate_correlated_alert,
            group_events,
            publish_alert,
        )

        async for msg in self._consumer:
            try:
                event = msg.value
                org_id = event.get("organization_id", "")

                # Determine event type from the topic
                topic = msg.topic
                event_type = _topic_to_event_type(topic)
                event["event_type"] = event_type

                # Add to in-memory buffer
                self._event_buffer.append(event)

                # Prune old events from buffer (beyond max correlation window)
                self._prune_event_buffer()

                async with AsyncSessionLocal() as db:
                    # Find matching correlation rules
                    matching_rules = await evaluate_correlation_rules(
                        db, event, org_id
                    )

                    if not matching_rules:
                        continue

                    for rule in matching_rules:
                        # Group buffered events by the rule's group_by fields
                        groups = group_events(
                            self._event_buffer,
                            group_by_fields=rule.group_by or [],
                            time_window_seconds=rule.time_window_seconds,
                        )

                        for correlation_key, grouped_events in groups.items():
                            # Check if minimum event count is met
                            if len(grouped_events) < rule.min_events:
                                continue

                            # Check for deduplication
                            existing_alert = await deduplicate_alert(
                                db,
                                organization_id=org_id,
                                correlation_key=correlation_key,
                            )

                            if existing_alert:
                                logger.debug(
                                    "Alert suppressed for key=%s (existing alert=%s)",
                                    correlation_key, existing_alert.id,
                                )
                                continue

                            # Generate correlated alert
                            alert = await generate_correlated_alert(
                                db,
                                organization_id=org_id,
                                correlation_rule_id=rule.id,
                                correlation_key=correlation_key,
                                contributing_events=grouped_events,
                            )

                            # Publish to cspm.alerts topic
                            await publish_alert(
                                alert,
                                contributing_events=grouped_events,
                                alert_producer=self._alert_producer,
                            )

                    await db.commit()

            except Exception as e:
                logger.error(f"Error processing event for correlation: {e}")

    def _prune_event_buffer(self) -> None:
        """Remove events older than the maximum correlation window from the buffer."""
        from datetime import datetime, timedelta, timezone

        max_window = settings.drift_correlation_window_seconds
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_window * 2)

        pruned: list[dict[str, Any]] = []
        for event in self._event_buffer:
            timestamp = event.get("timestamp")
            if isinstance(timestamp, str):
                try:
                    event_time = datetime.fromisoformat(
                        timestamp.replace("Z", "+00:00")
                    )
                    if event_time >= cutoff:
                        pruned.append(event)
                        continue
                except (ValueError, TypeError):
                    pass
            # Keep events without parseable timestamps (recent)
            pruned.append(event)

        # Also cap buffer size to prevent unbounded growth
        max_buffer_size = 10000
        if len(pruned) > max_buffer_size:
            pruned = pruned[-max_buffer_size:]

        self._event_buffer = pruned

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        if self._consumer:
            await self._consumer.stop()
            logger.info("Correlation event consumer stopped")


def _topic_to_event_type(topic: str) -> str:
    """Map Kafka topic name to event type string.

    Args:
        topic: The Kafka topic name.

    Returns:
        The corresponding event type string.
    """
    topic_map = {
        settings.kafka_topic_finding_created: "finding.created",
        settings.kafka_topic_drift_detected: "drift.detected",
        settings.kafka_topic_anomaly_detected: "anomaly.detected",
    }
    return topic_map.get(topic, topic)
