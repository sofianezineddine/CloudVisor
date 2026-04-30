"""Finding service — ingestion, deduplication, enrichment, Kafka events."""

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import FindingModel, FindingHistoryModel

logger = logging.getLogger(__name__)


class FindingService:
    """Service for managing findings with full lifecycle and Kafka event emission."""

    def __init__(self, db: AsyncSession, redis_client: Any = None, kafka_producer: Any = None):
        self._db = db
        self._redis = redis_client
        self._producer = kafka_producer  # AIOKafkaProducer instance

    # ─── Ingestion ────────────────────────────────────────────────────────────

    async def ingest_finding(self, finding_data: dict[str, Any]) -> dict[str, Any]:
        """
        Ingest a finding from Kafka (finding.raw).
        Deduplicates by fingerprint, enriches, persists, emits finding.created.
        """
        organization_id = finding_data.get("organization_id", "")
        rule_id = finding_data.get("rule_id", "")
        resource_id = finding_data.get("resource_id", "")
        account_id = finding_data.get("account_id", "")

        # Spec: SHA-256(rule_id + resource_id + account_id + organization_id)
        fingerprint = self._compute_fingerprint(organization_id, rule_id, resource_id, account_id)

        existing = await self._get_by_fingerprint(fingerprint)

        if existing:
            return await self._handle_duplicate(existing, finding_data)

        return await self._create_new_finding(fingerprint, finding_data)

    def _compute_fingerprint(
        self, organization_id: str, rule_id: str, resource_id: str, account_id: str = ""
    ) -> str:
        """Deterministic fingerprint per spec: SHA-256(rule_id+resource_id+account_id+org_id)."""
        content = f"{rule_id}:{resource_id}:{account_id}:{organization_id}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def _get_by_fingerprint(self, fingerprint: str) -> FindingModel | None:
        result = await self._db.execute(
            select(FindingModel).where(FindingModel.fingerprint == fingerprint)
        )
        return result.scalar_one_or_none()

    async def _create_new_finding(self, fingerprint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new finding, record history, emit finding.created to Kafka."""
        finding = FindingModel(
            id=str(uuid.uuid4()),
            organization_id=data.get("organization_id", ""),
            rule_id=data.get("rule_id", ""),
            resource_id=data.get("resource_id", ""),
            resource_name=data.get("resource_name"),
            severity=data.get("severity", "MEDIUM"),
            status="open",
            title=data.get("title", ""),
            description=data.get("description"),
            remediation=data.get("remediation"),
            provider=data.get("provider"),
            account_id=data.get("account_id"),
            region=data.get("region"),
            resource_type=data.get("resource_type"),
            tags=data.get("tags", []),
            compliance_mapping=data.get("compliance_mapping", []),
            context=data.get("context", {}),
            fingerprint=fingerprint,
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self._db.add(finding)
        await self._db.commit()
        await self._db.refresh(finding)

        await self._record_history(finding.id, None, "open")

        finding_dict = self._finding_to_dict(finding)

        # ── Emit finding.created to Kafka (Rule 6: emit events for state changes) ──
        await self._emit_kafka("finding.created", finding.id, {
            "event_type": "finding.created",
            "finding_id": finding.id,
            "organization_id": finding.organization_id,
            "rule_id": finding.rule_id,
            "resource_id": finding.resource_id,
            "severity": finding.severity,
            "title": finding.title,
            "provider": finding.provider,
            "account_id": finding.account_id,
            "region": finding.region,
            "resource_type": finding.resource_type,
            "compliance_mapping": finding.compliance_mapping,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # ── Publish to Redis for WebSocket clients ────────────────────────────
        await self._publish_ws_event("finding.created", finding.organization_id, finding_dict)

        logger.info(f"Created finding: {finding.id} [{finding.severity}] {finding.title}")
        return finding_dict

    async def _handle_duplicate(
        self, finding: FindingModel, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update last_seen_at on duplicate, emit finding.seen_again."""
        finding.last_seen_at = datetime.utcnow()
        finding.updated_at = datetime.utcnow()

        # Drift detection: if previously resolved, reopen and increment regression_count
        if finding.status == "resolved":
            old_status = finding.status
            finding.status = "open"
            finding.resolved_at = None
            finding.regression_count = (finding.regression_count or 0) + 1
            await self._record_history(finding.id, old_status, "open", note="Regression detected")
            logger.warning(f"Finding {finding.id} regressed (count={finding.regression_count})")

        await self._db.commit()

        await self._emit_kafka("finding.seen_again", finding.id, {
            "event_type": "finding.seen_again",
            "finding_id": finding.id,
            "organization_id": finding.organization_id,
            "severity": finding.severity,
            "regression_count": finding.regression_count,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return self._finding_to_dict(finding)

    # ─── Status management ────────────────────────────────────────────────────

    async def update_finding_status(
        self,
        finding_id: str,
        new_status: str,
        changed_by: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Update finding status with state machine validation."""
        result = await self._db.execute(select(FindingModel).where(FindingModel.id == finding_id))
        finding = result.scalar_one_or_none()

        if not finding:
            raise ValueError("Finding not found")

        old_status = finding.status

        if not self._is_valid_transition(old_status, new_status):
            raise ValueError(f"Invalid transition: {old_status} → {new_status}")

        finding.status = new_status
        finding.updated_at = datetime.utcnow()

        if new_status == "resolved":
            finding.resolved_at = datetime.utcnow()

        await self._record_history(finding_id, old_status, new_status, changed_by, reason)
        await self._db.commit()

        finding_dict = self._finding_to_dict(finding)

        # Emit appropriate Kafka event
        event_type = {
            "resolved": "finding.resolved",
            "suppressed": "finding.suppressed",
        }.get(new_status, "finding.updated")

        await self._emit_kafka(event_type, finding_id, {
            "event_type": event_type,
            "finding_id": finding_id,
            "organization_id": finding.organization_id,
            "old_status": old_status,
            "new_status": new_status,
            "severity": finding.severity,
            "changed_by": changed_by,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # ── Publish to Redis for WebSocket clients ────────────────────────────
        await self._publish_ws_event(event_type, finding.organization_id, finding_dict)

        return finding_dict

    def _is_valid_transition(self, old: str, new: str) -> bool:
        valid = {
            "open": ["in_progress", "resolved", "suppressed", "accepted_risk"],
            "in_progress": ["open", "resolved"],
            "resolved": ["open"],  # regression
            "suppressed": ["open"],
            "accepted_risk": ["open"],
        }
        return new in valid.get(old, [])

    # ─── Queries ──────────────────────────────────────────────────────────────

    async def get_finding(self, finding_id: str) -> dict[str, Any] | None:
        result = await self._db.execute(select(FindingModel).where(FindingModel.id == finding_id))
        finding = result.scalar_one_or_none()
        return self._finding_to_dict(finding) if finding else None

    async def list_findings(
        self,
        organization_id: str,
        severity: str | None = None,
        status: str | None = None,
        assignee_id: str | None = None,
        module: str | None = None,
        provider: str | None = None,
        account_id: str | None = None,
        region: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = select(FindingModel).where(FindingModel.organization_id == organization_id)

        if severity:
            query = query.where(FindingModel.severity == severity)
        if status:
            query = query.where(FindingModel.status == status)
        if assignee_id:
            query = query.where(FindingModel.assignee_id == assignee_id)
        if provider:
            query = query.where(FindingModel.provider == provider)
        if account_id:
            query = query.where(FindingModel.account_id == account_id)
        if region:
            query = query.where(FindingModel.region == region)

        # Default sort: severity DESC, first_seen_at DESC (most critical first)
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        query = query.order_by(FindingModel.first_seen_at.desc()).limit(limit).offset(offset)

        result = await self._db.execute(query)
        return [self._finding_to_dict(f) for f in result.scalars().all()]

    async def get_stats(self, organization_id: str) -> dict[str, Any]:
        result = await self._db.execute(
            select(FindingModel).where(FindingModel.organization_id == organization_id)
        )
        findings = result.scalars().all()

        by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        by_status = {"open": 0, "in_progress": 0, "resolved": 0, "suppressed": 0, "accepted_risk": 0}

        for f in findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
            by_status[f.status] = by_status.get(f.status, 0) + 1

        return {"by_severity": by_severity, "by_status": by_status, "total": len(findings)}

    # ─── Helpers ──────────────────────────────────────────────────────────────

    async def _record_history(
        self,
        finding_id: str,
        old_status: str | None,
        new_status: str,
        changed_by: str | None = None,
        reason: str | None = None,
        note: str | None = None,
    ) -> None:
        history = FindingHistoryModel(
            id=str(uuid.uuid4()),
            finding_id=finding_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason or note,
            timestamp=datetime.utcnow(),
        )
        self._db.add(history)

    async def _emit_kafka(self, topic: str, key: str, event: dict[str, Any]) -> None:
        """Emit event to Kafka. Non-fatal if producer unavailable."""
        if not self._producer:
            return
        try:
            await self._producer.send_and_wait(
                topic,
                key=key.encode("utf-8") if key else None,
                value=json.dumps(event, default=str).encode("utf-8"),
            )
        except Exception as e:
            logger.error(f"Failed to emit {topic}: {e}")

    async def _publish_ws_event(
        self, event_type: str, org_id: str, finding_data: dict[str, Any]
    ) -> None:
        """Publish finding event to Redis pub/sub for WebSocket clients."""
        if not self._redis:
            return
        try:
            channel = f"events:{org_id}"
            payload = json.dumps({
                "type": event_type,
                "data": finding_data,
                "org_id": org_id,
                "timestamp": datetime.utcnow().isoformat(),
            }, default=str)
            await self._redis.publish(channel, payload)
        except Exception as e:
            logger.error(f"Failed to publish WebSocket event: {e}")

    def _finding_to_dict(self, finding: FindingModel) -> dict[str, Any]:
        return {
            "id": finding.id,
            "organization_id": finding.organization_id,
            "rule_id": finding.rule_id,
            "resource_id": finding.resource_id,
            "resource_name": finding.resource_name,
            "severity": finding.severity,
            "status": finding.status,
            "title": finding.title,
            "description": finding.description,
            "remediation": finding.remediation,
            "provider": finding.provider,
            "account_id": finding.account_id,
            "region": finding.region,
            "resource_type": finding.resource_type,
            "tags": finding.tags,
            "compliance_mapping": finding.compliance_mapping,
            "assignee_id": finding.assignee_id,
            "fingerprint": finding.fingerprint,
            "regression_count": finding.regression_count,
            "first_seen_at": finding.first_seen_at.isoformat(),
            "last_seen_at": finding.last_seen_at.isoformat(),
            "resolved_at": finding.resolved_at.isoformat() if finding.resolved_at else None,
        }
