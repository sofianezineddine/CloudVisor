"""
GET    /v1/findings                   — List findings (cursor-based pagination, filter[x]=y, sort=)
GET    /v1/findings/stats             — Aggregated counts by severity, status, module
GET    /v1/findings/{id}              — Finding detail with remediation, compliance, history
PATCH  /v1/findings/{id}             — Update status, assignee, notes
POST   /v1/findings/{id}/suppress    — Suppress with required reason field (min 20 chars)
POST   /v1/findings/{id}/accept-risk — Accept risk with mandatory justification
POST   /v1/findings/bulk             — Bulk status update (max 500 per request)
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_alert_proxy
from app.schemas.envelope import (
    ok,
    parse_filter_params,
    parse_sort_param,
    parse_fields_param,
    cursor_to_offset,
    make_next_cursor,
)

router = APIRouter(prefix="/findings", tags=["findings"])


# ─── Request models ───────────────────────────────────────────────────────────

class FindingUpdateRequest(BaseModel):
    status: str | None = None
    assignee_id: str | None = None
    note: str | None = None


class SuppressRequest(BaseModel):
    reason: str = Field(..., min_length=20, description="Reason must be at least 20 characters")


class AcceptRiskRequest(BaseModel):
    justification: str = Field(
        ..., min_length=10, description="Justification for accepting this risk"
    )


class BulkUpdateRequest(BaseModel):
    finding_ids: list[str] = Field(..., description="Max 500 finding IDs per bulk operation")
    status: str
    reason: str | None = None

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        instance = super().model_validate(obj, *args, **kwargs)
        if len(instance.finding_ids) > 500:
            raise ValueError("Maximum 500 findings per bulk operation")
        return instance


# ─── Routes — static paths MUST come before parameterized paths ───────────────

@router.get("/stats")
async def get_finding_stats(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Aggregated finding counts by severity, status, and module."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.get(
            "/internal/findings/stats",
            params={"x_org_id": user.organization_id},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.get("/metrics")
async def get_finding_metrics(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Pre-aggregated Redis metrics for dashboard (by severity, status, provider, MTTR)."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.get(
            "/internal/findings/metrics",
            params={"x_org_id": user.organization_id},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.get("/sla-violations")
async def get_sla_violations(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get findings that have violated SLA targets (CRITICAL: 4h ack / 24h resolve)."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.get(
            "/internal/findings/sla-violations",
            params={"x_org_id": user.organization_id},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.post("/bulk")
async def bulk_update_findings(
    data: BulkUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Bulk update up to 500 findings at once."""
    t0 = time.monotonic()
    if len(data.finding_ids) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 findings per bulk operation")

    alert = get_alert_proxy()
    try:
        result = await alert.post(
            "/internal/findings/bulk",
            json=data.model_dump(),
            headers={**user.auth_headers, "x_org_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


class SubmitFindingRequest(BaseModel):
    """Direct finding submission from CI/CD tools."""
    rule_id: str
    resource_id: str
    resource_name: str | None = None
    severity: str = "MEDIUM"
    title: str
    description: str | None = None
    remediation: str | None = None
    provider: str | None = None
    account_id: str | None = None
    region: str | None = None
    resource_type: str | None = None
    tags: dict | None = None
    compliance_mapping: list | None = None


@router.post("/submit", status_code=201)
async def submit_finding(
    data: SubmitFindingRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Direct REST submission for CI/CD CLI tools that cannot use Kafka.
    Processes through the same deduplication + enrichment + notification pipeline.
    """
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.post(
            "/internal/findings/submit",
            json=data.model_dump(exclude_none=True),
            params={"x_org_id": user.organization_id},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.get("")
async def list_findings(
    request: Request,
    # Convenience explicit params (also accepted via filter[x]=y)
    severity: str | None = Query(None, description="CRITICAL|HIGH|MEDIUM|LOW|INFO"),
    status: str | None = Query(None, description="open|in_progress|resolved|suppressed|accepted_risk"),
    provider: str | None = Query(None),
    account_id: str | None = Query(None),
    region: str | None = Query(None),
    assignee_id: str | None = Query(None),
    module: str | None = Query(None, description="cspm|cwpp|cdr|ciem|kspm|dspm|cicd"),
    # Cursor-based pagination (spec: NO offset pagination)
    cursor: str | None = Query(None, description="Opaque pagination cursor"),
    limit: int = Query(50, ge=1, le=500),
    # Sorting: sort=severity,-created_at
    sort: str | None = Query(None, description="Sort fields, e.g. sort=severity,-created_at"),
    # Sparse field sets: fields[findings]=id,severity,title
    fields: str | None = Query(None, alias="fields[findings]", description="Comma-separated fields"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List findings for the authenticated organization."""
    t0 = time.monotonic()
    alert = get_alert_proxy()

    # Parse filter[field]=value from raw query string
    filters = parse_filter_params(str(request.url.query))

    # Explicit params override filter[] params
    if severity:
        filters["severity"] = severity
    if status:
        filters["status"] = status
    if provider:
        filters["provider"] = provider
    if account_id:
        filters["account_id"] = account_id
    if region:
        filters["region"] = region
    if assignee_id:
        filters["assignee_id"] = assignee_id
    if module:
        filters["module"] = module

    # Decode cursor → offset
    offset, _limit = cursor_to_offset(cursor, limit)

    params: dict[str, Any] = {
        "x_org_id": user.organization_id,
        "limit": limit,
        "offset": offset,
        **filters,
    }

    # Forward sort
    sort_fields = parse_sort_param(sort)
    if sort_fields:
        params["sort"] = ",".join(
            f"-{f}" if d == "desc" else f for f, d in sort_fields
        )

    try:
        result = await alert.get("/internal/findings", params=params, headers=user.auth_headers)
        findings = result.get("findings", [])
        total = result.get("total", len(findings))

        # Apply sparse field selection
        selected_fields = parse_fields_param(fields, "findings")
        if selected_fields:
            findings = [
                {k: v for k, v in item.items() if k in selected_fields}
                for item in findings
            ]

        return ok(
            data=findings,
            total=total,
            next_cursor=make_next_cursor(offset, limit, total),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.get("/{finding_id}")
async def get_finding(
    finding_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get finding detail with remediation, compliance mappings, and state history."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.get(
            f"/internal/findings/{finding_id}",
            headers=user.auth_headers,
        )
        if not result:
            raise HTTPException(status_code=404, detail="Finding not found")
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.patch("/{finding_id}")
async def update_finding(
    finding_id: str,
    data: FindingUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Update finding status, assignee, or notes."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.patch(
            f"/internal/findings/{finding_id}",
            json=data.model_dump(exclude_none=True),
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.post("/{finding_id}/suppress")
async def suppress_finding(
    finding_id: str,
    data: SuppressRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Suppress a finding with a mandatory reason (min 20 chars)."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.post(
            f"/internal/findings/{finding_id}/suppress",
            json={"reason": data.reason},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.post("/{finding_id}/accept-risk")
async def accept_risk(
    finding_id: str,
    data: AcceptRiskRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Accept risk for a finding with a mandatory justification.

    Spec §3.6: Update status to accepted_risk with justification recorded in history.
    """
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.post(
            f"/internal/findings/{finding_id}/accept-risk",
            json={"justification": data.justification},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.post("/{finding_id}/acknowledge")
async def acknowledge_finding(
    finding_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Acknowledge a finding for SLA tracking.
    Records the time of acknowledgment — used to compute SLA compliance.
    """
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.post(
            f"/internal/findings/{finding_id}/acknowledge",
            json={},
            headers={**user.auth_headers, "X-User-ID": user.user_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")
