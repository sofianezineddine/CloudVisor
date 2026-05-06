from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


class FindingResponse(BaseModel):
    id: str
    organization_id: str
    rule_id: str
    resource_id: str
    resource_name: str | None
    severity: str
    status: str
    title: str
    description: str | None
    remediation: str | None
    provider: str | None
    account_id: str | None
    region: str | None
    first_seen_at: str
    last_seen_at: str
    resolved_at: str | None


class FindingListResponse(BaseModel):
    findings: list[FindingResponse]
    total: int


class FindingUpdateRequest(BaseModel):
    status: str | None = None
    assignee_id: str | None = None


class BulkUpdateRequest(BaseModel):
    finding_ids: list[str]
    status: str | None = None
    assignee_id: str | None = None


class FindingStatsResponse(BaseModel):
    by_severity: dict[str, int]
    by_status: dict[str, int]
    total: int


class SuppressionCreateRequest(BaseModel):
    rule_id: str | None = None
    resource_tag_key: str | None = None
    resource_tag_value: str | None = None
    account_id: str | None = None
    region: str | None = None
    reason: str | None = None
    expires_in_days: int | None = None


class ChannelCreateRequest(BaseModel):
    name: str
    channel_type: str
    config: dict[str, Any]
    severity_filter: list[str] | None = None
    module_filter: list[str] | None = None
    account_filter: list[str] | None = None
    tag_filter: dict[str, str] | None = None


class ChannelResponse(BaseModel):
    id: str
    name: str
    channel_type: str
    severity_filter: list[str]
    module_filter: list[str]
    account_filter: list[str]
    is_active: bool


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
