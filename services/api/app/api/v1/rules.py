"""
GET  /v1/rules          — List all rules
GET  /v1/rules/{id}     — Rule detail
POST /v1/rules/{id}/disable — Disable a rule for this org
POST /v1/rules/custom   — Create a custom rule
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_policy_proxy
from app.schemas.envelope import ok

router = APIRouter(prefix="/rules", tags=["rules"])


class CustomRuleRequest(BaseModel):
    rego_code: str
    title: str
    description: str | None = None
    severity: str = Field(default="MEDIUM", pattern="^(CRITICAL|HIGH|MEDIUM|LOW|INFO)$")
    category: str = Field(default="custom")
    remediation: str | None = None
    compliance_mapping: list[dict] | None = None
    tags: list[str] | None = None


class DisableRuleRequest(BaseModel):
    reason: str | None = None
    expires_in_days: int | None = None


@router.get("")
async def list_rules(
    category: str | None = Query(None),
    provider: str | None = Query(None),
    severity: str | None = Query(None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all security rules (built-in + custom)."""
    t0 = time.monotonic()
    proxy = get_policy_proxy()
    params: dict[str, Any] = {"x_org_id": user.organization_id}
    if category:
        params["category"] = category
    if provider:
        params["provider"] = provider
    if severity:
        params["severity"] = severity
    try:
        result = await proxy.get("/policy/rules", params=params, headers=user.auth_headers)
        rules = result.get("rules", [])
        return ok(
            data=rules,
            total=result.get("total", len(rules)),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")


@router.get("/{rule_id}")
async def get_rule(
    rule_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get rule detail including metadata and compliance mappings."""
    t0 = time.monotonic()
    proxy = get_policy_proxy()
    try:
        result = await proxy.get(
            f"/policy/rules/{rule_id}",
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")


@router.post("/custom", status_code=201)
async def create_custom_rule(
    data: CustomRuleRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a custom Rego rule for this organization."""
    t0 = time.monotonic()
    proxy = get_policy_proxy()
    try:
        result = await proxy.post(
            "/policy/rules/custom",
            json=data.model_dump(exclude_none=True),
            headers={**user.auth_headers, "x_org_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")


@router.post("/{rule_id}/disable")
async def disable_rule(
    rule_id: str,
    data: DisableRuleRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Disable a built-in rule for this organization."""
    t0 = time.monotonic()
    proxy = get_policy_proxy()
    try:
        result = await proxy.post(
            f"/policy/rules/{rule_id}/disable",
            json=data.model_dump(exclude_none=True),
            headers={**user.auth_headers, "x_org_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")
