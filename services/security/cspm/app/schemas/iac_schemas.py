"""Pydantic schemas for IaC Scanner endpoints."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Request Schemas ───────────────────────────────────────────────────────────


class IaCScanRequest(BaseModel):
    """Request body for POST /api/v1/cspm/iac/scan."""

    template_type: str = Field(
        ..., description="One of: terraform, cloudformation, kubernetes, helm"
    )
    content: str = Field(..., description="Raw template content to scan")
    file_path: str = Field(
        default="template", description="Original file path for reporting"
    )
    enforcement_mode: str = Field(
        default="advisory", description="advisory or blocking"
    )


class IaCWebhookConfigRequest(BaseModel):
    """Request body for POST /api/v1/cspm/iac/webhook-configs."""

    git_provider: str = Field(
        ..., description="One of: github, gitlab, bitbucket"
    )
    repository: str = Field(..., description="Full repository name (org/repo)")
    webhook_secret: str = Field(default="", description="Secret for signature verification")
    enforcement_mode: str = Field(default="advisory")
    scan_paths: List[str] = Field(default_factory=list)
    excluded_paths: List[str] = Field(default_factory=list)
    severity_threshold: str = Field(default="HIGH")


# ─── Response Schemas ──────────────────────────────────────────────────────────


class IaCFindingOut(BaseModel):
    """Response schema for a single IaC scan finding."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    scan_id: str
    file_path: str
    line_number: Optional[int] = None
    resource_identifier: str
    resource_type: Optional[str] = None
    rule_id: str
    severity: str
    title: str
    description: Optional[str] = None
    remediation: Optional[str] = None
    is_secret: bool = False
    secret_type: Optional[str] = None
    created_at: Optional[datetime] = None


class IaCScanOut(BaseModel):
    """Response schema for an IaC scan result."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    source_type: str
    git_provider: Optional[str] = None
    repository: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    pull_request_id: Optional[str] = None
    template_type: str
    enforcement_mode: str = "advisory"
    status: str = "running"
    total_files: int = 0
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    passed: Optional[bool] = None
    findings: List[IaCFindingOut] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class IaCWebhookConfigOut(BaseModel):
    """Response schema for a webhook configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    git_provider: str
    repository: str
    enforcement_mode: str = "advisory"
    scan_paths: List[str] = []
    excluded_paths: List[str] = []
    severity_threshold: str = "HIGH"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
