from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_redis
from app.schemas import (
    FindingResponse,
    FindingListResponse,
    FindingUpdateRequest,
    BulkUpdateRequest,
    FindingStatsResponse,
    SuppressionCreateRequest,
    ChannelCreateRequest,
    ChannelResponse,
)
from app.services import FindingService, SuppressionService, NotificationService, ChannelService

router = APIRouter(prefix="/findings", tags=["findings"])


def get_org_id(x_org_id: str = Query(...)) -> str:
    return x_org_id


@router.get("/stats", response_model=FindingStatsResponse)
async def get_stats(
    organization_id: str = Depends(get_org_id),
    db: AsyncSession = Depends(get_db),
) -> FindingStatsResponse:
    finding_service = FindingService(db)
    stats = await finding_service.get_stats(organization_id)
    return FindingStatsResponse(**stats)


@router.get("", response_model=FindingListResponse)
async def list_findings(
    organization_id: str = Depends(get_org_id),
    severity: str | None = None,
    status: str | None = None,
    assignee_id: str | None = None,
    provider: str | None = None,
    account_id: str | None = None,
    region: str | None = None,
    resource_id: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> FindingListResponse:
    finding_service = FindingService(db)
    findings = await finding_service.list_findings(
        organization_id=organization_id,
        severity=severity,
        status=status,
        assignee_id=assignee_id,
        provider=provider,
        account_id=account_id,
        region=region,
        limit=limit,
        offset=offset,
    )
    # Filter by resource_id if provided (for asset findings endpoint)
    if resource_id:
        findings = [f for f in findings if f.get("resource_id") == resource_id]
    return FindingListResponse(findings=findings, total=len(findings))


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: str,
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    finding_service = FindingService(db)
    finding = await finding_service.get_finding(finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return FindingResponse(**finding)


@router.patch("/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: str,
    data: FindingUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    finding_service = FindingService(db)

    if data.status:
        finding = await finding_service.update_finding_status(finding_id, data.status)
        return FindingResponse(**finding)

    raise HTTPException(status_code=400, detail="No update data provided")


@router.post("/bulk", response_model=dict)
async def bulk_update(
    data: BulkUpdateRequest,
    organization_id: str = Depends(get_org_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Spec: Max 500 findings per bulk operation
    if len(data.finding_ids) > 500:
        raise HTTPException(
            status_code=400,
            detail="Bulk operations limited to 500 findings per request"
        )
    
    finding_service = FindingService(db)
    updated = 0

    for finding_id in data.finding_ids:
        try:
            if data.status:
                await finding_service.update_finding_status(finding_id, data.status)
                updated += 1
        except:
            pass

    return {"updated": updated, "total": len(data.finding_ids)}


@router.post("/{finding_id}/suppress")
async def suppress_finding(
    finding_id: str,
    reason: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """Suppress a finding with reason."""
    finding_service = FindingService(db)
    finding = await finding_service.update_finding_status(
        finding_id, "suppressed", reason=reason
    )
    return FindingResponse(**finding)


@router.post("/{finding_id}/accept-risk")
async def accept_risk(
    finding_id: str,
    justification: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """Accept risk for a finding with justification."""
    finding_service = FindingService(db)
    finding = await finding_service.update_finding_status(
        finding_id, "accepted_risk", reason=justification
    )
    return FindingResponse(**finding)


@router.post("/{finding_id}/acknowledge")
async def acknowledge_finding(
    finding_id: str,
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """Acknowledge a finding (for SLA tracking)."""
    finding_service = FindingService(db)
    finding = await finding_service.acknowledge_finding(finding_id, user_id or "system")
    return FindingResponse(**finding)


@router.get("/sla-violations")
async def get_sla_violations(
    organization_id: str = Depends(get_org_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get findings that have violated SLA targets."""
    finding_service = FindingService(db)
    violations = await finding_service.get_sla_violations(organization_id)
    return {"violations": violations, "total": len(violations)}


@router.get("/metrics")
async def get_metrics(
    organization_id: str = Depends(get_org_id),
    redis = Depends(get_redis),
) -> dict:
    """Get pre-aggregated metrics from Redis for dashboard."""
    from app.services.metrics import MetricsService
    metrics_service = MetricsService(redis)
    return await metrics_service.get_dashboard_metrics(organization_id)


@router.post("/submit")
async def submit_finding(
    finding_data: dict,
    organization_id: str = Depends(get_org_id),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
) -> FindingResponse:
    """
    Direct REST submission endpoint for CI/CD CLI tools.
    Accepts finding data and processes it through the same pipeline as Kafka events.
    """
    # Ensure organization_id is set
    finding_data["organization_id"] = organization_id
    
    finding_service = FindingService(db, redis)
    finding = await finding_service.ingest_finding(finding_data)
    
    # Send notifications if not suppressed
    if finding.get("status") == "open":
        from app.services.notifications import NotificationService
        notif_service = NotificationService(db, redis)
        await notif_service.send_notification(finding)
    
    return FindingResponse(**finding)
