"""Finding service — ingestion, deduplication, enrichment, Kafka events."""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta
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
        
        # Initialize metrics service
        from .metrics import MetricsService
        self._metrics = MetricsService(redis_client) if redis_client else None

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

        # ── Suppression check BEFORE persisting (per spec) ────────────────────
        from ..services.suppressions import SuppressionService
        suppression_service = SuppressionService(self._db)
        
        # Prepare finding dict for suppression check
        temp_finding = {
            "id": "temp",
            "organization_id": organization_id,
            "rule_id": rule_id,
            "resource_id": resource_id,
            "account_id": account_id,
            "region": finding_data.get("region"),
            "tags": finding_data.get("tags", {}),
        }
        
        if await suppression_service.check_suppression(temp_finding):
            logger.info(f"Finding suppressed by rule: {rule_id} on {resource_id}")
            # Create finding in suppressed state
            return await self._create_suppressed_finding(fingerprint, finding_data)

        return await self._create_new_finding(fingerprint, finding_data)

    def _compute_fingerprint(
        self, organization_id: str, rule_id: str, resource_id: str, account_id: str = ""
    ) -> str:
        """Deterministic fingerprint per spec: SHA-256(rule_id+resource_id+account_id+org_id)."""
        content = f"{rule_id}:{resource_id}:{account_id}:{organization_id}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def _get_by_fingerprint(self, fingerprint: str) -> FindingModel | None:
        # GAP 2: Check Redis cache first (key: dedup:{fingerprint}) for p99 < 5ms target
        if self._redis:
            try:
                cached_id = await self._redis.get(f"dedup:{fingerprint}")
                if cached_id:
                    result = await self._db.execute(
                        select(FindingModel).where(FindingModel.id == cached_id)
                    )
                    finding = result.scalar_one_or_none()
                    if finding:
                        return finding
                    # Cache entry stale — fall through to DB
            except Exception as e:
                logger.warning(f"Redis dedup cache read failed: {e}")

        result = await self._db.execute(
            select(FindingModel).where(FindingModel.fingerprint == fingerprint)
        )
        finding = result.scalar_one_or_none()

        # Populate cache on DB hit (TTL: indefinite — evicted on resolve)
        if finding and self._redis:
            try:
                await self._redis.set(f"dedup:{fingerprint}", finding.id)
            except Exception as e:
                logger.warning(f"Redis dedup cache write failed: {e}")

        return finding

    async def _create_new_finding(self, fingerprint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new finding, enrich, record history, emit finding.created to Kafka."""
        finding_id = str(uuid.uuid4())
        
        # ── Enrichment: Query external services per spec ──────────────────────
        enriched_context = await self._enrich_finding(data)
        
        finding = FindingModel(
            id=finding_id,
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
            context=enriched_context,  # Store enriched context
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

        # ── Update metrics counters ────────────────────────────────────────────
        if self._metrics:
            await self._metrics.increment_finding_counter(
                organization_id=finding.organization_id,
                severity=finding.severity,
                status="open",
                provider=finding.provider,
                account_id=finding.account_id,
                region=finding.region,
            )

        logger.info(f"Created finding: {finding.id} [{finding.severity}] {finding.title}")
        return finding_dict

    async def _create_suppressed_finding(self, fingerprint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a finding in suppressed state (matched suppression rule)."""
        finding = FindingModel(
            id=str(uuid.uuid4()),
            organization_id=data.get("organization_id", ""),
            rule_id=data.get("rule_id", ""),
            resource_id=data.get("resource_id", ""),
            resource_name=data.get("resource_name"),
            severity=data.get("severity", "MEDIUM"),
            status="suppressed",
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

        await self._record_history(finding.id, None, "suppressed", note="Auto-suppressed on ingestion")

        # Emit finding.suppressed event
        await self._emit_kafka("finding.suppressed", finding.id, {
            "event_type": "finding.suppressed",
            "finding_id": finding.id,
            "organization_id": finding.organization_id,
            "rule_id": finding.rule_id,
            "resource_id": finding.resource_id,
            "severity": finding.severity,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return self._finding_to_dict(finding)

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
            # GAP 2: Evict Redis dedup cache so the finding can be re-created on regression
            if self._redis:
                try:
                    await self._redis.delete(f"dedup:{finding.fingerprint}")
                except Exception as e:
                    logger.warning(f"Redis dedup cache eviction failed: {e}")

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

        # ── Update metrics counters ────────────────────────────────────────────
        if self._metrics:
            await self._metrics.update_status_counter(
                organization_id=finding.organization_id,
                old_status=old_status,
                new_status=new_status,
            )
            
            # Record resolution time for MTTR
            if new_status == "resolved" and finding.resolved_at:
                time_to_resolve = (finding.resolved_at - finding.first_seen_at).total_seconds() / 3600
                await self._metrics.record_resolution(
                    organization_id=finding.organization_id,
                    severity=finding.severity,
                    time_to_resolve_hours=time_to_resolve,
                )

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
        if not finding:
            return None

        # GAP 3: Include history entries in the detail response
        history_result = await self._db.execute(
            select(FindingHistoryModel)
            .where(FindingHistoryModel.finding_id == finding_id)
            .order_by(FindingHistoryModel.timestamp.asc())
        )
        history_entries = history_result.scalars().all()

        finding_dict = self._finding_to_dict(finding)
        finding_dict["history"] = [
            {
                "id": h.id,
                "old_status": h.old_status,
                "new_status": h.new_status,
                "changed_by": h.changed_by,
                "reason": h.reason,
                "timestamp": h.timestamp.isoformat(),
            }
            for h in history_entries
        ]
        return finding_dict

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
        # Module filter: match rule_id prefix (e.g. "cspm.", "cwpp.", "cdr.")
        if module:
            query = query.where(FindingModel.rule_id.like(f"{module}.%"))

        # Default sort: most recent first
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
        # GAP 4: by_module — group by rule_id prefix (e.g. "cspm", "cwpp", "cdr")
        by_module: dict[str, int] = {}

        for f in findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
            by_status[f.status] = by_status.get(f.status, 0) + 1
            # Extract module prefix from rule_id (e.g. "cspm.s3-public-access" → "cspm")
            module = f.rule_id.split(".")[0] if f.rule_id and "." in f.rule_id else (f.rule_id or "unknown")
            by_module[module] = by_module.get(module, 0) + 1

        return {
            "by_severity": by_severity,
            "by_status": by_status,
            "by_module": by_module,
            "total": len(findings),
        }

    async def get_sla_violations(self, organization_id: str) -> list[dict[str, Any]]:
        """Get findings that have violated SLA targets."""
        result = await self._db.execute(
            select(FindingModel).where(
                FindingModel.organization_id == organization_id,
                FindingModel.status.in_(["open", "in_progress"])
            )
        )
        findings = result.scalars().all()
        
        violations = []
        now = datetime.utcnow()
        
        for finding in findings:
            sla_info = self._compute_sla_status(finding, now)
            if sla_info["acknowledge_violated"] or sla_info["resolve_violated"]:
                violations.append({
                    "finding_id": finding.id,
                    "severity": finding.severity,
                    "title": finding.title,
                    "age_hours": sla_info["age_hours"],
                    "acknowledge_sla_hours": sla_info["acknowledge_sla_hours"],
                    "resolve_sla_hours": sla_info["resolve_sla_hours"],
                    "acknowledge_violated": sla_info["acknowledge_violated"],
                    "resolve_violated": sla_info["resolve_violated"],
                })
        
        return violations

    def _compute_sla_status(self, finding: FindingModel, now: datetime) -> dict[str, Any]:
        """
        Compute SLA status per spec:
        - CRITICAL: ack < 4h, resolve < 24h
        - HIGH: ack < 24h, resolve < 7 days
        - MEDIUM: ack < 7 days, resolve < 30 days
        """
        age = now - finding.first_seen_at
        age_hours = age.total_seconds() / 3600
        
        # SLA targets by severity
        sla_targets = {
            "CRITICAL": {"acknowledge_hours": 4, "resolve_hours": 24},
            "HIGH": {"acknowledge_hours": 24, "resolve_hours": 7 * 24},
            "MEDIUM": {"acknowledge_hours": 7 * 24, "resolve_hours": 30 * 24},
            "LOW": {"acknowledge_hours": None, "resolve_hours": None},
            "INFO": {"acknowledge_hours": None, "resolve_hours": None},
        }
        
        target = sla_targets.get(finding.severity, sla_targets["MEDIUM"])
        
        acknowledge_violated = False
        resolve_violated = False
        
        if target["acknowledge_hours"]:
            if not finding.acknowledged_at and age_hours > target["acknowledge_hours"]:
                acknowledge_violated = True
        
        if target["resolve_hours"]:
            if not finding.resolved_at and age_hours > target["resolve_hours"]:
                resolve_violated = True
        
        return {
            "age_hours": age_hours,
            "acknowledge_sla_hours": target["acknowledge_hours"],
            "resolve_sla_hours": target["resolve_hours"],
            "acknowledge_violated": acknowledge_violated,
            "resolve_violated": resolve_violated,
        }

    async def assign_finding(self, finding_id: str, assignee_id: str) -> dict[str, Any]:
        """GAP 5: Assign a finding to a team member (used by bulk assignment)."""
        result = await self._db.execute(
            select(FindingModel).where(FindingModel.id == finding_id)
        )
        finding = result.scalar_one_or_none()
        if not finding:
            raise ValueError("Finding not found")

        finding.assignee_id = assignee_id
        finding.updated_at = datetime.utcnow()
        await self._db.commit()

        await self._emit_kafka("finding.updated", finding_id, {
            "event_type": "finding.updated",
            "finding_id": finding_id,
            "organization_id": finding.organization_id,
            "assignee_id": assignee_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return self._finding_to_dict(finding)

    async def acknowledge_finding(self, finding_id: str, user_id: str) -> dict[str, Any]:
        """Mark finding as acknowledged (for SLA tracking)."""
        result = await self._db.execute(
            select(FindingModel).where(FindingModel.id == finding_id)
        )
        finding = result.scalar_one_or_none()
        
        if not finding:
            raise ValueError("Finding not found")
        
        if not finding.acknowledged_at:
            finding.acknowledged_at = datetime.utcnow()
            finding.updated_at = datetime.utcnow()
            await self._db.commit()
            
            logger.info(f"Finding {finding_id} acknowledged by {user_id}")
        
        return self._finding_to_dict(finding)

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
            "context": finding.context,  # GAP 10: include enrichment context
            "assignee_id": finding.assignee_id,
            "fingerprint": finding.fingerprint,
            "regression_count": finding.regression_count,
            "first_seen_at": finding.first_seen_at.isoformat(),
            "last_seen_at": finding.last_seen_at.isoformat(),
            "resolved_at": finding.resolved_at.isoformat() if finding.resolved_at else None,
        }

    async def _enrich_finding(self, finding_data: dict[str, Any]) -> dict[str, Any]:
        """
        Enrich finding with context from external services per spec:
        - Asset Graph: asset metadata (name, tags, environment, risk_score)
        - Policy Engine: compliance mappings
        - AIOps: AI risk score and priority
        """
        context = {}
        resource_id = finding_data.get("resource_id")
        organization_id = finding_data.get("organization_id")

        # ── Query Asset Graph Service ─────────────────────────────────────────
        try:
            asset_data = await self._query_asset_graph(resource_id, organization_id)
            if asset_data:
                context["asset"] = {
                    "name": asset_data.get("name"),
                    "tags": asset_data.get("tags", {}),
                    "environment": asset_data.get("environment"),
                    "risk_score": asset_data.get("risk_score"),
                    "is_internet_exposed": asset_data.get("is_internet_exposed"),
                }
        except Exception as e:
            logger.warning(f"Asset Graph enrichment failed: {e}")

        # ── Query Policy Engine for compliance mappings ───────────────────────
        try:
            rule_id = finding_data.get("rule_id")
            compliance_data = await self._query_policy_engine(rule_id, organization_id)
            if compliance_data:
                context["compliance"] = compliance_data
        except Exception as e:
            logger.warning(f"Policy Engine enrichment failed: {e}")

        # ── Query AIOps for AI-computed risk and priority ─────────────────────
        try:
            aiops_data = await self._query_aiops(finding_data)
            if aiops_data:
                context["aiops"] = {
                    "ai_risk_score": aiops_data.get("risk_score"),
                    "priority_rank": aiops_data.get("priority_rank"),
                    "explanation": aiops_data.get("explanation"),
                }
        except Exception as e:
            logger.warning(f"AIOps enrichment failed: {e}")

        context["enriched_at"] = datetime.utcnow().isoformat()
        return context

    async def _query_asset_graph(self, resource_id: str, org_id: str) -> dict[str, Any] | None:
        """Query Asset Graph service for resource metadata."""
        if not resource_id:
            return None
        
        try:
            import httpx
            import os
            graph_url = os.getenv("GRAPH_SERVICE_URL", "http://graph:8001")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{graph_url}/internal/assets/{resource_id}",
                    headers={"X-Org-ID": org_id},
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.debug(f"Asset Graph query failed: {e}")
        
        return None

    async def _query_policy_engine(self, rule_id: str, org_id: str) -> dict[str, Any] | None:
        """Query Policy Engine for compliance mappings."""
        if not rule_id:
            return None
        
        try:
            import httpx
            import os
            policy_url = os.getenv("POLICY_SERVICE_URL", "http://policy:8003")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{policy_url}/internal/rules/{rule_id}/compliance",
                    headers={"X-Org-ID": org_id},
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.debug(f"Policy Engine query failed: {e}")
        
        return None

    async def _query_aiops(self, finding_data: dict[str, Any]) -> dict[str, Any] | None:
        """Query AIOps service for AI-computed risk score."""
        try:
            import httpx
            import os
            aiops_url = os.getenv("AIOPS_SERVICE_URL", "http://aiops:8010")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{aiops_url}/internal/risk/compute",
                    json=finding_data,
                    headers={"X-Org-ID": finding_data.get("organization_id", "")},
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.debug(f"AIOps query failed: {e}")
        
        return None
