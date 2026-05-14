"""Webhook management routes for the Alert service.

Webhooks allow organizations to receive real-time event payloads at their
HTTPS endpoints. Payloads are signed with HMAC-SHA256 using the optional secret.
"""

import hashlib
import hmac
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models import WebhookModel

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., description="HTTPS endpoint URL")
    events: list[str] = Field(default_factory=list, description="Empty = all events")
    secret: str | None = Field(None, min_length=16, description="HMAC-SHA256 signing secret")
    severity_filter: list[str] = Field(default_factory=list, description="Empty = all severities")
    is_active: bool = True
    org_id: str | None = None
    created_by: str | None = None


def _webhook_to_dict(wh: WebhookModel) -> dict[str, Any]:
    return {
        "id": wh.id,
        "organization_id": wh.organization_id,
        "name": wh.name,
        "url": wh.url,
        "events": wh.events or [],
        "severity_filter": wh.severity_filter or [],
        "is_active": wh.is_active,
        "created_by": wh.created_by,
        "created_at": wh.created_at.isoformat() if wh.created_at else None,
        "updated_at": wh.updated_at.isoformat() if wh.updated_at else None,
    }


@router.get("")
async def list_webhooks(
    organization_id: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all configured webhooks for an organization."""
    result = await db.execute(
        select(WebhookModel)
        .where(WebhookModel.organization_id == organization_id)
        .order_by(WebhookModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    webhooks = result.scalars().all()
    return {
        "webhooks": [_webhook_to_dict(wh) for wh in webhooks],
        "total": len(webhooks),
    }


@router.post("", status_code=201)
async def create_webhook(
    data: WebhookCreateRequest,
    organization_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Register a new webhook endpoint."""
    # Validate URL is HTTPS
    if not data.url.startswith("https://") and not data.url.startswith("http://localhost"):
        raise HTTPException(
            status_code=400,
            detail="Webhook URL must use HTTPS (http://localhost is allowed for development)",
        )

    now = datetime.utcnow()
    wh = WebhookModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=data.name,
        url=data.url,
        secret=data.secret,
        events=data.events,
        severity_filter=data.severity_filter,
        is_active=data.is_active,
        created_by=data.created_by,
        created_at=now,
        updated_at=now,
    )
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return _webhook_to_dict(wh)


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str,
    organization_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a webhook endpoint."""
    result = await db.execute(
        select(WebhookModel).where(
            WebhookModel.id == webhook_id,
            WebhookModel.organization_id == organization_id,
        )
    )
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(wh)
    await db.commit()
