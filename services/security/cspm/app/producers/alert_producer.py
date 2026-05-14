"""Kafka producer for CSPM correlated alert events."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_cspm_settings

logger = logging.getLogger(__name__)
settings = get_cspm_settings()


class AlertProducer:
    """Publishes cspm.alerts events for correlated security alerts."""

    def __init__(self, kafka_producer=None):
        self._producer = kafka_producer

    async def publish_cspm_alert(
        self,
        *,
        alert_id: str,
        organization_id: str,
        correlation_rule_id: str,
        combined_severity: str,
        contributing_events: list[dict[str, Any]],
        correlation_id: str | None = None,
    ) -> None:
        """Publish a cspm.alerts event when a correlated alert is generated."""
        if not self._producer:
            logger.warning(
                "Kafka producer not available, skipping cspm.alerts event "
                f"for alert {alert_id}"
            )
            return

        event = {
            "alert_id": alert_id,
            "organization_id": organization_id,
            "correlation_rule_id": correlation_rule_id,
            "combined_severity": combined_severity,
            "contributing_events": contributing_events,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self._producer.send_and_wait(
                settings.kafka_topic_cspm_alerts,
                json.dumps(event).encode("utf-8"),
            )
            logger.info(
                f"Published cspm.alerts for alert_id={alert_id} "
                f"severity={combined_severity} "
                f"contributing_events={len(contributing_events)}"
            )
        except Exception as e:
            logger.error(f"Failed to publish cspm.alerts: {e}")
