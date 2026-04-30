"""Pydantic schemas for Policy service."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class RuleCreateRequest(BaseModel):
    """Create custom rule request."""

    rego_code: str
    title: str
    description: str | None = None
    severity: str = Field(default="MEDIUM", pattern="^(CRITICAL|HIGH|MEDIUM|LOW|INFO)$")
    category: str = Field(default="custom")
    remediation: str | None = None
    compliance_mapping: list[dict[str, Any]] | None = None
    tags: list[str] | None = None


class RuleUpdateRequest(BaseModel):
    """Update custom rule request."""

    rego_code: str | None = None
    title: str | None = None
    description: str | None = None
    remediation: str | None = None
    compliance_mapping: list[dict[str, Any]] | None = None


class RuleResponse(BaseModel):
    """Rule response."""

    id: str
    rule_id: str
    title: str
    description: str | None
    severity: str
    category: str
    provider: str | None
    resource_type: str | None
    remediation: str | None
    version: str
    compliance_mapping: list[dict[str, Any]]
    tags: list[str]
    is_builtin: bool
    is_custom: bool
    is_enabled: bool


class RuleListResponse(BaseModel):
    """Rule list response."""

    rules: list[RuleResponse]
    total: int


class EvaluateRequest(BaseModel):
    """Policy evaluation request."""

    resources: list[dict[str, Any]]
    category: str | None = None
    rule_ids: list[str] | None = None


class EvaluateResponse(BaseModel):
    """Policy evaluation response."""

    findings: list[dict[str, Any]]
    evaluated_count: int


class DryRunRequest(BaseModel):
    """Dry run request."""

    rego_code: str
    resources: list[dict[str, Any]]


class DryRunResponse(BaseModel):
    """Dry run response."""

    success: bool
    findings: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None
    error: str | None = None


class CompliancePostureResponse(BaseModel):
    """Compliance posture response."""

    framework: str
    display_name: str = ""
    total_controls: int
    passing: int
    failing: int
    not_applicable: int
    percentage: float
    controls: list[dict[str, Any]]


class ComplianceSummaryResponse(BaseModel):
    """Compliance summary response."""

    frameworks: list[dict[str, Any]]


class DisableRuleRequest(BaseModel):
    """Disable rule request."""

    reason: str | None = None
    expires_in_days: int | None = None


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
