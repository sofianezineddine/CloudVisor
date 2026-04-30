"""
CSPM Scan Executor — pulls resources from connector DB, evaluates them
against policy rules, and populates cspm_resource_posture + cspm_findings.
"""
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models_db import (
    CSPMComplianceResultModel,
    CSPMFindingModel,
    CSPMPostureSnapshotModel,
    CSPMResourcePostureModel,
    CSPMScanModel,
)
from .risk_scorer import compute_risk_score

logger = logging.getLogger(__name__)

POLICY_SERVICE_URL = os.environ.get("POLICY_SERVICE_URL", "http://cv-policy:8003")

# Compliance framework → rule_id mapping (rules that cover each framework)
COMPLIANCE_RULE_MAP: dict[str, list[str]] = {
    "CIS-AWS": [
        "aws-s3-public-access", "aws-s3-encryption", "aws-s3-logging", "aws-s3-versioning",
        "aws-iam-root-mfa", "aws-iam-mfa-all-users", "aws-iam-access-key-rotation",
        "aws-iam-password-policy", "aws-iam-wildcard-policy",
        "aws-sg-unrestricted-ssh", "aws-sg-unrestricted-rdp", "aws-sg-unrestricted-all",
        "aws-vpc-flow-logs", "aws-cloudtrail-disabled", "aws-cloudtrail-multiregion",
        "aws-cloudtrail-log-validation", "aws-cloudtrail-s3-public",
        "aws-rds-publicly-accessible", "aws-rds-encryption", "aws-rds-backup-disabled",
        "aws-kms-key-rotation", "aws-ec2-imdsv2", "aws-ec2-public-ip", "aws-eks-endpoint-public",
    ],
    "SOC2": [
        "aws-s3-public-access", "aws-s3-encryption", "aws-s3-logging",
        "aws-iam-root-mfa", "aws-iam-mfa-all-users", "aws-iam-access-key-rotation",
        "aws-sg-unrestricted-ssh", "aws-sg-unrestricted-rdp",
        "aws-vpc-flow-logs", "aws-cloudtrail-disabled", "aws-cloudtrail-log-validation",
        "aws-rds-publicly-accessible", "aws-rds-encryption",
        "aws-sqs-public-policy", "aws-sns-public-policy",
    ],
    "PCI-DSS": [
        "aws-s3-public-access", "aws-s3-encryption",
        "aws-iam-root-mfa", "aws-iam-mfa-all-users", "aws-iam-access-key-rotation",
        "aws-iam-password-policy", "aws-iam-wildcard-policy",
        "aws-sg-unrestricted-ssh", "aws-sg-unrestricted-rdp", "aws-sg-unrestricted-all",
        "aws-cloudtrail-disabled", "aws-cloudtrail-log-validation", "aws-cloudtrail-s3-public",
        "aws-rds-publicly-accessible", "aws-rds-encryption",
        "aws-ebs-encryption", "aws-secretsmanager-rotation", "aws-dynamodb-encryption",
    ],
    "HIPAA": [
        "aws-s3-encryption", "aws-rds-encryption", "aws-ebs-encryption",
        "aws-cloudtrail-disabled", "aws-dynamodb-encryption",
    ],
    "NIST-800-53": [
        "aws-iam-root-mfa", "aws-iam-mfa-all-users", "aws-vpc-flow-logs",
        "aws-cloudtrail-disabled", "aws-kms-key-rotation", "aws-ec2-imdsv2",
        "aws-eks-endpoint-public", "aws-sqs-public-policy", "aws-sns-public-policy",
    ],
    "ISO27001": [
        "aws-s3-public-access", "aws-s3-encryption", "aws-iam-root-mfa",
        "aws-iam-mfa-all-users", "aws-sg-unrestricted-ssh", "aws-cloudtrail-disabled",
        "aws-rds-encryption", "aws-kms-key-rotation",
    ],
    "GDPR": [
        "aws-s3-public-access", "aws-s3-encryption", "aws-rds-encryption",
        "aws-ebs-encryption", "aws-dynamodb-encryption", "aws-cloudtrail-disabled",
    ],
}


def _fingerprint(rule_id: str, resource_id: str, account_id: str, org_id: str) -> str:
    raw = f"{rule_id}{resource_id}{account_id}{org_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def _evaluate_resource(resource: dict[str, Any], org_id: str) -> list[dict]:
    """Call Policy service /internal/policy/evaluate for one resource."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{POLICY_SERVICE_URL}/internal/policy/evaluate",
                json={"resources": [resource], "org_id": org_id},
                headers={"X-Org-ID": org_id},
            )
            if resp.status_code == 200:
                return resp.json().get("findings", [])
            logger.warning(f"Policy evaluate {resp.status_code} for {resource.get('id')}")
            return []
    except Exception as e:
        logger.error(f"Policy evaluate error: {e}")
        return []


async def _publish_finding_event(
    kafka_producer: Any,
    topic: str,
    payload: dict,
) -> None:
    """Publish a finding event to Kafka (graph service listens)."""
    if not kafka_producer:
        return
    try:
        await kafka_producer.send_and_wait(
            topic,
            json.dumps(payload).encode("utf-8"),
        )
    except Exception as e:
        logger.warning(f"Kafka publish to {topic} failed: {e}")


async def run_scan(
    db: AsyncSession,
    scan_id: str,
    organization_id: str,
    account_id: str | None = None,
    kafka_producer: Any = None,
) -> None:
    """
    Full scan execution:
    1. Load resources from connector_discovered_resources
    2. Evaluate each against Policy service
    3. Upsert cspm_resource_posture
    4. Upsert cspm_findings (deduplicate by fingerprint, detect regressions)
    5. Emit finding.created / finding.resolved Kafka events
    6. Populate cspm_compliance_results
    7. Save posture snapshot
    8. Mark scan completed
    """
    logger.info(f"Starting CSPM scan {scan_id} for org {organization_id}")
    findings_created = 0
    findings_resolved = 0
    resources_scanned = 0

    try:
        # ── 1. Load resources ─────────────────────────────────────────────────
        query = text(
            """
            SELECT
                id, cloud_resource_id, provider, account_id, region,
                resource_type, name, tags, raw, organization_id,
                is_public, environment
            FROM connector_discovered_resources
            WHERE organization_id = :org_id
              AND is_deleted = false
            """
            + (" AND account_id = :account_id" if account_id else "")
        )
        params: dict = {"org_id": organization_id}
        if account_id:
            params["account_id"] = account_id

        result = await db.execute(query, params)
        resources = result.mappings().all()
        logger.info(f"Scan {scan_id}: {len(resources)} resources to evaluate")

        # ── 2. Evaluate each resource ─────────────────────────────────────────
        for row in resources:
            resources_scanned += 1
            resource_id = str(row["cloud_resource_id"] or row["id"])
            acc_id = str(row["account_id"] or "")
            org_id_str = str(row["organization_id"] or organization_id)

            resource_dict = {
                "id": resource_id,
                "cloud_resource_id": resource_id,
                "resource_type": row["resource_type"] or "",
                "name": row["name"] or "",
                "provider": row["provider"] or "",
                "account_id": acc_id,
                "region": row["region"] or "",
                "organization_id": org_id_str,
                "is_public": bool(row["is_public"]),
                "environment": row["environment"] or "unknown",
                "tags": row["tags"] or {},
                "raw": row["raw"] or {},
            }

            policy_findings = await _evaluate_resource(resource_dict, org_id_str)

            # ── 3. Upsert resource posture ────────────────────────────────────
            sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for f in policy_findings:
                sev = f.get("severity", "MEDIUM").upper()
                sev_counts[sev] = sev_counts.get(sev, 0) + 1

            risk_score = compute_risk_score(
                policy_findings,
                is_internet_exposed=bool(row["is_public"]),
                environment=row["environment"] or "unknown",
            )

            existing_posture = (await db.execute(
                select(CSPMResourcePostureModel).where(
                    CSPMResourcePostureModel.organization_id == org_id_str,
                    CSPMResourcePostureModel.resource_id == resource_id,
                )
            )).scalar_one_or_none()

            if existing_posture:
                existing_posture.risk_score = risk_score
                existing_posture.critical_count = sev_counts["CRITICAL"]
                existing_posture.high_count = sev_counts["HIGH"]
                existing_posture.medium_count = sev_counts["MEDIUM"]
                existing_posture.low_count = sev_counts["LOW"]
                existing_posture.is_internet_exposed = bool(row["is_public"])
                existing_posture.last_scanned_at = datetime.utcnow()
                existing_posture.updated_at = datetime.utcnow()
                existing_posture.environment = row["environment"] or "unknown"
            else:
                db.add(CSPMResourcePostureModel(
                    id=str(uuid.uuid4()),
                    organization_id=org_id_str,
                    resource_id=resource_id,
                    resource_name=row["name"] or resource_id,
                    resource_type=row["resource_type"] or "",
                    provider=row["provider"] or "",
                    account_id=acc_id,
                    region=row["region"] or "",
                    environment=row["environment"] or "unknown",
                    risk_score=risk_score,
                    is_internet_exposed=bool(row["is_public"]),
                    critical_count=sev_counts["CRITICAL"],
                    high_count=sev_counts["HIGH"],
                    medium_count=sev_counts["MEDIUM"],
                    low_count=sev_counts["LOW"],
                    last_scanned_at=datetime.utcnow(),
                ))

            # ── 4. Upsert findings + detect regressions ───────────────────────
            current_fps: set[str] = set()
            for finding in policy_findings:
                fp = _fingerprint(finding.get("rule_id", ""), resource_id, acc_id, org_id_str)
                current_fps.add(fp)

                existing_finding = (await db.execute(
                    select(CSPMFindingModel).where(CSPMFindingModel.fingerprint == fp)
                )).scalar_one_or_none()

                if existing_finding:
                    if existing_finding.status == "resolved":
                        # Regression — finding came back
                        existing_finding.status = "open"
                        existing_finding.regression_count += 1
                        existing_finding.resolved_at = None
                        # Emit drift/regression event
                        await _publish_finding_event(kafka_producer, "finding.regressed", {
                            "fingerprint": fp,
                            "finding_id": existing_finding.id,
                            "rule_id": existing_finding.rule_id,
                            "resource_id": resource_id,
                            "organization_id": org_id_str,
                            "regression_count": existing_finding.regression_count,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                    existing_finding.last_seen_at = datetime.utcnow()
                    existing_finding.updated_at = datetime.utcnow()
                else:
                    new_finding = CSPMFindingModel(
                        id=str(uuid.uuid4()),
                        organization_id=org_id_str,
                        fingerprint=fp,
                        rule_id=finding.get("rule_id", ""),
                        title=finding.get("title", ""),
                        description=finding.get("description", ""),
                        severity=finding.get("severity", "MEDIUM").upper(),
                        status="open",
                        resource_id=resource_id,
                        resource_name=row["name"] or resource_id,
                        resource_type=row["resource_type"] or "",
                        provider=row["provider"] or "",
                        account_id=acc_id,
                        region=row["region"] or "",
                        remediation=finding.get("remediation", ""),
                        compliance_mapping=finding.get("compliance_mapping", []),
                        first_seen_at=datetime.utcnow(),
                        last_seen_at=datetime.utcnow(),
                    )
                    db.add(new_finding)
                    findings_created += 1
                    # ── 5a. Emit finding.created to graph service ─────────────
                    await _publish_finding_event(kafka_producer, "finding.created", {
                        "finding_id": new_finding.id,
                        "fingerprint": fp,
                        "rule_id": finding.get("rule_id", ""),
                        "title": finding.get("title", ""),
                        "severity": finding.get("severity", "MEDIUM").upper(),
                        "resource_id": resource_id,
                        "resource_type": row["resource_type"] or "",
                        "organization_id": org_id_str,
                        "account_id": acc_id,
                        "provider": row["provider"] or "",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            # Auto-resolve findings that no longer fire
            open_findings = (await db.execute(
                select(CSPMFindingModel).where(
                    CSPMFindingModel.organization_id == org_id_str,
                    CSPMFindingModel.resource_id == resource_id,
                    CSPMFindingModel.status == "open",
                )
            )).scalars().all()

            for f in open_findings:
                if f.fingerprint not in current_fps:
                    f.status = "resolved"
                    f.resolved_at = datetime.utcnow()
                    f.updated_at = datetime.utcnow()
                    findings_resolved += 1
                    # ── 5b. Emit finding.resolved to graph service ────────────
                    await _publish_finding_event(kafka_producer, "finding.resolved", {
                        "finding_id": f.id,
                        "fingerprint": f.fingerprint,
                        "rule_id": f.rule_id,
                        "resource_id": resource_id,
                        "organization_id": org_id_str,
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            # Commit every 20 resources
            if resources_scanned % 20 == 0:
                await db.commit()
                logger.info(f"Scan {scan_id}: {resources_scanned}/{len(resources)} done")

        # ── 6. Populate compliance results ────────────────────────────────────
        await _update_compliance_results(db, organization_id)

        # ── 7. Save posture snapshot ──────────────────────────────────────────
        await _save_posture_snapshot(db, organization_id)

        # Final commit
        await db.commit()

        # ── 8. Mark scan completed ────────────────────────────────────────────
        scan = (await db.execute(
            select(CSPMScanModel).where(CSPMScanModel.id == scan_id)
        )).scalar_one_or_none()

        if scan:
            scan.status = "completed"
            scan.completed_at = datetime.utcnow()
            scan.resources_scanned = resources_scanned
            scan.findings_created = findings_created
            scan.findings_resolved = findings_resolved
            await db.commit()

        logger.info(
            f"Scan {scan_id} completed: {resources_scanned} resources, "
            f"{findings_created} created, {findings_resolved} resolved"
        )

    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}", exc_info=True)
        try:
            scan = (await db.execute(
                select(CSPMScanModel).where(CSPMScanModel.id == scan_id)
            )).scalar_one_or_none()
            if scan:
                scan.status = "failed"
                scan.completed_at = datetime.utcnow()
                scan.error_message = str(e)[:500]
                await db.commit()
        except Exception:
            pass


async def _update_compliance_results(db: AsyncSession, organization_id: str) -> None:
    """Recompute compliance results for all frameworks based on open findings."""
    try:
        open_findings = (await db.execute(
            select(CSPMFindingModel.rule_id, CSPMFindingModel.id)
            .where(
                CSPMFindingModel.organization_id == organization_id,
                CSPMFindingModel.status == "open",
            )
        )).all()

        failing_rules: set[str] = {row[0] for row in open_findings}

        for framework, rule_ids in COMPLIANCE_RULE_MAP.items():
            for rule_id in rule_ids:
                status = "fail" if rule_id in failing_rules else "pass"
                finding_count = sum(1 for r in open_findings if r[0] == rule_id)

                existing = (await db.execute(
                    select(CSPMComplianceResultModel).where(
                        CSPMComplianceResultModel.organization_id == organization_id,
                        CSPMComplianceResultModel.framework == framework,
                        CSPMComplianceResultModel.control_id == rule_id,
                    )
                )).scalar_one_or_none()

                if existing:
                    existing.status = status
                    existing.finding_count = finding_count
                    existing.last_evaluated_at = datetime.utcnow()
                else:
                    db.add(CSPMComplianceResultModel(
                        id=str(uuid.uuid4()),
                        organization_id=organization_id,
                        framework=framework,
                        control_id=rule_id,
                        status=status,
                        finding_count=finding_count,
                        last_evaluated_at=datetime.utcnow(),
                    ))

        await db.commit()
        logger.info(f"Compliance results updated for org {organization_id}")
    except Exception as e:
        logger.error(f"Failed to update compliance results: {e}", exc_info=True)


async def _save_posture_snapshot(db: AsyncSession, organization_id: str) -> None:
    """Save a daily posture snapshot for trend tracking."""
    try:
        from sqlalchemy import func as sqlfunc

        avg_risk = (await db.execute(
            select(sqlfunc.avg(CSPMResourcePostureModel.risk_score)).where(
                CSPMResourcePostureModel.organization_id == organization_id
            )
        )).scalar() or 0

        posture_score = max(0, 100 - int(avg_risk))

        sev_rows = (await db.execute(
            select(CSPMFindingModel.severity, sqlfunc.count())
            .where(
                CSPMFindingModel.organization_id == organization_id,
                CSPMFindingModel.status == "open",
            )
            .group_by(CSPMFindingModel.severity)
        )).all()
        sev_map = {r[0]: r[1] for r in sev_rows}

        today = datetime.utcnow().date()

        existing = (await db.execute(
            select(CSPMPostureSnapshotModel).where(
                CSPMPostureSnapshotModel.organization_id == organization_id,
                CSPMPostureSnapshotModel.snapshot_date == today,
            )
        )).scalar_one_or_none()

        if existing:
            existing.posture_score = posture_score
            existing.critical_count = sev_map.get("CRITICAL", 0)
            existing.high_count = sev_map.get("HIGH", 0)
            existing.medium_count = sev_map.get("MEDIUM", 0)
            existing.low_count = sev_map.get("LOW", 0)
            existing.updated_at = datetime.utcnow()
        else:
            db.add(CSPMPostureSnapshotModel(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                snapshot_date=today,
                posture_score=posture_score,
                critical_count=sev_map.get("CRITICAL", 0),
                high_count=sev_map.get("HIGH", 0),
                medium_count=sev_map.get("MEDIUM", 0),
                low_count=sev_map.get("LOW", 0),
            ))

        await db.commit()
        logger.info(f"Posture snapshot saved for org {organization_id}: score={posture_score}")
    except Exception as e:
        logger.error(f"Failed to save posture snapshot: {e}", exc_info=True)
