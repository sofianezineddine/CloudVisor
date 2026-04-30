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
