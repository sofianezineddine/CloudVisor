"""
GET    /v1/reports       — List generated reports (cursor-based pagination)
POST   /v1/reports       — Generate new report (async — returns 202 + job ID)
GET    /v1/reports/{id}  — Report status and download URL
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_cspm_proxy
from app.schemas.envelope import (
    ok,
    parse_filter_params,
    parse_sort_param,
    cursor_to_offset,
    make_next_cursor,
)

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportCreateRequest(BaseModel):
    report_type: str = Field(
        ...,
        description="Type of report: findings_export|compliance_summary|executive_summary|asset_inventory",
    )
    framework: str | None = Field(None, description="Compliance framework (for compliance reports)")
    format: str = Field(default="pdf", description="Output format: pdf|csv|json")
    date_from: str | None = Field(None, description="ISO-8601 start date")
    date_to: str | None = Field(None, description="ISO-8601 end date")
    account_ids: list[str] = Field(default_factory=list, description="Scope to specific accounts")
    filters: dict[str, Any] = Field(default_factory=dict, description="Additional report filters")


@router.get("")
async def list_reports(
    request: Request,
    report_type: str | None = Query(None, description="Filter by report type"),
    cursor: str | None = Query(None, description="Opaque pagination cursor"),
    limit: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None, description="Sort fields, e.g. sort=-created_at"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all generated reports for the authenticated organization."""
    t0 = time.monotonic()
    cspm = get_cspm_proxy()

    filters = parse_filter_params(str(request.url.query))
    if report_type:
        filters["report_type"] = report_type

    offset, _limit = cursor_to_offset(cursor, limit)

    params: dict[str, Any] = {
        "org_id": user.organization_id,
        "limit": limit,
        "offset": offset,
        **filters,
    }

    sort_fields = parse_sort_param(sort)
    if sort_fields:
        params["sort"] = ",".join(
            f"-{f}" if d == "desc" else f for f, d in sort_fields
        )

    try:
        result = await cspm.get("/api/v1/cspm/reports", params=params)
        items = result if isinstance(result, list) else result.get("items", [])
        total = len(items) if isinstance(result, list) else result.get("total", len(items))
        return ok(
            data=items,
            total=total,
            next_cursor=make_next_cursor(offset, limit, total),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Report service unavailable: {e}")


@router.post("", status_code=202)
async def create_report(
    data: ReportCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Generate a new report asynchronously.

    Returns HTTP 202 Accepted with a job_id.
    Poll GET /v1/reports/{job_id} to check status and retrieve the download URL.
    """
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.post(
            "/api/v1/cspm/reports",
            json={
                **data.model_dump(exclude_none=True),
                "org_id": user.organization_id,
                "requested_by": user.user_id,
            },
        )
        # Normalise: ensure job_id is present in the response
        if "job_id" not in result and "id" in result:
            result["job_id"] = result["id"]
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Report service unavailable: {e}")


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get report status and download URL.

    The `status` field will be one of: pending | processing | completed | failed.
    When status is `completed`, a `download_url` is included in the response.
    """
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(
            f"/api/v1/cspm/reports/{report_id}",
            params={"org_id": user.organization_id},
        )
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Report '{report_id}' not found",
            )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Report service unavailable: {e}")
