"""
CSPM Report Generator — produces CSV (and optionally PDF) reports.
Runs as a background task after a report record is created.
"""
import csv
import io
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models_db import (
    CSPMFindingModel,
    CSPMResourcePostureModel,
    CSPMComplianceResultModel,
    CSPMReportModel,
)

logger = logging.getLogger(__name__)

REPORTS_DIR = os.environ.get("CSPM_REPORTS_DIR", "/tmp/cspm_reports")


async def generate_report(
    db: AsyncSession,
    report_id: str,
    organization_id: str,
    payload: Any,
) -> None:
    """Generate a report and update the report record."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

    try:
        report_type = payload.report_type
        fmt = payload.format or "csv"

        if report_type == "findings_export":
            content, size = await _generate_findings_csv(db, organization_id, payload)
        elif report_type == "compliance":
            content, size = await _generate_compliance_csv(db, organization_id, payload)
        elif report_type == "posture":
            content, size = await _generate_posture_csv(db, organization_id, payload)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

        # Write to disk
        filename = f"{report_id}.{fmt}"
        file_path = os.path.join(REPORTS_DIR, filename)
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            f.write(content)

        # Update report record
        report = (await db.execute(
            select(CSPMReportModel).where(CSPMReportModel.id == report_id)
        )).scalar_one_or_none()

        if report:
            report.status = "ready"
            report.file_path = file_path
            report.file_size_bytes = size
            report.completed_at = datetime.utcnow()
            await db.commit()

        logger.info(f"Report {report_id} generated: {file_path} ({size} bytes)")

    except Exception as e:
        logger.error(f"Report {report_id} generation failed: {e}", exc_info=True)
        try:
            report = (await db.execute(
                select(CSPMReportModel).where(CSPMReportModel.id == report_id)
            )).scalar_one_or_none()
            if report:
                report.status = "failed"
                report.error_message = str(e)[:500]
                report.completed_at = datetime.utcnow()
                await db.commit()
        except Exception:
            pass


async def _generate_findings_csv(
    db: AsyncSession,
    organization_id: str,
    payload: Any,
) -> tuple[str, int]:
    """Export all findings as CSV."""
    q = select(CSPMFindingModel).where(
        CSPMFindingModel.organization_id == organization_id
    )
    if payload.date_from:
        q = q.where(CSPMFindingModel.created_at >= payload.date_from)
    if payload.date_to:
        q = q.where(CSPMFindingModel.created_at <= payload.date_to)
    if payload.account_ids:
        q = q.where(CSPMFindingModel.account_id.in_(payload.account_ids))

    rows = (await db.execute(q.order_by(CSPMFindingModel.severity, CSPMFindingModel.created_at.desc()))).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Rule ID", "Title", "Severity", "Status", "Resource Name",
        "Resource Type", "Provider", "Account ID", "Region",
        "First Seen", "Last Seen", "Resolved At", "Regression Count",
    ])
    for r in rows:
        writer.writerow([
            r.id, r.rule_id, r.title, r.severity, r.status,
            r.resource_name or r.resource_id, r.resource_type or "",
            r.provider or "", r.account_id or "", r.region or "",
            r.first_seen_at.isoformat() if r.first_seen_at else "",
            r.last_seen_at.isoformat() if r.last_seen_at else "",
            r.resolved_at.isoformat() if r.resolved_at else "",
            r.regression_count,
        ])

    content = output.getvalue()
    return content, len(content.encode("utf-8"))


async def _generate_compliance_csv(
    db: AsyncSession,
    organization_id: str,
    payload: Any,
) -> tuple[str, int]:
    """Export compliance results for a framework as CSV."""
    framework = payload.framework or "CIS-AWS"

    q = select(CSPMComplianceResultModel).where(
        CSPMComplianceResultModel.organization_id == organization_id,
        CSPMComplianceResultModel.framework == framework,
    ).order_by(CSPMComplianceResultModel.control_id)

    rows = (await db.execute(q)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Framework", "Control ID", "Status", "Finding Count", "Last Evaluated",
    ])
    for r in rows:
        writer.writerow([
            r.framework, r.control_id, r.status, r.finding_count,
            r.last_evaluated_at.isoformat() if r.last_evaluated_at else "",
        ])

    content = output.getvalue()
    return content, len(content.encode("utf-8"))


async def _generate_posture_csv(
    db: AsyncSession,
    organization_id: str,
    payload: Any,
) -> tuple[str, int]:
    """Export resource posture as CSV."""
    q = select(CSPMResourcePostureModel).where(
        CSPMResourcePostureModel.organization_id == organization_id
    )
    if payload.account_ids:
        q = q.where(CSPMResourcePostureModel.account_id.in_(payload.account_ids))

    rows = (await db.execute(q.order_by(CSPMResourcePostureModel.risk_score.desc()))).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Resource Name", "Resource Type", "Provider", "Account ID", "Region",
        "Environment", "Risk Score", "Critical", "High", "Medium", "Low",
        "Internet Exposed", "Last Scanned",
    ])
    for r in rows:
        writer.writerow([
            r.resource_name or r.resource_id, r.resource_type or "",
            r.provider or "", r.account_id or "", r.region or "",
            r.environment or "", r.risk_score,
            r.critical_count, r.high_count, r.medium_count, r.low_count,
            r.is_internet_exposed,
            r.last_scanned_at.isoformat() if r.last_scanned_at else "",
        ])

    content = output.getvalue()
    return content, len(content.encode("utf-8"))
