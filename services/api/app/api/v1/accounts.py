"""
GET    /v1/accounts          — List connected cloud accounts
POST   /v1/accounts          — Connect new cloud account
GET    /v1/accounts/{id}     — Account status and health
DELETE /v1/accounts/{id}     — Remove cloud account
POST   /v1/accounts/{id}/scan — Trigger on-demand scan
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_connector_proxy
from app.schemas.envelope import ok

router = APIRouter(prefix="/accounts", tags=["accounts"])


class ConnectAccountRequest(BaseModel):
    provider: str = Field(..., pattern="^(aws|azure|gcp|oci)$")
    name: str = Field(..., min_length=1, max_length=255)
    account_id: str = Field(..., min_length=1)
    region: str = Field(default="global")
    credentials: dict[str, Any] = Field(default_factory=dict)
    polling_interval_minutes: int = Field(default=1, ge=1, le=60)


@router.get("")
async def list_accounts(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all connected cloud accounts for the authenticated organization."""
    t0 = time.monotonic()
    proxy = get_connector_proxy()
    try:
        result = await proxy.get("/internal/accounts", headers=user.auth_headers)
        accounts = result.get("accounts", [])
        return ok(
            data=accounts,
            total=result.get("total", len(accounts)),
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


@router.post("/{account_id}/scan")
async def trigger_scan(
    account_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Trigger an on-demand full scan for a cloud account."""
    t0 = time.monotonic()
    proxy = get_connector_proxy()
    try:
        result = await proxy.post(
            f"/internal/accounts/{account_id}/sync",
            json={},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connector service unavailable: {e}")
