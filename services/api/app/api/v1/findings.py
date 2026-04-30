"""
GET    /v1/findings          — List findings with full filter support
GET    /v1/findings/{id}     — Finding detail with remediation and compliance
PATCH  /v1/findings/{id}     — Update status
POST   /v1/findings/{id}/suppress  — Suppress with reason
POST   /v1/findings/bulk     — Bulk status update (max 500)
GET    /v1/findings/stats    — Aggregated counts
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_alert_proxy
from app.schemas.envelope import ok

router = APIRouter(prefix="/findings", tags=["findings"])


class FindingUpdateRequest(BaseModel):
    status: str | None = None
    assignee_id: str | None = None
    note: str | None = None


class SuppressRequest(BaseModel):
    reason: str = Field(..., min_length=20, description="Reason must be at least 20 characters")


class BulkUpdateRequest(BaseModel):
    finding_ids: list[str] = Field(..., max_length=500)
    status: str
    reason: str | None = None


@router.get("/stats")
async def get_finding_stats(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Aggregated finding counts by severity and status."""
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


@router.get("")
async def list_findings(
    severity: str | None = Query(None, description="CRITICAL|HIGH|MEDIUM|LOW|INFO"),
    status: str | None = Query(None, description="open|in_progress|resolved|suppressed|accepted_risk"),
    provider: str | None = Query(None),
    account_id: str | None = Query(None),
    region: str | None = Query(None),
    assignee_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List findings for the authenticated organization."""
    t0 = time.monotonic()
    alert = get_alert_proxy()

    params: dict[str, Any] = {
        "x_org_id": user.organization_id,
        "limit": limit,
        "offset": offset,
    }
    if severity:
        params["severity"] = severity
    if status:
        params["status"] = status
    if provider:
        params["provider"] = provider
    if account_id:
        params["account_id"] = account_id
    if region:
        params["region"] = region
    if assignee_id:
        params["assignee_id"] = assignee_id

    try:
        result = await alert.get("/internal/findings", params=params, headers=user.auth_headers)
        findings = result.get("findings", [])
        return ok(
            data=findings,
            total=result.get("total", len(findings)),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.get("/{finding_id}")
async def get_finding(
    finding_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get finding detail with remediation and compliance mappings."""
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
    """Update finding status or assignee."""
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
        result = await alert.patch(
            f"/internal/findings/{finding_id}",
            json={"status": "suppressed", "reason": data.reason},
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
