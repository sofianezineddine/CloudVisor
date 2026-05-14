"""Pydantic schemas for Policy Engine endpoints."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Request Schemas ───────────────────────────────────────────────────────────


class CustomRuleRequest(BaseModel):
    """Request body for POST /api/v1/cspm/policies/rules."""

    rule_id: str = Field(..., description="User-defined rule identifier")
    name: str
    description: Optional[str] = None
    rego_content: str = Field(..., description="Rego policy source code")


class PolicyHierarchyRequest(BaseModel):
    """Request body for POST /api/v1/cspm/policies/hierarchy."""

    level: str = Field(..., description="One of: organization, team, project")
    level_id: str = Field(..., description="ID of the org, team, or project")
    rule_id: str
    enforcement_mode: str = Field(
        default="alert", description="One of: alert, block, auto_remediate"
    )
    is_override: bool = False
    override_justification: Optional[str] = None


class PolicyExceptionRequest(BaseModel):
    """Request body for POST /api/v1/cspm/policies/exceptions."""

    rule_id: str
    resource_id: str
    justification: str = Field(..., min_length=1)
    expires_at: datetime


class RuleTestRequest(BaseModel):
    """Request body for POST /api/v1/cspm/policies/rules/{rule_id}/test."""

    input_data: Any = Field(..., description="Sample input to evaluate the rule against")


# ─── Response Schemas ──────────────────────────────────────────────────────────


class CustomRuleOut(BaseModel):
    """Response schema for a custom Rego rule."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    rule_id: str
    name: str
    description: Optional[str] = None
    rego_content: str
    version: int = 1
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RuleVersionOut(BaseModel):
    """Response schema for a rule version history entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_id: str
    organization_id: str
    version: int
    rego_content: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


class PolicyHierarchyOut(BaseModel):
    """Response schema for a policy hierarchy assignment."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    level: str
    level_id: str
    rule_id: str
    enforcement_mode: str = "alert"
    is_override: bool = False
    override_justification: Optional[str] = None
    overridden_by: Optional[str] = None
    overridden_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PolicyExceptionOut(BaseModel):
    """Response schema for a policy exception."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    rule_id: str
    resource_id: str
    justification: str
    granted_by: str
    expires_at: datetime
    is_active: bool = True
    created_at: Optional[datetime] = None


class PolicyAuditLogOut(BaseModel):
    """Response schema for a policy audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    action: str
    rule_id: Optional[str] = None
    resource_id: Optional[str] = None
    actor: str
    details: Any = {}
    timestamp: Optional[datetime] = None


class RuleTestOut(BaseModel):
    """Response schema for a rule test execution result."""

    rule_id: str
    passed: bool
    violations: List[str] = []
    error: Optional[str] = None
