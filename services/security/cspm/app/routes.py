"""CSPM REST API routes — full implementation."""
import logging
import uuid
from datetime import datetime
from typing import Any, Optional, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .core.auth import require_org_id
from .db_helper import get_db
from .models_db import (
    CSPMComplianceResultModel,
    CSPMFindingModel,
    CSPMResourcePostureModel,
    CSPMScanModel,
)
from .services.risk_scorer import compute_risk_score, get_score_color

logger = logging.getLogger(__name__)

_VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
_VALID_STATUSES = {"open", "resolved", "suppressed", "accepted_risk"}

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------



class FindingOut(BaseModel):
    id: str
    organization_id: str
    fingerprint: str
    rule_id: str
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    resource_id: str
    resource_name: Optional[str] = None
    resource_type: Optional[str] = None
    provider: Optional[str] = None
    account_id: Optional[str] = None
    region: Optional[str] = None
    remediation: Optional[str] = None
    compliance_mapping: list[dict] = []
    regression_count: int = 0
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FindingListOut(BaseModel):
    items: list[FindingOut]
    total: int
    page: int
    page_size: int


class FindingStatusUpdate(BaseModel):
    status: str  # resolved, suppressed, accepted_risk, open

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(_VALID_STATUSES)}")
        return v


class ResourcePostureOut(BaseModel):
    id: str
    organization_id: str
    resource_id: str
    resource_name: Optional[str] = None
    resource_type: Optional[str] = None
    provider: Optional[str] = None
    account_id: Optional[str] = None
    region: Optional[str] = None
    environment: Optional[str] = None
    risk_score: int = 0
    risk_color: str = "green"
    is_internet_exposed: bool = False
    contains_sensitive_data: bool = False
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    last_scanned_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScanOut(BaseModel):
    id: str
    organization_id: str
    account_id: Optional[str] = None
    scan_type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    resources_scanned: int = 0
    findings_created: int = 0
    findings_resolved: int = 0
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ScanRequest(BaseModel):
    organization_id: Optional[str] = None  # sent by API gateway; also resolved from org_id param
    account_id: Optional[str] = None
    scan_type: str = "on_demand"


# ---------------------------------------------------------------------------
# Helper: extract org_id from validated JWT (never from query params)
# ---------------------------------------------------------------------------

def _org_id_from_query(org_id: Optional[str] = Query(default=None, alias="org_id")) -> str:
    # NOTE: This helper is kept only for the compliance proxy endpoints that
    # forward to the Policy service. All other endpoints use require_org_id.
    return org_id or "default"


# ---------------------------------------------------------------------------
# Findings endpoints
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/findings", response_model=FindingListOut)
async def list_findings(
    org_id: str = Depends(require_org_id),
    severity: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    rule_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> FindingListOut:
    # Validate enum inputs
    if severity and severity.upper() not in _VALID_SEVERITIES:
        raise HTTPException(status_code=422, detail=f"severity must be one of {sorted(_VALID_SEVERITIES)}")
    if status and status.lower() not in _VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(_VALID_STATUSES)}")
    try:
        q = select(CSPMFindingModel).where(CSPMFindingModel.organization_id == org_id)
        if severity:
            q = q.where(CSPMFindingModel.severity == severity.upper())
        if status:
            q = q.where(CSPMFindingModel.status == status.lower())
        if provider:
            q = q.where(CSPMFindingModel.provider == provider.lower())
        if account_id:
            q = q.where(CSPMFindingModel.account_id == account_id)
        if region:
            q = q.where(CSPMFindingModel.region == region)
        if rule_id:
            q = q.where(CSPMFindingModel.rule_id == rule_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return FindingListOut(
            items=[FindingOut.model_validate(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error(f"list_findings error: {e}")
        return FindingListOut(items=[], total=0, page=page, page_size=page_size)


@router.get("/api/v1/cspm/findings/{finding_id}", response_model=FindingOut)
async def get_finding(
    finding_id: str,
    db: AsyncSession = Depends(get_db),
) -> FindingOut:
    try:
        row = (
            await db.execute(
                select(CSPMFindingModel).where(CSPMFindingModel.id == finding_id)
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Finding not found")
        return FindingOut.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_finding error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.patch("/api/v1/cspm/findings/{finding_id}/status", response_model=FindingOut)
async def update_finding_status(
    finding_id: str,
    payload: FindingStatusUpdate,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> FindingOut:
    try:
        row = (
            await db.execute(
                select(CSPMFindingModel).where(
                    CSPMFindingModel.id == finding_id,
                    CSPMFindingModel.organization_id == org_id,  # enforce ownership
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Finding not found")

        row.status = payload.status
        row.updated_at = datetime.utcnow()
        if payload.status == "resolved":
            row.resolved_at = datetime.utcnow()
        await db.commit()
        await db.refresh(row)
        return FindingOut.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"update_finding_status error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.get("/api/v1/cspm/findings/{finding_id}/remediation")
async def get_finding_remediation(
    finding_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get structured remediation suggestion for a finding."""
    try:
        row = (await db.execute(
            select(CSPMFindingModel).where(CSPMFindingModel.id == finding_id)
        )).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Finding not found")

        from .services.remediation import get_remediation_suggestion
        suggestion = await get_remediation_suggestion(
            rule_id=row.rule_id,
            resource_name=row.resource_name or row.resource_id,
            resource_type=row.resource_type or "",
            provider=row.provider or "",
            remediation_text=row.remediation,
        )
        return suggestion
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_finding_remediation error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


# ---------------------------------------------------------------------------
# Posture endpoints
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/posture")
async def get_posture(
    org_id: str = Depends(require_org_id),
    account_id: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Org-level posture summary — filtered by account_id or provider if provided."""
    try:
        # Base filter
        finding_filters = [
            CSPMFindingModel.organization_id == org_id,
            CSPMFindingModel.status == "open",
        ]
        resource_filters = [CSPMResourcePostureModel.organization_id == org_id]
        compliance_filters = [CSPMComplianceResultModel.organization_id == org_id]

        # Apply scope filters
        if account_id:
            finding_filters.append(CSPMFindingModel.account_id == account_id)
            resource_filters.append(CSPMResourcePostureModel.account_id == account_id)
        elif provider:
            finding_filters.append(CSPMFindingModel.provider == provider.lower())
            resource_filters.append(CSPMResourcePostureModel.provider == provider.lower())

        # Severity counts from open findings
        sev_rows = (
            await db.execute(
                select(CSPMFindingModel.severity, func.count())
                .where(*finding_filters)
                .group_by(CSPMFindingModel.severity)
            )
        ).all()
        sev_map = {r[0]: r[1] for r in sev_rows}

        total_open = sum(sev_map.values())
        critical = sev_map.get("CRITICAL", 0)
        high = sev_map.get("HIGH", 0)
        medium = sev_map.get("MEDIUM", 0)
        low = sev_map.get("LOW", 0)

        # Resources evaluated
        resources_count = (
            await db.execute(
                select(func.count()).select_from(
                    select(CSPMResourcePostureModel).where(*resource_filters).subquery()
                )
            )
        ).scalar() or 0

        # Average risk score
        avg_score_row = (
            await db.execute(
                select(func.avg(CSPMResourcePostureModel.risk_score)).where(*resource_filters)
            )
        ).scalar()
        posture_score = max(0, 100 - int(avg_score_row or 0))

        # Compliance %
        comp_rows = (
            await db.execute(
                select(CSPMComplianceResultModel.status, func.count())
                .where(*compliance_filters)
                .group_by(CSPMComplianceResultModel.status)
            )
        ).all()
        comp_map = {r[0]: r[1] for r in comp_rows}
        total_controls = sum(comp_map.values())
        passing_controls = comp_map.get("pass", 0)

        if total_controls > 0:
            compliance_pct = round(passing_controls / total_controls * 100, 1)
        else:
            open_count = sum(sev_map.values())
            if open_count == 0:
                compliance_pct = 100.0
            else:
                penalty = (
                    sev_map.get("CRITICAL", 0) * 5
                    + sev_map.get("HIGH", 0) * 2
                    + sev_map.get("MEDIUM", 0) * 0.5
                )
                compliance_pct = max(0.0, round(100.0 - penalty, 1))

        return {
            "organization_id": org_id,
            "posture_score": posture_score,
            "total_open_findings": total_open,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "resources_evaluated": resources_count,
            "compliance_percentage": compliance_pct,
        }
    except Exception as e:
        logger.error(f"get_posture error: {e}")
        return {
            "organization_id": org_id,
            "posture_score": 0,
            "total_open_findings": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "resources_evaluated": 0,
            "compliance_percentage": 0.0,
        }


@router.get("/api/v1/cspm/posture/accounts")
async def get_account_posture(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Per-account posture cards."""
    try:
        rows = (
            await db.execute(
                select(
                    CSPMResourcePostureModel.account_id,
                    CSPMResourcePostureModel.provider,
                    func.count().label("resource_count"),
                    func.avg(CSPMResourcePostureModel.risk_score).label("avg_risk"),
                    func.sum(CSPMResourcePostureModel.critical_count).label("critical"),
                    func.sum(CSPMResourcePostureModel.high_count).label("high"),
                    func.sum(CSPMResourcePostureModel.medium_count).label("medium"),
                    func.sum(CSPMResourcePostureModel.low_count).label("low"),
                )
                .where(CSPMResourcePostureModel.organization_id == org_id)
                .group_by(
                    CSPMResourcePostureModel.account_id,
                    CSPMResourcePostureModel.provider,
                )
            )
        ).all()

        return [
            {
                "account_id": r.account_id,
                "provider": r.provider,
                "resource_count": r.resource_count,
                "avg_risk_score": round(r.avg_risk or 0, 1),
                "posture_score": max(0, 100 - int(r.avg_risk or 0)),
                "critical": int(r.critical or 0),
                "high": int(r.high or 0),
                "medium": int(r.medium or 0),
                "low": int(r.low or 0),
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"get_account_posture error: {e}")
        return []


# ---------------------------------------------------------------------------
# Resources endpoint
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/resources", response_model=list[ResourcePostureOut])
async def list_resources(
    org_id: str = Depends(require_org_id),
    provider: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[ResourcePostureOut]:
    try:
        q = select(CSPMResourcePostureModel).where(
            CSPMResourcePostureModel.organization_id == org_id
        )
        if provider:
            q = q.where(CSPMResourcePostureModel.provider == provider.lower())
        if account_id:
            q = q.where(CSPMResourcePostureModel.account_id == account_id)
        if region:
            q = q.where(CSPMResourcePostureModel.region == region)
        if resource_type:
            q = q.where(CSPMResourcePostureModel.resource_type == resource_type)

        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        result = []
        for r in rows:
            out = ResourcePostureOut.model_validate(r)
            out.risk_color = get_score_color(r.risk_score)
            result.append(out)
        return result
    except Exception as e:
        logger.error(f"list_resources error: {e}")
        return []


# ---------------------------------------------------------------------------
# Compliance endpoints (proxy to Policy service)
# ---------------------------------------------------------------------------

import os

POLICY_SERVICE_URL = os.environ.get("POLICY_SERVICE_URL", "http://localhost:8003")


@router.get("/api/v1/cspm/compliance")
async def get_compliance(
    org_id: str = Depends(require_org_id),
) -> Any:
    """Get compliance posture for all frameworks — proxied from Policy service."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{POLICY_SERVICE_URL}/policy/compliance",
                params={"x_org_id": org_id},
            )
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"Policy compliance returned {resp.status_code}")
            return {"frameworks": [], "error": "Policy service unavailable"}
    except Exception as e:
        logger.error(f"get_compliance proxy error: {e}")
        return {"frameworks": [], "error": str(e)}


@router.get("/api/v1/cspm/compliance/{framework}")
async def get_compliance_framework(
    framework: str,
    org_id: str = Depends(require_org_id),
) -> Any:
    """Get compliance posture for a specific framework — proxied from Policy service."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{POLICY_SERVICE_URL}/policy/compliance/{framework}",
                params={"x_org_id": org_id},
            )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Framework '{framework}' not found")
            return {"framework": framework, "error": "Policy service unavailable"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_compliance_framework proxy error: {e}")
        return {"framework": framework, "error": str(e)}


# ---------------------------------------------------------------------------
# Scans endpoints
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/scans", response_model=list[ScanOut])
async def list_scans(
    org_id: str = Depends(require_org_id),
    account_id: Optional[str] = Query(default=None),
    account_ids: Optional[str] = Query(default=None),  # comma-separated list
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ScanOut]:
    try:
        q = (
            select(CSPMScanModel)
            .where(CSPMScanModel.organization_id == org_id)
        )
        if account_id:
            q = q.where(CSPMScanModel.account_id == account_id)
        elif account_ids:
            ids = [i.strip() for i in account_ids.split(",") if i.strip()]
            if ids:
                q = q.where(CSPMScanModel.account_id.in_(ids))
        q = q.order_by(CSPMScanModel.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()
        return [ScanOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error(f"list_scans error: {e}")
        return []


@router.post("/api/v1/cspm/scans", response_model=ScanOut, status_code=201)
async def trigger_scan(
    payload: ScanRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> ScanOut:
    import asyncio
    # org_id from query param (set by API gateway) takes precedence;
    # fall back to body field for backward compatibility
    effective_org_id = org_id if org_id != "default" else (payload.organization_id or org_id)
    try:
        scan = CSPMScanModel(
            id=str(uuid.uuid4()),
            organization_id=effective_org_id,
            account_id=payload.account_id,
            scan_type=payload.scan_type,
            status="running",
            started_at=datetime.utcnow(),
        )
        db.add(scan)
        await db.commit()
        await db.refresh(scan)

        # Run scan in background
        from .services.scan_executor import run_scan
        from .db_helper import AsyncSessionLocal
        scan_id = scan.id

        async def _run():
            async with AsyncSessionLocal() as scan_db:
                await run_scan(scan_db, scan_id, effective_org_id, payload.account_id)

        asyncio.create_task(_run())

        return ScanOut.model_validate(scan)
    except Exception as e:
        logger.error(f"trigger_scan error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create scan")


@router.get("/api/v1/cspm/scans/{scan_id}", response_model=ScanOut)
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
) -> ScanOut:
    try:
        row = (
            await db.execute(
                select(CSPMScanModel).where(CSPMScanModel.id == scan_id)
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Scan not found")
        return ScanOut.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_scan error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


# ---------------------------------------------------------------------------
# Drift findings endpoint
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/drift")
async def get_drift_findings(
    org_id: str = Depends(require_org_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return findings that have regressed (regression_count > 0)."""
    try:
        q = select(CSPMFindingModel).where(
            CSPMFindingModel.organization_id == org_id,
            CSPMFindingModel.regression_count > 0,
            CSPMFindingModel.status == "open",
        ).order_by(CSPMFindingModel.regression_count.desc())

        count_q = select(func.count()).select_from(q.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return {
            "items": [FindingOut.model_validate(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"get_drift_findings error: {e}")
        return {"items": [], "total": 0, "page": page, "page_size": page_size}


@router.get("/api/v1/cspm/scans/{scan_id}/resources")
async def get_scan_resources(
    scan_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return resources evaluated in a specific scan."""
    try:
        scan = (await db.execute(
            select(CSPMScanModel).where(
                CSPMScanModel.id == scan_id,
                CSPMScanModel.organization_id == org_id,  # enforce ownership
            )
        )).scalar_one_or_none()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")

        # Return posture records last scanned around the scan time
        q = select(CSPMResourcePostureModel).where(
            CSPMResourcePostureModel.organization_id == org_id,
        )
        if scan.account_id:
            q = q.where(CSPMResourcePostureModel.account_id == scan.account_id)
        if scan.completed_at:
            from datetime import timedelta
            window_start = scan.started_at - timedelta(minutes=1)
            window_end = scan.completed_at + timedelta(minutes=1)
            q = q.where(
                CSPMResourcePostureModel.last_scanned_at >= window_start,
                CSPMResourcePostureModel.last_scanned_at <= window_end,
            )

        rows = (await db.execute(q.limit(500))).scalars().all()
        return {
            "scan_id": scan_id,
            "resources": [ResourcePostureOut.model_validate(r) for r in rows],
            "total": len(rows),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_scan_resources error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


# ---------------------------------------------------------------------------
# Reports endpoints
# ---------------------------------------------------------------------------

class ReportRequest(BaseModel):
    report_type: str = "findings_export"  # compliance, posture, findings_export
    framework: Optional[str] = None
    format: str = "csv"  # csv, pdf
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    account_ids: list[str] = []


class ReportOut(BaseModel):
    id: str
    organization_id: str
    report_type: str
    framework: Optional[str] = None
    format: str
    status: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    account_ids: list[str] = []
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/api/v1/cspm/reports", response_model=list[ReportOut])
async def list_reports(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> list[ReportOut]:
    try:
        from .models_db import CSPMReportModel
        rows = (await db.execute(
            select(CSPMReportModel)
            .where(CSPMReportModel.organization_id == org_id)
            .order_by(CSPMReportModel.created_at.desc())
            .limit(50)
        )).scalars().all()
        return [ReportOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error(f"list_reports error: {e}")
        return []


@router.post("/api/v1/cspm/reports", response_model=ReportOut, status_code=201)
async def create_report(
    payload: ReportRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> ReportOut:
    import asyncio
    try:
        from .models_db import CSPMReportModel
        report = CSPMReportModel(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            report_type=payload.report_type,
            framework=payload.framework,
            format=payload.format,
            status="generating",
            date_from=payload.date_from,
            date_to=payload.date_to,
            account_ids=payload.account_ids,
            created_at=datetime.utcnow(),
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        report_id = report.id

        async def _generate():
            from .db_helper import AsyncSessionLocal
            from .services.report_generator import generate_report
            async with AsyncSessionLocal() as rdb:
                await generate_report(rdb, report_id, org_id, payload)

        asyncio.create_task(_generate())
        return ReportOut.model_validate(report)
    except Exception as e:
        logger.error(f"create_report error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create report")


@router.get("/api/v1/cspm/reports/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReportOut:
    try:
        from .models_db import CSPMReportModel
        row = (await db.execute(
            select(CSPMReportModel).where(CSPMReportModel.id == report_id)
        )).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")
        return ReportOut.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_report error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.get("/api/v1/cspm/reports/{report_id}/download")
async def download_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download a generated report file."""
    import os
    from fastapi.responses import FileResponse
    try:
        from .models_db import CSPMReportModel
        row = (await db.execute(
            select(CSPMReportModel).where(CSPMReportModel.id == report_id)
        )).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")
        if row.status != "ready":
            raise HTTPException(status_code=409, detail=f"Report is {row.status}")
        if not row.file_path or not os.path.exists(row.file_path):
            raise HTTPException(status_code=404, detail="Report file not found")

        media_type = "application/pdf" if row.format == "pdf" else "text/csv"
        filename = f"cloudvisor-{row.report_type}-{report_id[:8]}.{row.format}"
        return FileResponse(row.file_path, media_type=media_type, filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"download_report error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@router.get("/api/v1/cspm/stats")
async def get_stats(
    org_id: str = Depends(require_org_id),
    account_id: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Dashboard summary stats — filtered by account_id or provider if provided."""
    try:
        # Build scope filters
        finding_filters = [CSPMFindingModel.organization_id == org_id]
        resource_filters = [CSPMResourcePostureModel.organization_id == org_id]

        if account_id:
            finding_filters.append(CSPMFindingModel.account_id == account_id)
            resource_filters.append(CSPMResourcePostureModel.account_id == account_id)
        elif provider:
            finding_filters.append(CSPMFindingModel.provider == provider.lower())
            resource_filters.append(CSPMResourcePostureModel.provider == provider.lower())

        # Open findings by severity
        sev_rows = (
            await db.execute(
                select(CSPMFindingModel.severity, func.count())
                .where(*finding_filters, CSPMFindingModel.status == "open")
                .group_by(CSPMFindingModel.severity)
            )
        ).all()
        sev_map = {r[0]: r[1] for r in sev_rows}

        # Total findings (all statuses)
        total_findings = (
            await db.execute(
                select(func.count()).select_from(
                    select(CSPMFindingModel).where(*finding_filters).subquery()
                )
            )
        ).scalar() or 0

        # Resources
        total_resources = (
            await db.execute(
                select(func.count()).select_from(
                    select(CSPMResourcePostureModel).where(*resource_filters).subquery()
                )
            )
        ).scalar() or 0

        # Last scan — filter by account if specified
        scan_filters = [CSPMScanModel.organization_id == org_id]
        if account_id:
            scan_filters.append(CSPMScanModel.account_id == account_id)
        last_scan = (
            await db.execute(
                select(CSPMScanModel)
                .where(*scan_filters)
                .order_by(CSPMScanModel.started_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        # Avg risk score
        avg_risk = (
            await db.execute(
                select(func.avg(CSPMResourcePostureModel.risk_score)).where(*resource_filters)
            )
        ).scalar()

        return {
            "organization_id": org_id,
            "total_findings": total_findings,
            "open_findings": sum(sev_map.values()),
            "critical": sev_map.get("CRITICAL", 0),
            "high": sev_map.get("HIGH", 0),
            "medium": sev_map.get("MEDIUM", 0),
            "low": sev_map.get("LOW", 0),
            "total_resources": total_resources,
            "avg_risk_score": round(float(avg_risk or 0), 1),
            "posture_score": max(0, 100 - int(avg_risk or 0)),
            "last_scan_at": last_scan.started_at.isoformat() if last_scan else None,
            "last_scan_status": last_scan.status if last_scan else None,
        }
    except Exception as e:
        logger.error(f"get_stats error: {e}")
        return {
            "organization_id": org_id,
            "total_findings": 0,
            "open_findings": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "total_resources": 0,
            "avg_risk_score": 0.0,
            "posture_score": 0,
            "last_scan_at": None,
            "last_scan_status": None,
        }


# ---------------------------------------------------------------------------
# Posture trend endpoint
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/posture/trend")
async def get_posture_trend(
    org_id: str = Depends(require_org_id),
    days: int = Query(default=30, ge=7, le=90),
    account_id: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return daily posture score snapshots for trend chart.

    When account_id or provider is provided, the snapshot table (which has no
    per-account columns) cannot be used directly.  Instead we compute a daily
    trend on-the-fly from the findings table so the chart reflects the correct
    scope.  When no scope filter is active we fall back to the pre-aggregated
    snapshot rows for efficiency.
    """
    from .models_db import CSPMPostureSnapshotModel
    from datetime import timedelta, date as date_type
    from sqlalchemy import cast, Date as SADate

    try:
        cutoff = datetime.utcnow().date() - timedelta(days=days)

        # ── Scoped path: compute trend from findings ──────────────────────────
        if account_id or provider:
            finding_filters = [
                CSPMFindingModel.organization_id == org_id,
                CSPMFindingModel.first_seen_at >= datetime.combine(cutoff, datetime.min.time()),
            ]
            if account_id:
                finding_filters.append(CSPMFindingModel.account_id == account_id)
            elif provider:
                finding_filters.append(CSPMFindingModel.provider == provider.lower())

            # Group open findings by day and severity
            day_col = cast(CSPMFindingModel.first_seen_at, SADate).label("day")
            rows = (await db.execute(
                select(
                    day_col,
                    CSPMFindingModel.severity,
                    func.count().label("cnt"),
                )
                .where(*finding_filters)
                .group_by(day_col, CSPMFindingModel.severity)
                .order_by(day_col.asc())
            )).all()

            # Aggregate per day
            day_map: dict[str, dict] = {}
            for r in rows:
                key = r.day.isoformat() if hasattr(r.day, "isoformat") else str(r.day)
                if key not in day_map:
                    day_map[key] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
                sev = (r.severity or "").upper()
                if sev in day_map[key]:
                    day_map[key][sev.lower()] += r.cnt

            result = []
            for day_str in sorted(day_map.keys()):
                d = day_map[day_str]
                total = d["critical"] + d["high"] + d["medium"] + d["low"]
                penalty = d["critical"] * 5 + d["high"] * 2 + d["medium"] * 0.5
                score = max(0, round(100.0 - penalty, 1))
                result.append({
                    "date": day_str,
                    "posture_score": score,
                    "critical": d["critical"],
                    "high": d["high"],
                    "medium": d["medium"],
                    "low": d["low"],
                })
            return result

        # ── Unscoped path: use pre-aggregated snapshots ───────────────────────
        rows = (await db.execute(
            select(CSPMPostureSnapshotModel)
            .where(
                CSPMPostureSnapshotModel.organization_id == org_id,
                CSPMPostureSnapshotModel.snapshot_date >= cutoff,
            )
            .order_by(CSPMPostureSnapshotModel.snapshot_date.asc())
        )).scalars().all()

        return [
            {
                "date": r.snapshot_date.isoformat(),
                "posture_score": r.posture_score,
                "critical": r.critical_count,
                "high": r.high_count,
                "medium": r.medium_count,
                "low": r.low_count,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"get_posture_trend error: {e}")
        return []
