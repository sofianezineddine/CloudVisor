"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class CloudAccountCreate(BaseModel):
    """Request to create a new cloud account."""

    provider: str = Field(..., pattern="^(aws|azure|gcp|oci)$")
    name: str = Field(..., min_length=1, max_length=255)
    account_id: str = Field(..., min_length=1, max_length=255)
    region: str = Field(default="global", max_length=50)
    credentials: dict[str, Any] = Field(default_factory=dict)
    polling_interval_minutes: int = Field(default=15, ge=1, le=60)


class CloudAccountUpdate(BaseModel):
    """Request to update cloud account config."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    region: str | None = Field(default=None, max_length=50)
    polling_interval_minutes: int | None = Field(default=None, ge=1, le=60)


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
