"""
GET    /v1/accounts          — List connected cloud accounts (cursor-based pagination)
POST   /v1/accounts          — Connect new cloud account
GET    /v1/accounts/{id}     — Account status and health
DELETE /v1/accounts/{id}     — Remove cloud account
POST   /v1/accounts/{id}/scan — Trigger on-demand scan (async, returns 202)
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_connector_proxy
from app.schemas.envelope import (
    ok,
    parse_filter_params,
    cursor_to_offset,
    make_next_cursor,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


class ConnectAccountRequest(BaseModel):
    provider: str = Field(..., pattern="^(aws|azure|gcp|oci)$")
    name: str = Field(..., min_length=1, max_length=255)
    account_id: str = Field(..., min_length=1)
    region: str = Field(default="global")
    credentials: dict[str, Any] = Field(default_factory=dict)
    polling_interval_minutes: int = Field(default=15, description="Allowed: 1, 5, 15, 30, 60")


@router.get("")
async def list_accounts(
    request: Request,
    cursor: str | None = Query(None, description="Opaque pagination cursor"),
    limit: int = Query(50, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all connected cloud accounts for the authenticated organization."""
    t0 = time.monotonic()
    proxy = get_connector_proxy()

    filters = parse_filter_params(str(request.url.query))
    offset, _limit = cursor_to_offset(cursor, limit)

    params: dict[str, Any] = {"limit": limit, "offset": offset, **filters}

    try:
        result = await proxy.get("/internal/accounts", params=params, headers=user.auth_headers)
        accounts = result.get("accounts", [])
        total = result.get("total", len(accounts))
        return ok(
            data=accounts,
            total=total,
            next_cursor=make_next_cursor(offset, limit, total),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connector service unavailable: {e}")


# ─── Resources (must be BEFORE /{account_id} to avoid route conflict) ─────────

@router.get("/resources")
async def list_resources(
    request: Request,
    account_id: str | None = Query(None),
    provider: str | None = Query(None),
    resource_type: str | None = Query(None),
    region: str | None = Query(None),
    search: str | None = Query(None),
    is_public: bool | None = Query(None),
    environment: str | None = Query(None),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List discovered resources from the connector service."""
    t0 = time.monotonic()
    proxy = get_connector_proxy()

    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if account_id:
        params["account_id"] = account_id
    if provider:
        params["provider"] = provider
    if resource_type:
        params["resource_type"] = resource_type
    if region:
        params["region"] = region
    if search:
        params["search"] = search
    if is_public is not None:
        params["is_public"] = str(is_public).lower()
    if environment:
        params["environment"] = environment

    try:
        result = await proxy.get("/internal/resources", params=params, headers=user.auth_headers)
        resources = result.get("resources", [])
        total = result.get("total", len(resources))
        return ok(
            data=resources,
            total=total,
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connector service unavailable: {e}")


@router.post("", status_code=201)
async def connect_account(
    data: ConnectAccountRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Connect a new cloud account and trigger initial discovery."""
    t0 = time.monotonic()
    proxy = get_connector_proxy()
    try:
        result = await proxy.post(
            "/internal/accounts",
            json=data.model_dump(),
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connector service unavailable: {e}")


@router.get("/{account_id}")
async def get_account(
    account_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get account status and health."""
    t0 = time.monotonic()
    proxy = get_connector_proxy()
    try:
        result = await proxy.get(
            f"/internal/accounts/{account_id}",
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connector service unavailable: {e}")


@router.delete("/{account_id}", status_code=204)
async def remove_account(
    account_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Remove a cloud account and stop all syncing."""
    proxy = get_connector_proxy()
    try:
        await proxy.delete(f"/internal/accounts/{account_id}", headers=user.auth_headers)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connector service unavailable: {e}")


@router.post("/{account_id}/scan", status_code=202)
async def trigger_scan(
    account_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Trigger an on-demand full scan for a specific cloud account.

    Returns HTTP 202 Accepted with a job_id.
    Poll GET /v1/scans/{job_id} to check scan status.
    """
    t0 = time.monotonic()
    proxy = get_connector_proxy()
    try:
        result = await proxy.post(
            f"/internal/accounts/{account_id}/sync",
            json={},
            headers=user.auth_headers,
        )
        # Normalise: ensure job_id is present
        if "job_id" not in result and "id" in result:
            result["job_id"] = result["id"]
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connector service unavailable: {e}")
