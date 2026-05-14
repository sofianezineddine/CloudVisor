"""Drift Detection service — configuration drift detection and management.

Compares resource configurations against stored baselines, classifies drift
as security-relevant or informational, assigns severity, and persists findings.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from deepdiff import DeepDiff
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_cspm_settings
from ..models.drift_models import (
    ConfigChangeHistoryModel,
    DriftBaselineModel,
    DriftEventModel,
)

logger = logging.getLogger(__name__)
settings = get_cspm_settings()

# Fields covered by Rego security rules — drift in these is security-relevant
SECURITY_RELEVANT_FIELDS: set[str] = {
    "public_access",
    "encryption",
    "encryption_enabled",
    "ssl_enabled",
    "tls_enabled",
    "firewall_rules",
    "security_groups",
    "iam_policy",
    "access_control",
    "authentication",
    "mfa_enabled",
    "logging_enabled",
    "audit_logging",
    "network_acl",
    "kms_key_id",
    "versioning",
    "backup_enabled",
    "deletion_protection",
    "publicly_accessible",
    "ingress_rules",
    "egress_rules",
    "password_policy",
    "rotation_enabled",
    "vpc_config",
    "subnet_type",
}


def compare_config(
    baseline_config: dict[str, Any],
    current_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Deep-diff baseline vs current config using deepdiff.

    Returns a list of changed fields with their baseline and current values.

    Args:
        baseline_config: The stored baseline configuration dict.
        current_config: The current resource configuration dict.

    Returns:
        List of dicts with keys: field_name, baseline_value, current_value, change_type.
    """
    diff = DeepDiff(
        baseline_config,
        current_config,
        ignore_order=True,
        verbose_level=2,
    )

    changes: list[dict[str, Any]] = []

    # Values changed
    for path, change in diff.get("values_changed", {}).items():
        field_name = _extract_field_name(path)
        changes.append({
            "field_name": field_name,
            "baseline_value": change.get("old_value"),
            "current_value": change.get("new_value"),
            "change_type": "modified",
        })

    # Items added
    for path, value in diff.get("dictionary_item_added", {}).items():
        field_name = _extract_field_name(path)
        changes.append({
            "field_name": field_name,
            "baseline_value": None,
            "current_value": value,
            "change_type": "added",
        })

    # Items removed
    for path, value in diff.get("dictionary_item_removed", {}).items():
        field_name = _extract_field_name(path)
        changes.append({
            "field_name": field_name,
            "baseline_value": value,
            "current_value": None,
            "change_type": "removed",
        })

    # Type changes
    for path, change in diff.get("type_changes", {}).items():
        field_name = _extract_field_name(path)
        changes.append({
            "field_name": field_name,
            "baseline_value": change.get("old_value"),
            "current_value": change.get("new_value"),
            "change_type": "type_changed",
        })

    # Iterable items added/removed
    for path, value in diff.get("iterable_item_added", {}).items():
        field_name = _extract_field_name(path)
        changes.append({
            "field_name": field_name,
            "baseline_value": None,
            "current_value": value,
            "change_type": "item_added",
        })

    for path, value in diff.get("iterable_item_removed", {}).items():
        field_name = _extract_field_name(path)
        changes.append({
            "field_name": field_name,
            "baseline_value": value,
            "current_value": None,
            "change_type": "item_removed",
        })

    return changes


def classify_drift(field_name: str) -> bool:
    """Check if a changed field is covered by a Rego security rule.

    Args:
        field_name: The name of the field that changed.

    Returns:
        True if the field is security-relevant, False otherwise.
    """
    # Normalize field name: extract the last segment for nested paths
    normalized = field_name.lower().replace("-", "_")
    # Check if any security-relevant keyword is contained in the field name
    for sec_field in SECURITY_RELEVANT_FIELDS:
        if sec_field in normalized:
            return True
    return False


def assign_drift_severity(
    is_security_relevant: bool,
    environment: Optional[str] = None,
) -> str:
    """Assign severity based on security relevance and environment.

    HIGH for security-relevant drift on production environments,
    MEDIUM for security-relevant on non-prod or non-security on prod,
    LOW for non-security-relevant on non-prod.

    Args:
        is_security_relevant: Whether the drift field is security-relevant.
        environment: The resource environment (e.g., "production", "staging", "dev").

    Returns:
        Severity string: "HIGH", "MEDIUM", or "LOW".
    """
    is_prod = environment and environment.lower() in ("production", "prod")

    if is_security_relevant and is_prod:
        return "HIGH"
    elif is_security_relevant or is_prod:
        return "MEDIUM"
    else:
        return "LOW"


async def store_drift_event(
    db: AsyncSession,
    *,
    organization_id: str,
    resource_id: str,
    field_name: str,
    baseline_value: Any,
    current_value: Any,
    is_security_relevant: bool,
    severity: str,
    environment: Optional[str] = None,
) -> DriftEventModel:
    """Persist a drift finding to the database.

    Args:
        db: Async database session.
        organization_id: The organization ID.
        resource_id: The resource that drifted.
        field_name: The field that changed.
        baseline_value: The expected baseline value.
        current_value: The current observed value.
        is_security_relevant: Whether the drift is security-relevant.
        severity: The assigned severity level.
        environment: The resource environment.

    Returns:
        The persisted DriftEventModel instance.
    """
    event = DriftEventModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        resource_id=resource_id,
        field_name=field_name,
        baseline_value=baseline_value,
        current_value=current_value,
        is_security_relevant=is_security_relevant,
        severity=severity,
        environment=environment,
        detected_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()
    logger.info(
        "Stored drift event id=%s resource=%s field=%s severity=%s",
        event.id, resource_id, field_name, severity,
    )
    return event


async def update_change_history(
    db: AsyncSession,
    *,
    organization_id: str,
    resource_id: str,
    field_name: str,
    old_value: Any,
    new_value: Any,
) -> ConfigChangeHistoryModel:
    """Append to config change history with retention period.

    Creates a history entry that will expire after the configured retention period.

    Args:
        db: Async database session.
        organization_id: The organization ID.
        resource_id: The resource ID.
        field_name: The field that changed.
        old_value: The previous value.
        new_value: The new value.

    Returns:
        The persisted ConfigChangeHistoryModel instance.
    """
    now = datetime.now(timezone.utc)
    retention_expires = now + timedelta(days=settings.drift_baseline_retention_days)

    history_entry = ConfigChangeHistoryModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        resource_id=resource_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        changed_at=now,
        retention_expires_at=retention_expires,
    )
    db.add(history_entry)
    await db.flush()
    logger.debug(
        "Recorded change history for resource=%s field=%s expires=%s",
        resource_id, field_name, retention_expires.isoformat(),
    )
    return history_entry


async def set_baseline(
    db: AsyncSession,
    *,
    organization_id: str,
    resource_id: str,
    resource_type: str,
    baseline_config: dict[str, Any],
    set_by: Optional[str] = None,
) -> DriftBaselineModel:
    """Create or replace the baseline for a resource.

    If a baseline already exists for the resource, it is updated in place.

    Args:
        db: Async database session.
        organization_id: The organization ID.
        resource_id: The resource ID.
        resource_type: The type of resource (e.g., "aws_s3_bucket").
        baseline_config: The configuration snapshot to use as baseline.
        set_by: Who set the baseline (user email or "auto").

    Returns:
        The created or updated DriftBaselineModel instance.
    """
    now = datetime.now(timezone.utc)

    # Check for existing baseline
    result = await db.execute(
        select(DriftBaselineModel).where(
            DriftBaselineModel.organization_id == organization_id,
            DriftBaselineModel.resource_id == resource_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.baseline_config = baseline_config
        existing.resource_type = resource_type
        existing.set_by = set_by
        existing.updated_at = now
        await db.flush()
        logger.info("Updated baseline for resource=%s org=%s", resource_id, organization_id)
        return existing

    baseline = DriftBaselineModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        resource_id=resource_id,
        resource_type=resource_type,
        baseline_config=baseline_config,
        set_by=set_by,
        created_at=now,
        updated_at=now,
    )
    db.add(baseline)
    await db.flush()
    logger.info("Created baseline for resource=%s org=%s", resource_id, organization_id)
    return baseline


async def cleanup_expired_history(db: AsyncSession) -> int:
    """Remove history entries past the retention period.

    Deletes all ConfigChangeHistory records whose retention_expires_at is in the past.

    Args:
        db: Async database session.

    Returns:
        Number of deleted records.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        delete(ConfigChangeHistoryModel).where(
            ConfigChangeHistoryModel.retention_expires_at < now
        )
    )
    deleted_count = result.rowcount
    if deleted_count > 0:
        logger.info("Cleaned up %d expired config change history entries", deleted_count)
    return deleted_count


def _extract_field_name(deepdiff_path: str) -> str:
    """Extract a readable field name from a DeepDiff path string.

    DeepDiff paths look like: root['key1']['key2'] or root[0]['key']
    This extracts the meaningful field path.

    Args:
        deepdiff_path: The raw DeepDiff path string.

    Returns:
        A dot-separated field path string.
    """
    # Remove 'root' prefix
    path = deepdiff_path.replace("root", "")
    # Extract keys from bracket notation
    parts: list[str] = []
    import re
    for match in re.finditer(r"\['([^']+)'\]|\[(\d+)\]", path):
        if match.group(1):
            parts.append(match.group(1))
        elif match.group(2):
            parts.append(f"[{match.group(2)}]")
    return ".".join(parts) if parts else deepdiff_path
