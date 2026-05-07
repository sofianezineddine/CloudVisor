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
    resource_type: str | None
    tags: list | dict | None = None  # GAP 15: supports dict[str,str] key-value tags
    compliance_mapping: list | None = None
    context: dict | None = None
    assignee_id: str | None = None
    fingerprint: str | None = None
    regression_count: int = 0
    first_seen_at: str
    last_seen_at: str
    resolved_at: str | None
    history: list[dict] | None = None  # GAP 3: finding history entries


class FindingListResponse(BaseModel):
    findings: list[FindingResponse]
    total: int


class FindingUpdateRequest(BaseModel):
    status: str | None = None
    assignee_id: str | None = None
    reason: str | None = None


class BulkUpdateRequest(BaseModel):
    finding_ids: list[str] = Field(..., description="Max 500 finding IDs per bulk operation")
    status: str | None = None
    assignee_id: str | None = None
    reason: str | None = None

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, dict) and "finding_ids" in v:
            if len(v["finding_ids"]) > 500:
                raise ValueError("Bulk operations limited to 500 findings per request")
        return v


class FindingStatsResponse(BaseModel):
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_module: dict[str, int] = Field(default_factory=dict)  # GAP 4: module breakdown
    total: int


class SuppressionCreateRequest(BaseModel):
    rule_id: str | None = None
    resource_tag_key: str | None = None
    resource_tag_value: str | None = None
    account_id: str | None = None
    region: str | None = None
    reason: str | None = None
    # Spec: expiry options 7 days / 30 days / never (None)
    expires_in_days: int | None = Field(
        default=None,
        description="Expiry in days. Spec options: 7, 30, or None (never expires).",
    )


class ChannelCreateRequest(BaseModel):
    name: str
    channel_type: str
    config: dict[str, Any]
    severity_filter: list[str] | None = None
    # Routing filters per spec §3.5
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
