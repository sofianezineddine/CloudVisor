"""Incidents API routes for the Alert service."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.alert import IncidentModel

router = APIRouter(prefix="/incidents", tags=["incidents"])


def get_org_id(x_org_id: str = Query(...)) -> str:
    return x_org_id


# GAP 7: Incident lifecycle state machine
# Spec: open → investigating → resolved, open → resolved (direct)
_INCIDENT_VALID_TRANSITIONS: dict[str, list[str]] = {
    "open": ["investigating", "resolved"],
    "investigating": ["resolved", "open"],  # allow re-open from investigating
    "resolved": ["open"],  # allow re-open on regression
}


def _validate_incident_transition(old_status: str, new_status: str) -> None:
    """Raise HTTPException if the transition is not allowed by the incident lifecycle."""
    allowed = _INCIDENT_VALID_TRANSITIONS.get(old_status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid incident status transition: {old_status} → {new_status}. "
                   f"Allowed: {allowed}",
        )


class IncidentUpdateRequest(BaseModel):
    status: str | None = None
    title: str | None = None
    description: str | None = None
    assignee_id: str | None = None


def _incident_to_dict(incident: IncidentModel) -> dict[str, Any]:
    return {
        "id": incident.id,
        "organization_id": incident.organization_id,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "status": incident.status,
        "finding_ids": incident.finding_ids or [],
        "assignee_id": incident.assignee_id,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,  # GAP 12
    }


@router.get("")
async def list_incidents(
    organization_id: str = Depends(get_org_id),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List incidents for an organization."""
    stmt = select(IncidentModel).where(IncidentModel.organization_id == organization_id)

    if status:
        stmt = stmt.where(IncidentModel.status == status)
    if severity:
        stmt = stmt.where(IncidentModel.severity == severity)

    stmt = stmt.order_by(IncidentModel.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    incidents = result.scalars().all()

    return {
        "incidents": [_incident_to_dict(i) for i in incidents],
        "total": len(incidents),
        "offset": offset,
        "limit": limit,
    }


@router.get("/{incident_id}")
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get incident detail."""
    incident = await db.get(IncidentModel, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _incident_to_dict(incident)


@router.patch("/{incident_id}")
async def update_incident(
    incident_id: str,
    data: IncidentUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update incident status or other fields."""
    incident = await db.get(IncidentModel, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if data.status is not None:
        # GAP 7: Enforce incident lifecycle state machine
        _validate_incident_transition(incident.status, data.status)
        incident.status = data.status
        if data.status == "resolved":
            incident.resolved_at = datetime.utcnow()
    if data.title is not None:
        incident.title = data.title
    if data.description is not None:
        incident.description = data.description
    if data.assignee_id is not None:
        incident.assignee_id = data.assignee_id

    incident.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(incident)

    return _incident_to_dict(incident)
