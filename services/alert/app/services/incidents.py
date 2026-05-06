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
        """
        Automatically group findings into incidents per spec:
        1. Same attack path (findings linked by graph traversal)
        2. Same root cause rule on the same account (bulk misconfiguration)
        3. Same resource with multiple findings (compromised resource)
        4. CDR alerts on the same entity within a 1-hour window
        """
        incidents = []

        # Strategy 1: Group by rule + account (bulk misconfiguration)
        by_rule_account = await self._group_by_rule_and_account(organization_id, new_finding_ids)
        for key, findings in by_rule_account.items():
            if len(findings) >= 3:  # At least 3 findings to create incident
                rule_id, account_id = key.split(":", 1)
                incident = await self.create_incident(
                    organization_id=organization_id,
                    title=f"Bulk misconfiguration: {rule_id} in account {account_id}",
                    finding_ids=[f["id"] for f in findings],
                    severity=max([f["severity"] for f in findings], key=self._severity_rank),
                    description=f"Multiple resources ({len(findings)}) affected by the same rule",
                )
                incidents.append(incident)

        # Strategy 2: Group by resource (compromised resource)
        by_resource = await self._group_by_resource(organization_id, new_finding_ids)
        for resource_id, findings in by_resource.items():
            if len(findings) >= 2:  # At least 2 findings on same resource
                incident = await self.create_incident(
                    organization_id=organization_id,
                    title=f"Multiple findings on resource: {resource_id}",
                    finding_ids=[f["id"] for f in findings],
                    severity=max([f["severity"] for f in findings], key=self._severity_rank),
                    description=f"Resource has {len(findings)} security findings",
                )
                incidents.append(incident)

        # Strategy 3: CDR time-window grouping (same entity within 1 hour)
        cdr_incidents = await self._group_cdr_by_time_window(organization_id, new_finding_ids)
        incidents.extend(cdr_incidents)

        return incidents

    async def _group_by_rule_and_account(
        self, organization_id: str, finding_ids: list[str]
    ) -> dict[str, list]:
        """Group findings by rule_id + account_id."""
        result = await self._db.execute(
            select(FindingModel).where(
                FindingModel.id.in_(finding_ids),
                FindingModel.organization_id == organization_id,
            )
        )
        findings = result.scalars().all()

        grouped = {}
        for f in findings:
            key = f"{f.rule_id}:{f.account_id}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append({
                "id": f.id,
                "severity": f.severity,
                "resource_id": f.resource_id,
            })

        return grouped

    async def _group_by_resource(
        self, organization_id: str, finding_ids: list[str]
    ) -> dict[str, list]:
        """Group findings by resource_id."""
        result = await self._db.execute(
            select(FindingModel).where(
                FindingModel.id.in_(finding_ids),
                FindingModel.organization_id == organization_id,
            )
        )
        findings = result.scalars().all()

        grouped = {}
        for f in findings:
            if f.resource_id not in grouped:
                grouped[f.resource_id] = []
            grouped[f.resource_id].append({
                "id": f.id,
                "severity": f.severity,
                "rule_id": f.rule_id,
            })

        return grouped

    async def _group_cdr_by_time_window(
        self, organization_id: str, finding_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Group CDR alerts on the same entity within 1-hour window."""
        result = await self._db.execute(
            select(FindingModel).where(
                FindingModel.id.in_(finding_ids),
                FindingModel.organization_id == organization_id,
                FindingModel.rule_id.like("cdr.%"),  # CDR module findings
            )
        )
        findings = result.scalars().all()

        # Group by resource within 1-hour windows
        time_windows = {}
        for f in findings:
            window_key = f"{f.resource_id}:{f.first_seen_at.strftime('%Y-%m-%d-%H')}"
            if window_key not in time_windows:
                time_windows[window_key] = []
            time_windows[window_key].append(f)

        incidents = []
        for window_key, window_findings in time_windows.items():
            if len(window_findings) >= 2:
                incident = await self.create_incident(
                    organization_id=organization_id,
                    title=f"CDR alert cluster: {window_findings[0].resource_id}",
                    finding_ids=[f.id for f in window_findings],
                    severity=max([f.severity for f in window_findings], key=self._severity_rank),
                    description=f"Multiple CDR alerts within 1-hour window",
                )
                incidents.append(incident)

        return incidents

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
