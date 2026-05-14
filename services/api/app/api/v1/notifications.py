"""
GET    /v1/notifications/channels        — List notification channels
POST   /v1/notifications/channels        — Add a notification channel
DELETE /v1/notifications/channels/{id}   — Remove a notification channel
POST   /v1/notifications/test            — Test a notification channel
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_alert_proxy
from app.schemas.envelope import ok

router = APIRouter(prefix="/notifications", tags=["notifications"])


class ChannelCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    channel_type: str = Field(..., description="slack|pagerduty|email|webhook|teams|jira")
    config: dict[str, Any] = Field(..., description="Channel-specific configuration")
    severity_filter: list[str] = Field(
        default_factory=list,
        description="Only notify for these severities. Empty = all severities.",
    )
    # Routing filters per spec §3.5
    module_filter: list[str] = Field(
        default_factory=list,
        description="Only notify for findings from these modules (cspm, cwpp, cdr, etc.).",
    )
    account_filter: list[str] = Field(
        default_factory=list,
        description="Only notify for findings from these cloud account IDs.",
    )
    tag_filter: dict[str, str] = Field(
        default_factory=dict,
        description="Only notify for findings on resources with these tags.",
    )
    is_active: bool = True


class TestChannelRequest(BaseModel):
    channel_id: str | None = None
    channel_type: str | None = None
    config: dict[str, Any] | None = None


@router.get("/channels")
async def list_channels(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all notification channels for the authenticated organization."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.get(
            "/internal/notifications/channels",
            # Alert service expects 'organization_id' as the query param name
            params={"organization_id": user.organization_id},
            headers=user.auth_headers,
        )
        channels = result.get("channels", result if isinstance(result, list) else [])
        return ok(
            data=channels,
            total=len(channels),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.post("/channels", status_code=201)
async def add_channel(
    data: ChannelCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Add a new notification channel."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.post(
            "/internal/notifications/channels",
            json=data.model_dump(),
            # Alert service expects organization_id as query param
            params={"organization_id": user.organization_id},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.delete("/channels/{channel_id}", status_code=204)
async def remove_channel(
    channel_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Remove a notification channel."""
    alert = get_alert_proxy()
    try:
        await alert.delete(
            f"/internal/notifications/channels/{channel_id}",
            headers=user.auth_headers,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.put("/channels/{channel_id}")
async def update_channel(
    channel_id: str,
    data: ChannelCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Update an existing notification channel configuration."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.put(
            f"/internal/notifications/channels/{channel_id}",
            json=data.model_dump(),
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.post("/test")
async def test_channel(
    data: TestChannelRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Send a test notification to verify channel configuration."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.post(
            "/internal/notifications/test",
            json=data.model_dump(exclude_none=True),
            params={"organization_id": user.organization_id},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")
