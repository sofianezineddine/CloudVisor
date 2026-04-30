"""API routes for compliance."""

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_db, get_redis
from app.schemas import CompliancePostureResponse, ComplianceSummaryResponse
from app.services import ComplianceService


router = APIRouter(prefix="/policy/compliance", tags=["compliance"])


def get_organization_id(x_org_id: str = Query(...)) -> str:
    return x_org_id


@router.get("", response_model=ComplianceSummaryResponse)
async def get_compliance_summary(
    organization_id: str = Depends(get_organization_id),
    db=Depends(get_db),
    redis=Depends(get_redis),
) -> ComplianceSummaryResponse:
    """Get compliance posture for all frameworks."""
    compliance_service = ComplianceService(db, redis)
    frameworks = await compliance_service.get_all_frameworks(organization_id)

    return ComplianceSummaryResponse(frameworks=frameworks)


@router.get("/{framework}", response_model=CompliancePostureResponse)
async def get_compliance_posture(
    framework: str,
    organization_id: str = Depends(get_organization_id),
    db=Depends(get_db),
    redis=Depends(get_redis),
) -> CompliancePostureResponse:
    """Get compliance posture for a specific framework."""
    compliance_service = ComplianceService(db, redis)
    posture = await compliance_service.get_compliance_posture(organization_id, framework)

    return CompliancePostureResponse(**posture)


@router.get("/{framework}/evidence")
async def get_evidence(
    framework: str,
    control_id: str = Query(...),
    organization_id: str = Depends(get_organization_id),
    db=Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Download evidence for a compliance control."""
    compliance_service = ComplianceService(db, redis)
    evidence = await compliance_service.get_evidence(
        organization_id=organization_id,
        framework=framework,
        control_id=control_id,
    )
    return evidence
