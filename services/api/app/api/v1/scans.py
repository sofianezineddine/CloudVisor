"""
POST /v1/scan         — Trigger full on-demand scan across all accounts (async, returns 202 + job_id)
GET  /v1/scans/{id}   — Get scan status and results summary
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_connector_proxy, get_cspm_proxy
from app.schemas.envelope import ok

router = APIRouter(tags=["scans"])


class FullScanRequest(BaseModel):
    account_ids: list[str] = Field(
        default_factory=list,
        description="Specific account IDs to scan. Empty = scan all connected accounts.",
    )
    scan_type: str = Field(
        default="full",
        description="Scan type: full | quick | compliance",
    )
    priority: str = Field(
        default="normal",
        description="Scan priority: low | normal | high",
    )


@router.post("/scan", status_code=202)
async def trigger_full_scan(
    data: FullScanRequest | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Trigger a full on-demand scan across all connected cloud accounts.

    Returns HTTP 202 Accepted with a `job_id`.
    Poll GET /v1/scans/{job_id} to check scan status and retrieve results.
    """
    t0 = time.monotonic()
    if data is None:
        data = FullScanRequest()

    # Try CSPM service first (primary scan orchestrator), fall back to connector
    cspm = get_cspm_proxy()
    try:
        result = await cspm.post(
            "/api/v1/cspm/scans",
            json={
                "organization_id": user.organization_id,
                "account_ids": data.account_ids,
                "scan_type": data.scan_type,
                "priority": data.priority,
                "triggered_by": user.user_id,
            },
        )
        # Normalise: ensure job_id is present
        if "job_id" not in result and "id" in result:
            result["job_id"] = result["id"]
        if "scan_id" not in result and "id" in result:
            result["scan_id"] = result["id"]
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception:
        pass

    # Fallback: trigger via connector service
    connector = get_connector_proxy()
    try:
        result = await connector.post(
            "/internal/sync/all",
            json={
                "account_ids": data.account_ids,
                "scan_type": data.scan_type,
            },
            headers=user.auth_headers,
        )
        if "job_id" not in result and "id" in result:
            result["job_id"] = result["id"]
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scan service unavailable: {e}")


@router.get("/scans/{scan_id}")
async def get_scan_status(
    scan_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get scan status and results summary.

    The `status` field will be one of: queued | running | completed | failed | cancelled.
    When status is `completed`, a `results_summary` is included.
    """
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(
            f"/api/v1/cspm/scans/{scan_id}",
            params={"org_id": user.organization_id},
        )
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Scan '{scan_id}' not found",
            )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scan service unavailable: {e}")
