"""
GET    /v1/suppressions       — List active suppression rules
POST   /v1/suppressions       — Create a suppression rule
DELETE /v1/suppressions/{id}  — Delete a suppression rule

Spec §3.5 (Alert Pipeline) and §3.6 (Public API):
Suppression rules allow orgs to automatically suppress matching findings.
Criteria: rule_id, resource tag, account, region, time window.
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_alert_proxy
from app.schemas.envelope import ok

router = APIRouter(prefix="/suppressions", tags=["suppressions"])


class SuppressionCreateRequest(BaseModel):
    rule_id: str | None = Field(None, description="Security rule ID to suppress")
    resource_tag_key: str | None = Field(None, description="Tag key to match on resources")
    resource_tag_value: str | None = Field(None, description="Tag value to match on resources")
    account_id: str | None = Field(None, description="Cloud account ID to scope suppression")
    region: str | None = Field(None, description="Cloud region to scope suppression")
    reason: str | None = Field(None, description="Reason for creating this suppression rule")
    # Spec: expiry options 7 days / 30 days / never (None)
    expires_in_days: int | None = Field(
        None,
        description="Expiry in days. Options: 7, 30, or null (never expires).",
    )


@router.get("")
async def list_suppressions(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all active suppression rules for the authenticated organization."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.get(
            "/internal/suppressions",
            params={"organization_id": user.organization_id},
            headers=user.auth_headers,
        )
        rules = result if isinstance(result, list) else result.get("rules", [])
        return ok(
            data=rules,
            total=len(rules),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.post("", status_code=201)
async def create_suppression(
    data: SuppressionCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new suppression rule."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.post(
            "/internal/suppressions",
            json=data.model_dump(exclude_none=True),
            params={"organization_id": user.organization_id},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.delete("/{rule_id}", status_code=204)
async def delete_suppression(
    rule_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Delete a suppression rule."""
    alert = get_alert_proxy()
    try:
        await alert.delete(
            f"/internal/suppressions/{rule_id}",
            headers={**user.auth_headers, "x_org_id": user.organization_id},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")
