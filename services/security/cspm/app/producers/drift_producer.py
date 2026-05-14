"""Kafka producer for drift detection and anomaly events."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_cspm_settings

logger = logging.getLogger(__name__)
settings = get_cspm_settings()


class DriftProducer:
    """Publishes drift.detected, drift.security_relevant, and anomaly.detected events."""

    def __init__(self, kafka_producer=None):
        self._producer = kafka_producer

    async def publish_drift_detected(
        self,
        *,
        organization_id: str,
        resource_id: str,
        resource_type: str,
        field_name: str,
        baseline_value: Any,
        current_value: Any,
        is_security_relevant: bool,
        severity: str,
        correlation_id: str | None = None,
    ) -> None:
        """Publish a drift.detected event when configuration drift is found."""
        if not self._producer:
            logger.warning(
                "Kafka producer not available, skipping drift.detected event "
                f"for resource {resource_id}"
            )
            return

        event = {
            "organization_id": organization_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "field_name": field_name,
            "baseline_value": baseline_value,
            "current_value": current_value,
            "is_security_relevant": is_security_relevant,
            "severity": severity,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self._producer.send_and_wait(
                settings.kafka_topic_drift_detected,
                json.dumps(event).encode("utf-8"),
            )
            logger.info(
                f"Published drift.detected for resource={resource_id} field={field_name}"
            )
        except Exception as e:
            logger.error(f"Failed to publish drift.detected: {e}")

    async def publish_drift_security_relevant(
        self,
        *,
        organization_id: str,
        resource_id: str,
        resource_type: str,
        field_name: str,
        environment: str,
        severity: str,
        drift_event_id: str,
        correlation_id: str | None = None,
    ) -> None:
        """Publish a drift.security_relevant event for security-impacting drift."""
        if not self._producer:
            logger.warning(
                "Kafka producer not available, skipping drift.security_relevant event "
                f"for resource {resource_id}"
            )
            return

        event = {
            "organization_id": organization_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "field_name": field_name,
            "environment": environment,
            "severity": severity,
            "drift_event_id": drift_event_id,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self._producer.send_and_wait(
                settings.kafka_topic_drift_security_relevant,
                json.dumps(event).encode("utf-8"),
            )
            logger.info(
                f"Published drift.security_relevant for resource={resource_id} "
                f"field={field_name} severity={severity}"
            )
        except Exception as e:
            logger.error(f"Failed to publish drift.security_relevant: {e}")

    async def publish_anomaly_detected(
        self,
        *,
        organization_id: str,
        resource_id: str,
        resource_type: str,
        anomaly_score: float,
        deviating_fields: list[dict[str, Any]],
        severity: str,
        correlation_id: str | None = None,
    ) -> None:
        """Publish an anomaly.detected event when behavioral anomaly is found."""
        if not self._producer:
            logger.warning(
                "Kafka producer not available, skipping anomaly.detected event "
                f"for resource {resource_id}"
            )
            return

        event = {
            "organization_id": organization_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "anomaly_score": anomaly_score,
            "deviating_fields": deviating_fields,
            "severity": severity,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self._producer.send_and_wait(
                settings.kafka_topic_anomaly_detected,
                json.dumps(event).encode("utf-8"),
            )
            logger.info(
                f"Published anomaly.detected for resource={resource_id} "
                f"score={anomaly_score} severity={severity}"
            )
        except Exception as e:
            logger.error(f"Failed to publish anomaly.detected: {e}")
