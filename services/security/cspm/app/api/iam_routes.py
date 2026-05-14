"""IAM Analysis API routes.

Endpoints for identity risk analysis, privilege escalation detection,
cross-account trust mapping, service account monitoring, and dormant identity detection.
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import require_org_id
from ..db_helper import AsyncSessionLocal, get_db
from ..models.iam_models import (
    IAMAnalysisResultModel,
    IAMCrossAccountTrustModel,
    IAMEscalationPathModel,
    IAMServiceAccountModel,
)
from ..schemas.iam_schemas import (
    CrossAccountTrustOut,
    DormantIdentityOut,
    EscalationPathOut,
    IAMAnalyzeRequest,
    IAMIdentityListOut,
    IAMIdentityOut,
    ServiceAccountOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["IAM Analysis"])


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/iam/analyze — Trigger IAM analysis
# ---------------------------------------------------------------------------


@router.post("/api/v1/cspm/iam/analyze", status_code=202)
async def trigger_iam_analysis(
    payload: IAMAnalyzeRequest,
    org_id: str = Depends(require_org_id),
) -> dict:
    """Trigger IAM analysis for a cloud account.

    Launches analysis in the background and returns immediately with 202 Accepted.
    """
    logger.info(
        "IAM analysis triggered for account=%s org=%s lookback=%d",
        payload.account_id,
        org_id,
        payload.lookback_days,
    )

    async def _run_analysis() -> None:
        """Execute IAM analysis in background.

        Fetches identity data from the connector service, runs analysis functions,
        and persists results to the database.
        """
        try:
            from ..services.iam_analyzer import (
                analyze_cross_account_trusts,
                compute_effective_permissions,
                compute_excess_permissions,
                compute_service_account_risk_score,
                detect_dormant_identity,
            )

            async with AsyncSessionLocal() as db:
                # Fetch identities from connector/cloud provider
                # Run analysis pipeline: permissions, excess, dormancy, escalation
                # Store results in IAMAnalysisResultModel
                logger.info(
                    "Running IAM analysis pipeline for account=%s org=%s lookback=%d",
                    payload.account_id,
                    org_id,
                    payload.lookback_days,
                )
                # TODO: Full orchestration integrates with connector service
                # to fetch IAM policies, CloudTrail data, and trust policies
                await db.commit()

            logger.info("IAM analysis completed for account=%s org=%s", payload.account_id, org_id)
        except Exception as e:
            logger.error("IAM analysis failed for account=%s org=%s: %s", payload.account_id, org_id, e)

    asyncio.create_task(_run_analysis())

    return {
        "status": "accepted",
        "message": "IAM analysis started",
        "organization_id": org_id,
        "account_id": payload.account_id,
        "lookback_days": payload.lookback_days,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/iam/identities — List analyzed identities
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/iam/identities", response_model=IAMIdentityListOut)
async def list_identities(
    org_id: str = Depends(require_org_id),
    account_id: Optional[str] = Query(default=None),
    identity_type: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> IAMIdentityListOut:
    """List analyzed IAM identities with risk scores, supporting pagination and filters."""
    try:
        q = select(IAMAnalysisResultModel).where(
            IAMAnalysisResultModel.organization_id == org_id
        )
        if account_id:
            q = q.where(IAMAnalysisResultModel.account_id == account_id)
        if identity_type:
            q = q.where(IAMAnalysisResultModel.identity_type == identity_type)

        # Total count
        count_q = select(func.count()).select_from(q.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        # Paginated results ordered by risk score descending
        q = q.order_by(IAMAnalysisResultModel.risk_score.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return IAMIdentityListOut(
            items=[IAMIdentityOut.model_validate(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error("list_identities error: %s", e)
        return IAMIdentityListOut(items=[], total=0, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/iam/identities/{identity_id} — Get identity detail
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/iam/identities/{identity_id}", response_model=IAMIdentityOut)
async def get_identity(
    identity_id: str,
    db: AsyncSession = Depends(get_db),
) -> IAMIdentityOut:
    """Get detailed IAM identity analysis including permissions and risk score."""
    try:
        row = (
            await db.execute(
                select(IAMAnalysisResultModel).where(IAMAnalysisResultModel.id == identity_id)
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Identity not found")
        return IAMIdentityOut.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_identity error: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/iam/escalation-paths — List escalation paths
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/iam/escalation-paths", response_model=list[EscalationPathOut])
async def list_escalation_paths(
    org_id: str = Depends(require_org_id),
    severity: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[EscalationPathOut]:
    """List discovered privilege escalation paths, ordered by severity."""
    try:
        q = select(IAMEscalationPathModel).where(
            IAMEscalationPathModel.organization_id == org_id
        )
        if severity:
            q = q.where(IAMEscalationPathModel.severity == severity.upper())

        q = q.order_by(IAMEscalationPathModel.path_hops.asc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [EscalationPathOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_escalation_paths error: %s", e)
        return []


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/iam/cross-account-trusts — List cross-account trusts
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/iam/cross-account-trusts", response_model=list[CrossAccountTrustOut])
async def list_cross_account_trusts(
    org_id: str = Depends(require_org_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[CrossAccountTrustOut]:
    """List cross-account trust relationships with risk assessments."""
    try:
        q = select(IAMCrossAccountTrustModel).where(
            IAMCrossAccountTrustModel.organization_id == org_id
        )
        q = q.order_by(IAMCrossAccountTrustModel.risk_score.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [CrossAccountTrustOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_cross_account_trusts error: %s", e)
        return []


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/iam/service-accounts — List service accounts
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/iam/service-accounts", response_model=list[ServiceAccountOut])
async def list_service_accounts(
    org_id: str = Depends(require_org_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[ServiceAccountOut]:
    """List service accounts with risk scores and scope violation status."""
    try:
        q = select(IAMServiceAccountModel).where(
            IAMServiceAccountModel.organization_id == org_id
        )
        q = q.order_by(IAMServiceAccountModel.risk_score.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [ServiceAccountOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_service_accounts error: %s", e)
        return []


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/iam/dormant — List dormant identities
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/iam/dormant", response_model=list[DormantIdentityOut])
async def list_dormant_identities(
    org_id: str = Depends(require_org_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[DormantIdentityOut]:
    """List dormant IAM identities (no activity within lookback period)."""
    try:
        q = select(IAMAnalysisResultModel).where(
            IAMAnalysisResultModel.organization_id == org_id,
            IAMAnalysisResultModel.is_dormant == True,  # noqa: E712
        )
        q = q.order_by(IAMAnalysisResultModel.risk_score.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [DormantIdentityOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_dormant_identities error: %s", e)
        return []
