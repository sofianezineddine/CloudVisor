"""Incident service - grouping findings into incidents."""

import uuid
import logging
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import IncidentModel, FindingModel

logger = logging.getLogger(__name__)


class IncidentService:
    """Service for managing incidents (grouped findings)."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_incident(
        self,
        organization_id: str,
        title: str,
        finding_ids: list[str],
        severity: str = "MEDIUM",
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create an incident from multiple findings."""
        incident = IncidentModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            title=title,
            description=description,
            severity=severity,
            status="open",
            finding_ids=finding_ids,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self._db.add(incident)
        await self._db.commit()
        await self._db.refresh(incident)

        logger.info(f"Created incident: {incident.id} with {len(finding_ids)} findings")

        return self._incident_to_dict(incident)

    async def group_findings(
        self,
        organization_id: str,
        new_finding_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Automatically group findings into incidents."""
        incidents = []

        by_rule = await self._group_by_rule(organization_id, new_finding_ids)

        for rule_id, findings in by_rule.items():
            if len(findings) > 1:
                incident = await self.create_incident(
                    organization_id=organization_id,
                    title=f"Multiple findings from rule: {rule_id}",
                    finding_ids=[f["id"] for f in findings],
                    severity=max([f["severity"] for f in findings], key=self._severity_rank),
                )
                incidents.append(incident)

        return incidents

    async def _group_by_rule(self, organization_id: str, finding_ids: list[str]) -> dict[str, list]:
        result = await self._db.execute(
            select(FindingModel).where(
                FindingModel.id.in_(finding_ids),
                FindingModel.organization_id == organization_id,
            )
        )
        findings = result.scalars().all()

        grouped = {}
        for f in findings:
            if f.rule_id not in grouped:
                grouped[f.rule_id] = []
            grouped[f.rule_id].append({"id": f.id, "severity": f.severity})

        return grouped

    def _severity_rank(self, severity: str) -> int:
        ranks = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
        return ranks.get(severity, 0)

    async def update_incident_status(
        self,
        incident_id: str,
        new_status: str,
    ) -> dict[str, Any]:
        """Update incident status."""
        result = await self._db.execute(
            select(IncidentModel).where(IncidentModel.id == incident_id)
        )
        incident = result.scalar_one_or_none()

        if not incident:
            raise ValueError("Incident not found")

        incident.status = new_status
        incident.updated_at = datetime.utcnow()
        await self._db.commit()

        return self._incident_to_dict(incident)

    async def list_incidents(
        self,
        organization_id: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(IncidentModel).where(IncidentModel.organization_id == organization_id)
        if status:
            query = query.where(IncidentModel.status == status)

        result = await self._db.execute(query)
        return [self._incident_to_dict(i) for i in result.scalars().all()]

    def _incident_to_dict(self, incident: IncidentModel) -> dict[str, Any]:
        return {
            "id": incident.id,
            "organization_id": incident.organization_id,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity,
            "status": incident.status,
            "finding_ids": incident.finding_ids,
            "assignee_id": incident.assignee_id,
            "created_at": incident.created_at.isoformat(),
            "updated_at": incident.updated_at.isoformat(),
        }
