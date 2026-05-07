"""
GET /v1/posture/score  — Overall security posture score (0–100) with trend

Spec §3.6 Dashboard page: "Overall security posture score (0–100) with trend vs. last 30 days"
This endpoint aggregates posture data from the CSPM service.
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_cspm_proxy
from app.schemas.envelope import ok

router = APIRouter(prefix="/posture", tags=["posture"])


@router.get("/score")
async def get_posture_score(
    account_id: str | None = Query(None, description="Scope to a specific cloud account"),
    provider: str | None = Query(None, description="Scope to a specific cloud provider"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get the overall security posture score (0–100) with trend vs. last 30 days.

    The score is a weighted average of compliance across all active frameworks,
    adjusted for open finding severity. 100 = fully compliant, 0 = critical risk.
    """
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id}
    if account_id:
        params["account_id"] = account_id
    if provider:
        params["provider"] = provider
    try:
        result = await cspm.get("/api/v1/cspm/posture", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")
