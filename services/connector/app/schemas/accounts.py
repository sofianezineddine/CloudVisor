"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator


# Allowed polling intervals per spec §3.1 (5/15/30/60 min) plus 1 for near-realtime dev
_ALLOWED_POLLING_INTERVALS = {1, 5, 15, 30, 60}


class CloudAccountCreate(BaseModel):
    """Request to create a new cloud account."""

    provider: str = Field(
        ..., pattern="^(aws|azure|gcp|oci)$",
        description="Cloud provider: aws | azure | gcp | oci",
    )
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable account name")
    account_id: str = Field(
        ..., min_length=1, max_length=255,
        description="Provider-native account ID (AWS account ID, Azure subscription ID, etc.)",
    )
    region: str = Field(default="global", max_length=50, description="Default region to scan")
    credentials: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider credentials (access keys, service principal, SA JSON, etc.)",
    )
    polling_interval_minutes: int = Field(
        default=15,
        description=f"Sync interval in minutes. Allowed: {sorted(_ALLOWED_POLLING_INTERVALS)}",
    )

    @field_validator("polling_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v not in _ALLOWED_POLLING_INTERVALS:
            raise ValueError(
                f"polling_interval_minutes must be one of {sorted(_ALLOWED_POLLING_INTERVALS)}"
            )
        return v


class CloudAccountUpdate(BaseModel):
    """Request to update cloud account config."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    region: str | None = Field(default=None, max_length=50)
    polling_interval_minutes: int | None = Field(default=None)

    @field_validator("polling_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int | None) -> int | None:
        if v is not None and v not in _ALLOWED_POLLING_INTERVALS:
            raise ValueError(
                f"polling_interval_minutes must be one of {sorted(_ALLOWED_POLLING_INTERVALS)}"
            )
        return v


class CloudAccountResponse(BaseModel):
    """Response for cloud account."""

    id: str
    organization_id: str
    provider: str
    name: str
    account_id: str
    region: str
    status: str
    sync_status: str
    last_sync_at: datetime | None
    last_successful_sync_at: datetime | None
    consecutive_errors: int
    error_message: str | None
    resource_count: int
    polling_interval_minutes: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class CloudAccountListResponse(BaseModel):
    """List of cloud accounts."""

    accounts: list[CloudAccountResponse]
    total: int


class CloudAccountHealthResponse(BaseModel):
    """Health status for a cloud account."""

    id: str
    status: str
    sync_status: str
    last_sync_at: datetime | None
    last_successful_sync_at: datetime | None
    consecutive_errors: int
    error_message: str | None
    resource_count: int
    error_rate: float


class SyncTriggerRequest(BaseModel):
    """Request to trigger a manual sync."""

    correlation_id: str | None = None


class SyncTriggerResponse(BaseModel):
    """Response for sync trigger."""

    account_id: str
    correlation_id: str
    status: str
    message: str


class OnboardingResponse(BaseModel):
    """Response for onboarding instructions."""

    provider: str
    instructions: str
    template: str | None = None


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
    correlation_id: str | None = None


class CredentialRotateRequest(BaseModel):
    """Request to rotate credentials for a cloud account."""

    credentials: dict[str, Any] = Field(
        ...,
        description="New provider credentials. Same format as CloudAccountCreate.credentials.",
    )


class CredentialRotateResponse(BaseModel):
    """Response for credential rotation."""

    account_id: str
    vault_stored: bool
    connectivity_ok: bool
    warnings: list[str] = Field(default_factory=list)


class ScanHistoryEntry(BaseModel):
    """A single scan history record."""

    id: str
    account_id: str
    sync_type: str
    status: str
    correlation_id: str
    discovered: int
    updated: int
    deleted: int
    errors: int
    duration_seconds: float
    started_at: datetime
    finished_at: datetime | None
    error_details: list[str] = Field(default_factory=list)


class ScanHistoryResponse(BaseModel):
    """Paginated scan history."""

    scans: list[ScanHistoryEntry]
    total: int
    account_id: str
