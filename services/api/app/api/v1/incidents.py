"""
GET   /v1/incidents        — List incidents (cursor-based pagination)
GET   /v1/incidents/{id}   — Get incident detail
PATCH /v1/incidents/{id}   — Update incident status or fields
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_alert_proxy
from app.schemas.envelope import (
    ok,
    parse_filter_params,
    parse_sort_param,
    cursor_to_offset,
    make_next_cursor,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentUpdateRequest(BaseModel):
    status: str | None = None
    title: str | None = None
    description: str | None = None
    assignee_id: str | None = None


@router.get("")
async def list_incidents(
    request: Request,
    status: str | None = Query(None, description="open|in_progress|resolved|closed"),
    severity: str | None = Query(None, description="CRITICAL|HIGH|MEDIUM|LOW"),
    cursor: str | None = Query(None, description="Opaque pagination cursor"),
    limit: int = Query(50, ge=1, le=200),
    sort: str | None = Query(None, description="Sort fields, e.g. sort=severity,-created_at"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List incidents for the authenticated organization."""
    t0 = time.monotonic()
    alert = get_alert_proxy()

    filters = parse_filter_params(str(request.url.query))
    if status:
        filters["status"] = status
    if severity:
        filters["severity"] = severity

    offset, _limit = cursor_to_offset(cursor, limit)

    params: dict[str, Any] = {
        "x_org_id": user.organization_id,
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
        result = await alert.get(
            "/internal/incidents",
            params=params,
            headers=user.auth_headers,
        )
        incidents = result.get("incidents", [])
        total = result.get("total", len(incidents))
        return ok(
            data=incidents,
            total=total,
            next_cursor=make_next_cursor(offset, limit, total),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.get("/{incident_id}")
async def get_incident(
    incident_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get incident detail."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.get(
            f"/internal/incidents/{incident_id}",
            headers=user.auth_headers,
        )
        if not result:
            raise HTTPException(status_code=404, detail="Incident not found")
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.patch("/{incident_id}")
async def update_incident(
    incident_id: str,
    data: IncidentUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Update incident status or other fields."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.patch(
            f"/internal/incidents/{incident_id}",
            json=data.model_dump(exclude_none=True),
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")
