"""
GET /v1/compliance              — Posture summary across all active frameworks
GET /v1/compliance/{framework}  — Control-level detail for one framework
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_policy_proxy
from app.schemas.envelope import ok

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("")
async def get_compliance_summary(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get compliance posture summary across all active frameworks."""
    t0 = time.monotonic()
    proxy = get_policy_proxy()
    try:
        result = await proxy.get(
            "/policy/compliance",
            params={"x_org_id": user.organization_id},
            headers=user.auth_headers,
        )
        return ok(
            data=result.get("frameworks", []),
            total=len(result.get("frameworks", [])),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")


@router.get("/{framework}/evidence")
async def get_compliance_evidence(
    framework: str,
    control_id: str = Query(..., description="Control ID to get evidence for"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Download evidence for a specific compliance control."""
    t0 = time.monotonic()
    proxy = get_policy_proxy()
    try:
        result = await proxy.get(
            f"/policy/compliance/{framework}/evidence",
            params={"x_org_id": user.organization_id, "control_id": control_id},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")


@router.get("/{framework}")
async def get_framework_posture(
    framework: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get control-level compliance detail for a specific framework."""
    t0 = time.monotonic()
    proxy = get_policy_proxy()
    try:
        result = await proxy.get(
            f"/policy/compliance/{framework}",
            params={"x_org_id": user.organization_id},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")
