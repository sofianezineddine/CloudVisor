"""Kafka consumer for drift detection — listens for resource changes.

Subscribes to resource.discovered and resource.updated topics.
On each event, compares the resource config against its stored baseline
and publishes drift events via the DriftProducer.
"""

import asyncio
import json
import logging
from typing import Any, Optional

from ..core.config import get_cspm_settings
from ..producers.drift_producer import DriftProducer

logger = logging.getLogger(__name__)
settings = get_cspm_settings()


class DriftEventConsumer:
    """Consumes resource events and triggers drift detection."""

    def __init__(
        self,
        bootstrap_servers: str,
        kafka_producer=None,
        drift_producer: Optional[DriftProducer] = None,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._kafka_producer = kafka_producer
        self._drift_producer = drift_producer or DriftProducer(kafka_producer)
        self._consumer = None

    async def start(self) -> None:
        """Start the Kafka consumer subscribing to resource topics."""
        try:
            from aiokafka import AIOKafkaConsumer

            self._consumer = AIOKafkaConsumer(
                settings.kafka_topic_resource_discovered,
                settings.kafka_topic_resource_updated,
                bootstrap_servers=self._bootstrap_servers,
                group_id="cspm-drift-detector",
                auto_offset_reset="earliest",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            )
            await self._consumer.start()
            logger.info("Drift event consumer started")
        except Exception as e:
            logger.warning(f"Drift consumer failed to start: {e}")
            self._consumer = None

    async def run(self) -> None:
        """Main consumer loop — process resource events for drift detection."""
        if not self._consumer:
            logger.warning("No Kafka consumer — drift detector running in degraded mode")
            return

        from ..db_helper import AsyncSessionLocal
        from ..services.drift_detector import (
            assign_drift_severity,
            classify_drift,
            compare_config,
            store_drift_event,
            update_change_history,
        )
        from ..models.drift_models import DriftBaselineModel
        from sqlalchemy import select

        async for msg in self._consumer:
            try:
                resource = msg.value
                org_id = resource.get("organization_id", "")
                resource_id = resource.get("cloud_resource_id", resource.get("id", ""))
                resource_type = resource.get("resource_type", "")
                current_config = resource.get("configuration", resource.get("config", {}))
                environment = resource.get("environment", resource.get("env"))

                if not current_config or not resource_id:
                    continue

                async with AsyncSessionLocal() as db:
                    # Fetch baseline for this resource
                    result = await db.execute(
                        select(DriftBaselineModel).where(
                            DriftBaselineModel.organization_id == org_id,
                            DriftBaselineModel.resource_id == resource_id,
                        )
                    )
                    baseline = result.scalar_one_or_none()

                    if not baseline:
                        # No baseline exists — skip drift detection for this resource
                        logger.debug(
                            "No baseline for resource=%s org=%s, skipping drift check",
                            resource_id, org_id,
                        )
                        continue

                    # Compare current config against baseline
                    changes = compare_config(baseline.baseline_config, current_config)

                    if not changes:
                        continue

                    logger.info(
                        "Drift detected: %d changes for resource=%s org=%s",
                        len(changes), resource_id, org_id,
                    )

                    for change in changes:
                        field_name = change["field_name"]
                        baseline_value = change["baseline_value"]
                        current_value = change["current_value"]

                        # Classify and assign severity
                        is_security_relevant = classify_drift(field_name)
                        severity = assign_drift_severity(is_security_relevant, environment)

                        # Store drift event
                        drift_event = await store_drift_event(
                            db,
                            organization_id=org_id,
                            resource_id=resource_id,
                            field_name=field_name,
                            baseline_value=baseline_value,
                            current_value=current_value,
                            is_security_relevant=is_security_relevant,
                            severity=severity,
                            environment=environment,
                        )

                        # Update change history
                        await update_change_history(
                            db,
                            organization_id=org_id,
                            resource_id=resource_id,
                            field_name=field_name,
                            old_value=baseline_value,
                            new_value=current_value,
                        )

                        # Publish drift event via Kafka
                        await self._drift_producer.publish_drift_detected(
                            organization_id=org_id,
                            resource_id=resource_id,
                            resource_type=resource_type,
                            field_name=field_name,
                            baseline_value=baseline_value,
                            current_value=current_value,
                            is_security_relevant=is_security_relevant,
                            severity=severity,
                        )

                        # Publish security-relevant drift separately
                        if is_security_relevant:
                            await self._drift_producer.publish_drift_security_relevant(
                                organization_id=org_id,
                                resource_id=resource_id,
                                resource_type=resource_type,
                                field_name=field_name,
                                environment=environment or "unknown",
                                severity=severity,
                                drift_event_id=drift_event.id,
                            )

                    await db.commit()

            except Exception as e:
                logger.error(f"Error processing resource event for drift detection: {e}")

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        if self._consumer:
            await self._consumer.stop()
            logger.info("Drift event consumer stopped")
