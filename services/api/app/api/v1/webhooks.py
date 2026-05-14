"""
GET    /v1/webhooks       — List configured webhooks
POST   /v1/webhooks       — Register a new webhook endpoint
DELETE /v1/webhooks/{id}  — Remove a webhook

Outbound webhook payloads are signed with:
  X-CloudVisor-Signature: sha256=<hmac-sha256-hex>
"""

import hashlib
import hmac
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, HttpUrl

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_alert_proxy
from app.schemas.envelope import (
    ok,
    parse_filter_params,
    cursor_to_offset,
    make_next_cursor,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookCreateRequest(BaseModel):
    url: str = Field(..., description="HTTPS endpoint URL to deliver events to")
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable name")
    events: list[str] = Field(
        default_factory=list,
        description=(
            "Event types to subscribe to. Empty list = all events. "
            "Examples: finding.created, finding.updated, incident.created, scan.completed"
        ),
    )
    secret: str | None = Field(
        None,
        min_length=16,
        description=(
            "Optional shared secret used to sign payloads. "
            "CloudVisor will include X-CloudVisor-Signature: sha256=<hmac> on every delivery."
        ),
    )
    severity_filter: list[str] = Field(
        default_factory=list,
        description="Only deliver events for these severities. Empty = all.",
    )
    is_active: bool = Field(default=True, description="Whether the webhook is enabled")
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Custom HTTP headers to include in webhook deliveries",
    )


@router.get("")
async def list_webhooks(
    request: Request,
    cursor: str | None = Query(None, description="Opaque pagination cursor"),
    limit: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all configured webhooks for the authenticated organization."""
    t0 = time.monotonic()
    alert = get_alert_proxy()

    filters = parse_filter_params(str(request.url.query))
    offset, _limit = cursor_to_offset(cursor, limit)

    params: dict[str, Any] = {
        "x_org_id": user.organization_id,
        "limit": limit,
        "offset": offset,
        **filters,
    }

    try:
        result = await alert.get(
            "/internal/webhooks",
            params={
                "organization_id": user.organization_id,
                "limit": limit,
                "offset": offset,
                **filters,
            },
            headers=user.auth_headers,
        )
        webhooks = result.get("webhooks", result if isinstance(result, list) else [])
        total = result.get("total", len(webhooks))
        return ok(
            data=webhooks,
            total=total,
            next_cursor=make_next_cursor(offset, limit, total),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.post("", status_code=201)
async def create_webhook(
    data: WebhookCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Register a new webhook endpoint.

    CloudVisor will POST JSON payloads to the specified URL when matching events occur.
    If a `secret` is provided, each delivery will include:
      X-CloudVisor-Signature: sha256=<hmac-sha256(secret, payload)>
    """
    t0 = time.monotonic()
    alert = get_alert_proxy()
    try:
        result = await alert.post(
            "/internal/webhooks",
            json=data.model_dump(exclude_none=True),
            params={"organization_id": user.organization_id},
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Remove a webhook. CloudVisor will stop delivering events to the endpoint."""
    alert = get_alert_proxy()
    try:
        await alert.delete(
            f"/internal/webhooks/{webhook_id}",
            params={"organization_id": user.organization_id},
            headers=user.auth_headers,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")
