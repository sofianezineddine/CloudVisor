"""Event Correlation Engine — groups related security events and generates alerts.

Evaluates configurable correlation rules against incoming events, groups them
by correlation key within time windows, deduplicates alerts, and publishes
to the cspm.alerts Kafka topic.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_cspm_settings
from ..models.drift_models import (
    CorrelatedAlertModel,
    CorrelationRuleModel,
)
from ..producers.alert_producer import AlertProducer

logger = logging.getLogger(__name__)
settings = get_cspm_settings()

# Severity ordering for combined severity computation
SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


async def evaluate_correlation_rules(
    db: AsyncSession,
    event: dict[str, Any],
    organization_id: str,
) -> list[CorrelationRuleModel]:
    """Match an incoming event against configurable correlation rules.

    Retrieves active rules for the organization and checks if the event's
    type matches any rule's configured event_types.

    Args:
        db: Async database session.
        event: The incoming event dict (must have 'event_type' key).
        organization_id: The organization ID.

    Returns:
        List of matching CorrelationRuleModel instances.
    """
    event_type = event.get("event_type", "")

    result = await db.execute(
        select(CorrelationRuleModel).where(
            CorrelationRuleModel.organization_id == organization_id,
            CorrelationRuleModel.is_active == True,  # noqa: E712
        )
    )
    rules = result.scalars().all()

    matching_rules: list[CorrelationRuleModel] = []
    for rule in rules:
        if event_type in (rule.event_types or []):
            matching_rules.append(rule)

    if matching_rules:
        logger.debug(
            "Event type=%s matched %d correlation rules for org=%s",
            event_type, len(matching_rules), organization_id,
        )

    return matching_rules


def group_events(
    events: list[dict[str, Any]],
    group_by_fields: list[str],
    time_window_seconds: int,
) -> dict[str, list[dict[str, Any]]]:
    """Group events by correlation key within a time window.

    Events are grouped by the hash of their group_by field values.
    Only events within the specified time window are included.

    Args:
        events: List of event dicts to group.
        group_by_fields: Fields to use as the grouping key.
        time_window_seconds: Maximum time span (seconds) for events in a group.

    Returns:
        Dict mapping correlation_key -> list of events in that group.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=time_window_seconds)

    groups: dict[str, list[dict[str, Any]]] = {}

    for event in events:
        # Filter by time window
        event_time = event.get("timestamp")
        if isinstance(event_time, str):
            try:
                event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                event_time = now
        elif not isinstance(event_time, datetime):
            event_time = now

        if event_time < window_start:
            continue

        # Compute correlation key from group_by fields
        key_parts = []
        for field in group_by_fields:
            value = event.get(field, "")
            key_parts.append(f"{field}={value}")

        correlation_key = _compute_correlation_key(key_parts)

        if correlation_key not in groups:
            groups[correlation_key] = []
        groups[correlation_key].append(event)

    return groups


async def generate_correlated_alert(
    db: AsyncSession,
    *,
    organization_id: str,
    correlation_rule_id: str,
    correlation_key: str,
    contributing_events: list[dict[str, Any]],
) -> CorrelatedAlertModel:
    """Create an alert with combined severity from correlated events.

    The combined severity is the maximum severity among all contributing events.

    Args:
        db: Async database session.
        organization_id: The organization ID.
        correlation_rule_id: The rule that triggered this alert.
        correlation_key: The hash key grouping the events.
        contributing_events: List of event dicts that triggered the alert.

    Returns:
        The persisted CorrelatedAlertModel instance.
    """
    # Compute combined severity (max of all contributing events)
    combined_severity = _compute_combined_severity(contributing_events)

    # Extract event IDs
    event_ids = [
        e.get("id") or e.get("event_id") or e.get("drift_event_id", "")
        for e in contributing_events
    ]

    now = datetime.now(timezone.utc)
    suppression_expires = now + timedelta(seconds=settings.drift_alert_suppression_seconds)

    alert = CorrelatedAlertModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        correlation_rule_id=correlation_rule_id,
        correlation_key=correlation_key,
        contributing_event_ids=event_ids,
        combined_severity=combined_severity,
        status="open",
        suppression_expires_at=suppression_expires,
        created_at=now,
        updated_at=now,
    )
    db.add(alert)
    await db.flush()
    logger.info(
        "Generated correlated alert id=%s rule=%s severity=%s events=%d",
        alert.id, correlation_rule_id, combined_severity, len(contributing_events),
    )
    return alert


async def deduplicate_alert(
    db: AsyncSession,
    *,
    organization_id: str,
    correlation_key: str,
) -> Optional[CorrelatedAlertModel]:
    """Check suppression window for existing alerts with the same correlation key.

    If an open alert exists for the same correlation key and its suppression
    window has not expired, the existing alert is returned (indicating dedup).

    Args:
        db: Async database session.
        organization_id: The organization ID.
        correlation_key: The correlation key to check.

    Returns:
        The existing alert if within suppression window, None otherwise.
    """
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(CorrelatedAlertModel).where(
            CorrelatedAlertModel.organization_id == organization_id,
            CorrelatedAlertModel.correlation_key == correlation_key,
            CorrelatedAlertModel.status == "open",
            CorrelatedAlertModel.suppression_expires_at > now,
        ).order_by(CorrelatedAlertModel.created_at.desc()).limit(1)
    )
    existing = result.scalar_one_or_none()

    if existing:
        logger.debug(
            "Alert deduplicated: existing alert id=%s for key=%s (suppression until %s)",
            existing.id, correlation_key, existing.suppression_expires_at,
        )

    return existing


async def publish_alert(
    alert: CorrelatedAlertModel,
    contributing_events: list[dict[str, Any]],
    alert_producer: Optional[AlertProducer] = None,
) -> None:
    """Publish a correlated alert to the cspm.alerts Kafka topic.

    Args:
        alert: The CorrelatedAlertModel to publish.
        contributing_events: The events that contributed to this alert.
        alert_producer: The AlertProducer instance for Kafka publishing.
    """
    if not alert_producer:
        logger.warning(
            "No alert producer available, skipping publish for alert id=%s", alert.id
        )
        return

    await alert_producer.publish_cspm_alert(
        alert_id=alert.id,
        organization_id=alert.organization_id,
        correlation_rule_id=alert.correlation_rule_id,
        combined_severity=alert.combined_severity,
        contributing_events=contributing_events,
    )
    logger.info("Published correlated alert id=%s to cspm.alerts", alert.id)


def _compute_correlation_key(key_parts: list[str]) -> str:
    """Compute a stable hash key from group_by field values.

    Args:
        key_parts: List of "field=value" strings.

    Returns:
        A hex digest string representing the correlation key.
    """
    raw = "|".join(sorted(key_parts))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _compute_combined_severity(events: list[dict[str, Any]]) -> str:
    """Compute the maximum severity across all contributing events.

    Args:
        events: List of event dicts with optional 'severity' key.

    Returns:
        The highest severity string found, defaults to "MEDIUM".
    """
    max_level = 0
    for event in events:
        severity = event.get("severity", "LOW").upper()
        level = SEVERITY_ORDER.get(severity, 1)
        if level > max_level:
            max_level = level

    # Reverse lookup
    for name, level in SEVERITY_ORDER.items():
        if level == max_level:
            return name

    return "MEDIUM"
