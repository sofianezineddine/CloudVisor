"""
CloudVisor → Keep Alert Bridge Consumer

Consumes alerts from the CloudVisor Kafka topic `cloudvisor.alerts` and
ingests them into Keep's alert management system for correlation, deduplication,
and incident creation.

Consumer Group: keep-alert-ingestion
Topic: cloudvisor.alerts (configurable via KAFKA_TOPIC env var)

Field Mapping:
  CloudVisor.title        → Keep.name
  CloudVisor.severity     → Keep.severity
  CloudVisor.source       → Keep.source (list)
  CloudVisor.resource_id  → Keep.fingerprint
  CloudVisor.created_at   → Keep.lastReceived
  CloudVisor.tenant_id    → Keep.tenant_id
  CloudVisor.description  → Keep.description
  CloudVisor.metadata     → Keep.labels
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

import requests
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "cv-kafka:9092")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "cloudvisor.alerts")
KAFKA_GROUP_ID = os.environ.get("KAFKA_GROUP_ID", "keep-alert-ingestion")
KEEP_API_URL = os.environ.get("KEEP_API_URL", "http://localhost:8007")

# Severity mapping: CloudVisor uses 'medium', Keep uses 'warning'
SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "warning",
    "warning": "warning",
    "low": "low",
    "info": "info",
}


def map_cloudvisor_alert_to_keep(cv_alert: dict) -> dict:
    """Map a CloudVisor alert event to Keep's AlertDto format.

    Field Mapping (CloudVisor → Keep):
        title        → name
        severity     → severity (with mapping: medium→warning)
        source       → source[] (wrapped in a list)
        resource_id  → fingerprint
        created_at   → lastReceived
        tenant_id    → tenant_id
        metadata     → labels (merged with resource_type)
        description  → description

    This function is resilient to malformed inputs: any dict (including those
    with None values, wrong types, or missing fields) will produce a valid
    Keep alert dict without raising exceptions.
    """
    # Safely extract severity, handling None and non-string values
    raw_severity = cv_alert.get("severity")
    severity = str(raw_severity).lower() if raw_severity is not None else "info"
    mapped_severity = SEVERITY_MAP.get(severity, "info")

    # Safely build labels from resource_type and metadata
    labels = {}
    resource_type = cv_alert.get("resource_type")
    if resource_type is not None:
        labels["resource_type"] = str(resource_type)
    metadata = cv_alert.get("metadata")
    if metadata and isinstance(metadata, dict):
        labels.update({str(k): str(v) for k, v in metadata.items()})

    # Safely extract tenant_id with fallback to organization_id
    tenant_id = cv_alert.get("tenant_id") or cv_alert.get("organization_id") or ""
    tenant_id = str(tenant_id) if tenant_id else ""

    # Safely extract string fields, defaulting to sensible values
    name = cv_alert.get("title")
    name = str(name) if name is not None else "CloudVisor Alert"

    description = cv_alert.get("description")
    description = str(description) if description is not None else ""

    source = cv_alert.get("source")
    source = str(source) if source is not None else "cloudvisor"

    resource_id = cv_alert.get("resource_id") or cv_alert.get("id") or ""
    fingerprint = str(resource_id) if resource_id else ""

    created_at = cv_alert.get("created_at")
    last_received = str(created_at) if created_at is not None else datetime.now(timezone.utc).isoformat()

    environment = cv_alert.get("environment")
    environment = str(environment) if environment is not None else "production"

    return {
        "name": name,
        "description": description,
        "severity": mapped_severity,
        "status": "firing",
        "source": [source],
        "fingerprint": fingerprint,
        "lastReceived": last_received,
        "tenant_id": tenant_id,
        "labels": labels,
        "pushed": True,
        "environment": environment,
    }


def consume_cloudvisor_alerts():
    """Main consumer loop — consumes from cloudvisor.alerts and pushes to Keep."""
    max_retries = 10
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=KAFKA_GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                reconnect_backoff_max_ms=30000,
            )
            break
        except NoBrokersAvailable:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Kafka not available at {KAFKA_BOOTSTRAP_SERVERS}, "
                    f"retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(retry_delay)
            else:
                logger.error(
                    f"Could not connect to Kafka at {KAFKA_BOOTSTRAP_SERVERS} "
                    f"after {max_retries} attempts. Consumer will not start."
                )
                return

    logger.info(
        f"Started CloudVisor alert consumer "
        f"(topic: {KAFKA_TOPIC}, group: {KAFKA_GROUP_ID}, "
        f"brokers: {KAFKA_BOOTSTRAP_SERVERS})"
    )

    try:
        for message in consumer:
            try:
                cv_alert = message.value

                # Map to Keep format (includes tenant_id extraction)
                keep_alert = map_cloudvisor_alert_to_keep(cv_alert)
                tenant_id = keep_alert.get("tenant_id", "keep")

                # Push to Keep's alert ingestion endpoint
                try:
                    response = requests.post(
                        f"{KEEP_API_URL}/alerts/event",
                        json=keep_alert,
                        headers={
                            "Content-Type": "application/json",
                            "X-Tenant-ID": tenant_id,
                        },
                        timeout=10,
                    )
                    if response.status_code in (200, 201, 202):
                        logger.debug(
                            f"Alert ingested: {keep_alert['name']} (tenant: {tenant_id})"
                        )
                    else:
                        logger.warning(
                            f"Keep rejected alert: {response.status_code} - {response.text}",
                            extra={"alert": keep_alert, "tenant_id": tenant_id},
                        )
                except requests.RequestException as e:
                    logger.warning(
                        f"Failed to push alert to Keep: {e}",
                        extra={"alert": keep_alert, "tenant_id": tenant_id},
                    )

            except json.JSONDecodeError as e:
                logger.error(
                    f"Malformed JSON in Kafka message: {e}",
                    extra={"raw": str(message.value)[:500]},
                )
                continue
            except Exception as e:
                logger.error(
                    f"Error processing alert: {e}",
                    extra={"message": str(message.value)[:500]},
                )
                continue
    except Exception as e:
        logger.error(f"Consumer loop error: {e}")
    finally:
        try:
            consumer.close()
        except Exception:
            pass
        logger.info("CloudVisor alert consumer stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    consume_cloudvisor_alerts()
