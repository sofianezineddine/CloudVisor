"""Pydantic schemas for Drift Detection endpoints."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Request Schemas ───────────────────────────────────────────────────────────


class DriftBaselineRequest(BaseModel):
    """Request body for POST /api/v1/cspm/drift/baselines."""

    resource_id: str
    resource_type: Optional[str] = None
    baseline_config: Any = Field(..., description="Configuration snapshot to use as baseline")


class CorrelationRuleRequest(BaseModel):
    """Request body for POST /api/v1/cspm/drift/correlation-rules."""

    name: str
    description: Optional[str] = None
    group_by: List[str] = Field(default_factory=list)
    event_types: List[str] = Field(default_factory=list)
    time_window_seconds: int = Field(default=900, ge=60, le=86400)
    min_events: int = Field(default=2, ge=2)


# ─── Response Schemas ──────────────────────────────────────────────────────────


class DriftEventOut(BaseModel):
    """Response schema for a drift event."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    resource_id: str
    field_name: str
    baseline_value: Optional[Any] = None
    current_value: Optional[Any] = None
    is_security_relevant: bool = False
    severity: str = "LOW"
    environment: Optional[str] = None
    detected_at: Optional[datetime] = None


class DriftBaselineOut(BaseModel):
    """Response schema for a drift baseline."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    resource_id: str
    resource_type: str
    baseline_config: Any
    set_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AnomalyOut(BaseModel):
    """Response schema for an anomaly finding."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    resource_id: str
    resource_type: str
    anomaly_score: float
    deviating_fields: List[Any] = []
    severity: str = "MEDIUM"
    threat_indicators: List[Any] = []
    correlated_incident_id: Optional[str] = None
    detected_at: Optional[datetime] = None


class CorrelationRuleOut(BaseModel):
    """Response schema for a correlation rule."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    group_by: List[str] = []
    event_types: List[str] = []
    time_window_seconds: int = 900
    min_events: int = 2
    is_active: bool = True
    created_at: Optional[datetime] = None


class CorrelatedAlertOut(BaseModel):
    """Response schema for a correlated alert."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    correlation_rule_id: str
    correlation_key: str
    contributing_event_ids: List[str] = []
    combined_severity: str
    status: str = "open"
    suppression_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConfigChangeHistoryOut(BaseModel):
    """Response schema for a configuration change history entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    resource_id: str
    field_name: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    changed_at: Optional[datetime] = None
    retention_expires_at: Optional[datetime] = None
