"""Drift Detection and Anomaly database models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
)

from ..db_helper import Base


class DriftBaselineModel(Base):
    """Stores configuration baselines for drift detection."""

    __tablename__ = "cspm_drift_baselines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    resource_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)
    baseline_config = Column(JSON, nullable=False)
    set_by = Column(String, nullable=True)  # user or "auto"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_drift_baseline_org_resource", "organization_id", "resource_id", unique=True),
    )


class DriftEventModel(Base):
    """Stores individual drift events when configuration deviates from baseline."""

    __tablename__ = "cspm_drift_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    resource_id = Column(String, nullable=False, index=True)
    field_name = Column(String, nullable=False)
    baseline_value = Column(JSON, nullable=True)
    current_value = Column(JSON, nullable=True)
    is_security_relevant = Column(Boolean, default=False)
    severity = Column(String, default="LOW")
    environment = Column(String, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_drift_event_org_resource", "organization_id", "resource_id"),
        Index("ix_drift_event_detected", "detected_at"),
    )


class ConfigChangeHistoryModel(Base):
    """Stores configuration change history with retention policy."""

    __tablename__ = "cspm_config_change_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    resource_id = Column(String, nullable=False, index=True)
    field_name = Column(String, nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)
    retention_expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_config_history_org_resource", "organization_id", "resource_id"),
        Index("ix_config_history_retention", "retention_expires_at"),
    )


class BehavioralBaselineModel(Base):
    """Stores statistical behavioral baselines for anomaly detection."""

    __tablename__ = "cspm_behavioral_baselines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)
    field_name = Column(String, nullable=False)
    mean_value = Column(Float, nullable=False)
    stddev_value = Column(Float, nullable=False)
    sample_count = Column(Integer, default=0)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_behavioral_baseline_org_type", "organization_id", "resource_type"),
    )


class AnomalyFindingModel(Base):
    """Stores detected behavioral anomalies."""

    __tablename__ = "cspm_anomaly_findings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    resource_id = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    deviating_fields = Column(JSON, default=list)  # [{field, value, expected_min, expected_max}]
    severity = Column(String, default="MEDIUM")
    threat_indicators = Column(JSON, default=list)
    correlated_incident_id = Column(String, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_anomaly_org", "organization_id"),
    )


class CorrelationRuleModel(Base):
    """Stores configurable event correlation rules."""

    __tablename__ = "cspm_correlation_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    group_by = Column(JSON, default=list)  # ["resource_id", "account_id"]
    event_types = Column(JSON, default=list)  # ["finding.created", "drift.detected"]
    time_window_seconds = Column(Integer, default=900)  # 15 min
    min_events = Column(Integer, default=2)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CorrelatedAlertModel(Base):
    """Stores correlated alerts generated from matching correlation rules."""

    __tablename__ = "cspm_correlated_alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    correlation_rule_id = Column(String, nullable=False)
    correlation_key = Column(String, nullable=False)  # hash of group_by values
    contributing_event_ids = Column(JSON, default=list)
    combined_severity = Column(String, nullable=False)
    status = Column(String, default="open")  # open, acknowledged, resolved
    suppression_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_correlated_alert_org", "organization_id"),
        Index("ix_correlated_alert_key", "correlation_key"),
    )
