from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
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


def _extract_user_id(request: Request) -> str | None:
    """Extract user ID from JWT Bearer token for audit logging."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import base64, json
            token = auth[7:]
            parts = token.split(".")
            if len(parts) == 3:
                payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                return payload.get("sub")
        except Exception:
            pass
    return request.headers.get("X-User-ID")


# ─── Static paths MUST come before parameterized paths ───────────────────────

@router.get("/stats", response_model=FindingStatsResponse)
async def get_stats(
    organization_id: str = Depends(get_org_id),
    db: AsyncSession = Depends(get_db),
) -> FindingStatsResponse:
    finding_service = FindingService(db)
    stats = await finding_service.get_stats(organization_id)
    return FindingStatsResponse(**stats)


@router.post("/bulk", response_model=dict)
async def bulk_update(
    data: BulkUpdateRequest,
    request: Request,
    organization_id: str = Depends(get_org_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bulk update up to 500 findings. Spec: max 500 per request."""
    if len(data.finding_ids) > 500:
        raise HTTPException(
            status_code=400,
            detail="Bulk operations limited to 500 findings per request"
        )

    user_id = _extract_user_id(request)
    finding_service = FindingService(db)
    updated = 0

    for finding_id in data.finding_ids:
        try:
            if data.status:
                await finding_service.update_finding_status(
                    finding_id, data.status, changed_by=user_id, reason=data.reason
                )
                updated += 1
            elif data.assignee_id:
                await finding_service.assign_finding(finding_id, data.assignee_id)
                updated += 1
        except Exception:
            pass

    return {"updated": updated, "total": len(data.finding_ids)}


class BulkSuppressRequest(BaseModel):
    """Filter criteria for bulk suppression."""
    severity: str | None = None
    account_id: str | None = None
    region: str | None = None
    module: str | None = None
    resource_id: str | None = None
    reason: str = "Bulk suppression"


@router.post("/bulk-suppress", response_model=dict)
async def bulk_suppress(
    data: BulkSuppressRequest,
    request: Request,
    organization_id: str = Depends(get_org_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Suppress all findings matching the given filter criteria."""
    from sqlalchemy import select
    from app.models.alert import FindingModel

    user_id = _extract_user_id(request)

    query = select(FindingModel).where(
        FindingModel.organization_id == organization_id,
        FindingModel.status.in_(["open", "in_progress"]),
    )
    if data.severity:
        query = query.where(FindingModel.severity == data.severity)
    if data.account_id:
        query = query.where(FindingModel.account_id == data.account_id)
    if data.region:
        query = query.where(FindingModel.region == data.region)
    if data.module:
        query = query.where(FindingModel.rule_id.like(f"{data.module}.%"))
    if data.resource_id:
        query = query.where(FindingModel.resource_id == data.resource_id)

    result = await db.execute(query)
    findings = result.scalars().all()

    finding_service = FindingService(db)
    suppressed = 0
    for finding in findings:
        try:
            await finding_service.update_finding_status(
                finding.id, "suppressed", changed_by=user_id, reason=data.reason
            )
            suppressed += 1
        except Exception:
            pass

    return {"suppressed": suppressed, "total": len(findings)}


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
    redis=Depends(get_redis),
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
    redis=Depends(get_redis),
) -> FindingResponse:
    """
    Direct REST submission endpoint for CI/CD CLI tools.
    Accepts finding data and processes it through the same pipeline as Kafka events.
    """
    finding_data["organization_id"] = organization_id

    finding_service = FindingService(db, redis)
    finding = await finding_service.ingest_finding(finding_data)

    if finding.get("status") == "open":
        from app.services.notifications import NotificationService
        notif_service = NotificationService(db, redis)
        await notif_service.send_notification(finding)

    return FindingResponse(**finding)


# ─── List and detail (parameterized paths AFTER static paths) ─────────────────

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
    module: str | None = None,
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
        module=module,
        limit=limit,
        offset=offset,
    )
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
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """Update finding status, assignee, or notes. All fields are optional."""
    user_id = _extract_user_id(request)
    finding_service = FindingService(db)

    if data.status:
        finding = await finding_service.update_finding_status(
            finding_id, data.status, changed_by=user_id, reason=data.reason
        )
        return FindingResponse(**finding)

    if data.assignee_id:
        finding = await finding_service.assign_finding(finding_id, data.assignee_id)
        return FindingResponse(**finding)

    # If only note is provided, record it as a history entry without status change
    if data.reason:
        from sqlalchemy import select
        from app.models.alert import FindingModel
        result = await db.execute(select(FindingModel).where(FindingModel.id == finding_id))
        f = result.scalar_one_or_none()
        if not f:
            raise HTTPException(status_code=404, detail="Finding not found")
        await finding_service._record_history(finding_id, f.status, f.status, user_id, data.reason)
        await db.commit()
        finding = await finding_service.get_finding(finding_id)
        return FindingResponse(**finding)

    raise HTTPException(status_code=400, detail="No update data provided")


@router.post("/{finding_id}/suppress")
async def suppress_finding(
    finding_id: str,
    request: Request,
    reason: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """Suppress a finding with reason. Records the user who suppressed it."""
    user_id = _extract_user_id(request)
    finding_service = FindingService(db)
    finding = await finding_service.update_finding_status(
        finding_id, "suppressed", changed_by=user_id, reason=reason
    )
    return FindingResponse(**finding)


@router.post("/{finding_id}/accept-risk")
async def accept_risk(
    finding_id: str,
    request: Request,
    justification: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """Accept risk for a finding with justification. Records the user who accepted it."""
    user_id = _extract_user_id(request)
    finding_service = FindingService(db)
    finding = await finding_service.update_finding_status(
        finding_id, "accepted_risk", changed_by=user_id, reason=justification
    )
    return FindingResponse(**finding)


@router.post("/{finding_id}/acknowledge")
async def acknowledge_finding(
    finding_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """Acknowledge a finding (for SLA tracking). Records the acknowledging user."""
    user_id = _extract_user_id(request) or "system"
    finding_service = FindingService(db)
    finding = await finding_service.acknowledge_finding(finding_id, user_id)
    return FindingResponse(**finding)
