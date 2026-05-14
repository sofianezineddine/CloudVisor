"""Pydantic schemas for IAM Analysis endpoints."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Request Schemas ───────────────────────────────────────────────────────────


class IAMAnalyzeRequest(BaseModel):
    """Request body for POST /api/v1/cspm/iam/analyze."""

    account_id: str
    lookback_days: int = Field(default=90, ge=1, le=365)
    include_escalation_paths: bool = True


# ─── Response Schemas ──────────────────────────────────────────────────────────


class IAMIdentityOut(BaseModel):
    """Response schema for a single IAM identity analysis result."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    identity_arn: str
    identity_type: str
    provider: str
    account_id: str
    granted_permissions: List[str] = []
    used_permissions: List[str] = []
    excess_permissions: List[str] = []
    excess_ratio: float = 0.0
    is_dormant: bool = False
    last_activity_at: Optional[datetime] = None
    has_mfa: bool = True
    is_admin: bool = False
    risk_score: int = 0
    recommended_policy: Optional[Any] = None
    lookback_days: int = 90
    analyzed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IAMIdentityListOut(BaseModel):
    """Paginated list response for IAM identities."""

    items: List[IAMIdentityOut]
    total: int = 0
    page: int = 1
    page_size: int = 20


class EscalationPathOut(BaseModel):
    """Response schema for a privilege escalation path."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    source_identity: str
    target_identity: str
    path_hops: int
    path_details: List[Any] = []
    target_privilege_level: str
    severity: str
    pattern_ids: List[str] = []
    discovered_at: Optional[datetime] = None


class CrossAccountTrustOut(BaseModel):
    """Response schema for a cross-account trust relationship."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    source_account_id: str
    target_account_id: str
    trusted_principal: str
    trust_conditions: Any = {}
    has_external_id: bool = False
    has_wildcard_principal: bool = False
    is_overly_permissive: bool = False
    risk_score: int = 0
    discovered_at: Optional[datetime] = None


class ServiceAccountOut(BaseModel):
    """Response schema for a service account risk analysis."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    account_id: str
    service_account_id: str
    permission_breadth: int = 0
    resource_scope: List[str] = []
    intended_scope: List[str] = []
    has_scope_violation: bool = False
    last_key_rotation: Optional[datetime] = None
    key_age_days: int = 0
    risk_score: int = 0
    analyzed_at: Optional[datetime] = None


class DormantIdentityOut(BaseModel):
    """Response schema for a dormant identity."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    identity_arn: str
    identity_type: str
    provider: str
    account_id: str
    last_activity_at: Optional[datetime] = None
    has_mfa: bool = True
    is_admin: bool = False
    risk_score: int = 0
    excess_ratio: float = 0.0
    analyzed_at: Optional[datetime] = None
