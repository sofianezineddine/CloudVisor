"""Behavioral Anomaly Detection service.

Builds statistical baselines over rolling windows and detects anomalies
using z-score computation. Enriches findings with threat intelligence
correlation.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_cspm_settings
from ..models.drift_models import (
    AnomalyFindingModel,
    BehavioralBaselineModel,
)

logger = logging.getLogger(__name__)
settings = get_cspm_settings()

# Known threat indicators for enrichment
KNOWN_THREAT_INDICATORS: list[dict[str, Any]] = [
    {
        "pattern": "rapid_permission_changes",
        "description": "Multiple permission changes in short window",
        "severity_boost": "HIGH",
        "mitre_technique": "T1098",
    },
    {
        "pattern": "unusual_api_calls",
        "description": "API calls from unusual geographic location",
        "severity_boost": "HIGH",
        "mitre_technique": "T1078",
    },
    {
        "pattern": "data_exfiltration_pattern",
        "description": "Abnormal data transfer volume",
        "severity_boost": "CRITICAL",
        "mitre_technique": "T1537",
    },
    {
        "pattern": "privilege_escalation_attempt",
        "description": "Unusual privilege elevation activity",
        "severity_boost": "CRITICAL",
        "mitre_technique": "T1548",
    },
    {
        "pattern": "resource_creation_spike",
        "description": "Abnormal rate of resource creation",
        "severity_boost": "MEDIUM",
        "mitre_technique": "T1578",
    },
]


async def build_behavioral_baseline(
    db: AsyncSession,
    *,
    organization_id: str,
    resource_type: str,
    field_name: str,
    data_points: list[float],
) -> BehavioralBaselineModel:
    """Compute mean/stddev over a 30-day rolling window and persist the baseline.

    Uses numpy for statistical computation. If a baseline already exists for the
    given org/resource_type/field combination, it is updated.

    Args:
        db: Async database session.
        organization_id: The organization ID.
        resource_type: The type of resource being baselined.
        field_name: The metric field name.
        data_points: List of numeric values collected over the window.

    Returns:
        The created or updated BehavioralBaselineModel instance.
    """
    now = datetime.now(timezone.utc)
    window_days = settings.drift_behavioral_window_days

    # Compute statistics using numpy
    arr = np.array(data_points, dtype=np.float64)
    mean_value = float(np.mean(arr)) if len(arr) > 0 else 0.0
    stddev_value = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    sample_count = len(data_points)

    window_start = now - timedelta(days=window_days)
    window_end = now

    # Check for existing baseline
    result = await db.execute(
        select(BehavioralBaselineModel).where(
            BehavioralBaselineModel.organization_id == organization_id,
            BehavioralBaselineModel.resource_type == resource_type,
            BehavioralBaselineModel.field_name == field_name,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.mean_value = mean_value
        existing.stddev_value = stddev_value
        existing.sample_count = sample_count
        existing.window_start = window_start
        existing.window_end = window_end
        existing.updated_at = now
        await db.flush()
        logger.info(
            "Updated behavioral baseline org=%s type=%s field=%s mean=%.2f stddev=%.2f n=%d",
            organization_id, resource_type, field_name, mean_value, stddev_value, sample_count,
        )
        return existing

    baseline = BehavioralBaselineModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        resource_type=resource_type,
        field_name=field_name,
        mean_value=mean_value,
        stddev_value=stddev_value,
        sample_count=sample_count,
        window_start=window_start,
        window_end=window_end,
        updated_at=now,
    )
    db.add(baseline)
    await db.flush()
    logger.info(
        "Created behavioral baseline org=%s type=%s field=%s mean=%.2f stddev=%.2f n=%d",
        organization_id, resource_type, field_name, mean_value, stddev_value, sample_count,
    )
    return baseline


def detect_anomaly(
    current_value: float,
    baseline_mean: float,
    baseline_stddev: float,
    threshold: Optional[float] = None,
) -> tuple[bool, float]:
    """Z-score computation and threshold comparison.

    Computes the z-score of the current value against the baseline statistics
    and determines if it exceeds the configured threshold.

    Args:
        current_value: The current observed metric value.
        baseline_mean: The mean from the behavioral baseline.
        baseline_stddev: The standard deviation from the behavioral baseline.
        threshold: The z-score threshold (defaults to config value).

    Returns:
        Tuple of (is_anomalous, z_score).
    """
    if threshold is None:
        threshold = settings.drift_anomaly_stddev_threshold

    # Avoid division by zero — if stddev is 0, any deviation is anomalous
    if baseline_stddev == 0.0:
        if current_value != baseline_mean:
            # Infinite z-score effectively; use a large value
            return (True, float("inf"))
        return (False, 0.0)

    z_score = abs(current_value - baseline_mean) / baseline_stddev
    is_anomalous = z_score > threshold
    return (is_anomalous, z_score)


def enrich_with_threat_intel(
    anomaly_fields: list[dict[str, Any]],
    resource_type: str,
) -> list[dict[str, Any]]:
    """Correlate anomalous patterns with known threat indicators.

    Matches deviating fields against known threat intelligence patterns
    to provide additional context for security teams.

    Args:
        anomaly_fields: List of deviating field dicts with field names and values.
        resource_type: The type of resource exhibiting the anomaly.

    Returns:
        List of matching threat indicator dicts.
    """
    matched_indicators: list[dict[str, Any]] = []

    for indicator in KNOWN_THREAT_INDICATORS:
        pattern = indicator["pattern"]

        # Match based on field names and patterns
        for field_info in anomaly_fields:
            field_name = field_info.get("field", "").lower()

            if pattern == "rapid_permission_changes" and "permission" in field_name:
                matched_indicators.append(indicator)
                break
            elif pattern == "unusual_api_calls" and "api_call" in field_name:
                matched_indicators.append(indicator)
                break
            elif pattern == "data_exfiltration_pattern" and "data_transfer" in field_name:
                matched_indicators.append(indicator)
                break
            elif pattern == "privilege_escalation_attempt" and "privilege" in field_name:
                matched_indicators.append(indicator)
                break
            elif pattern == "resource_creation_spike" and "resource_count" in field_name:
                matched_indicators.append(indicator)
                break

    return matched_indicators


async def generate_anomaly_finding(
    db: AsyncSession,
    *,
    organization_id: str,
    resource_id: str,
    resource_type: str,
    deviating_fields: list[dict[str, Any]],
    anomaly_score: float,
    threat_indicators: Optional[list[dict[str, Any]]] = None,
) -> AnomalyFindingModel:
    """Create an anomaly finding with score, fields, and expected range.

    Persists the anomaly finding to the database with all relevant context
    including the anomaly score, deviating fields with expected ranges,
    and any matched threat indicators.

    Args:
        db: Async database session.
        organization_id: The organization ID.
        resource_id: The resource exhibiting anomalous behavior.
        resource_type: The type of resource.
        deviating_fields: List of dicts with field, value, expected_min, expected_max.
        anomaly_score: The computed anomaly score (max z-score across fields).
        threat_indicators: Optional list of matched threat indicators.

    Returns:
        The persisted AnomalyFindingModel instance.
    """
    # Determine severity based on anomaly score and threat indicators
    severity = _compute_anomaly_severity(anomaly_score, threat_indicators or [])

    finding = AnomalyFindingModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        resource_id=resource_id,
        resource_type=resource_type,
        anomaly_score=anomaly_score,
        deviating_fields=deviating_fields,
        severity=severity,
        threat_indicators=threat_indicators or [],
        detected_at=datetime.now(timezone.utc),
    )
    db.add(finding)
    await db.flush()
    logger.info(
        "Generated anomaly finding id=%s resource=%s score=%.2f severity=%s indicators=%d",
        finding.id, resource_id, anomaly_score, severity, len(threat_indicators or []),
    )
    return finding


def _compute_anomaly_severity(
    anomaly_score: float,
    threat_indicators: list[dict[str, Any]],
) -> str:
    """Compute severity for an anomaly based on score and threat indicators.

    Args:
        anomaly_score: The z-score based anomaly score.
        threat_indicators: Matched threat intelligence indicators.

    Returns:
        Severity string: "CRITICAL", "HIGH", "MEDIUM", or "LOW".
    """
    # If any threat indicator boosts to CRITICAL, use that
    for indicator in threat_indicators:
        if indicator.get("severity_boost") == "CRITICAL":
            return "CRITICAL"

    # Score-based severity
    if anomaly_score > 4.0:
        return "CRITICAL"
    elif anomaly_score > 3.0:
        return "HIGH"
    elif anomaly_score > 2.0:
        return "MEDIUM"
    else:
        return "LOW"
