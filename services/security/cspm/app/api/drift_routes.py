"""Drift Detection API routes.

Endpoints for drift events, baselines, anomaly findings, config change history,
correlated alerts, and correlation rule management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import require_org_id
from ..db_helper import get_db
from ..models.drift_models import (
    AnomalyFindingModel,
    ConfigChangeHistoryModel,
    CorrelatedAlertModel,
    CorrelationRuleModel,
    DriftBaselineModel,
    DriftEventModel,
)
from ..schemas.drift_schemas import (
    AnomalyOut,
    ConfigChangeHistoryOut,
    CorrelatedAlertOut,
    CorrelationRuleOut,
    CorrelationRuleRequest,
    DriftBaselineOut,
    DriftBaselineRequest,
    DriftEventOut,
)
from ..services.drift_detector import set_baseline

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Drift Detection"])


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/drift/events — List drift events
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/drift/events", response_model=list[DriftEventOut])
async def list_drift_events(
    org_id: str = Depends(require_org_id),
    resource_id: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    security_relevant: Optional[bool] = Query(default=None, alias="security_relevant"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[DriftEventOut]:
    """List drift events with optional filters for resource, severity, and security relevance."""
    try:
        q = select(DriftEventModel).where(
            DriftEventModel.organization_id == org_id
        )
        if resource_id:
            q = q.where(DriftEventModel.resource_id == resource_id)
        if severity:
            q = q.where(DriftEventModel.severity == severity.upper())
        if security_relevant is not None:
            q = q.where(DriftEventModel.is_security_relevant == security_relevant)

        q = q.order_by(DriftEventModel.detected_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [DriftEventOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_drift_events error: %s", e)
        return []


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/drift/events/{event_id} — Get drift event detail
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/drift/events/{event_id}", response_model=DriftEventOut)
async def get_drift_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> DriftEventOut:
    """Get detailed information about a specific drift event."""
    try:
        row = (
            await db.execute(
                select(DriftEventModel).where(DriftEventModel.id == event_id)
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Drift event not found")
        return DriftEventOut.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_drift_event error: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/drift/baselines — Set baseline for a resource
# ---------------------------------------------------------------------------


@router.post("/api/v1/cspm/drift/baselines", response_model=DriftBaselineOut, status_code=201)
async def create_baseline(
    payload: DriftBaselineRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> DriftBaselineOut:
    """Set or replace the configuration baseline for a resource."""
    try:
        baseline = await set_baseline(
            db,
            organization_id=org_id,
            resource_id=payload.resource_id,
            resource_type=payload.resource_type or "unknown",
            baseline_config=payload.baseline_config,
            set_by="api",
        )
        await db.commit()
        await db.refresh(baseline)
        return DriftBaselineOut.model_validate(baseline)
    except Exception as e:
        logger.error("create_baseline error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to set baseline")


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/drift/baselines/{resource_id} — Get current baseline
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/cspm/drift/baselines/{resource_id}", response_model=DriftBaselineOut
)
async def get_baseline(
    resource_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> DriftBaselineOut:
    """Get the current configuration baseline for a resource."""
    try:
        row = (
            await db.execute(
                select(DriftBaselineModel).where(
                    DriftBaselineModel.organization_id == org_id,
                    DriftBaselineModel.resource_id == resource_id,
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Baseline not found")
        return DriftBaselineOut.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_baseline error: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/drift/anomalies — List anomaly findings
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/drift/anomalies", response_model=list[AnomalyOut])
async def list_anomalies(
    org_id: str = Depends(require_org_id),
    resource_id: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[AnomalyOut]:
    """List behavioral anomaly findings with optional filters."""
    try:
        q = select(AnomalyFindingModel).where(
            AnomalyFindingModel.organization_id == org_id
        )
        if resource_id:
            q = q.where(AnomalyFindingModel.resource_id == resource_id)
        if severity:
            q = q.where(AnomalyFindingModel.severity == severity.upper())

        q = q.order_by(AnomalyFindingModel.detected_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [AnomalyOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_anomalies error: %s", e)
        return []


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/drift/history/{resource_id} — Get config change history
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/cspm/drift/history/{resource_id}",
    response_model=list[ConfigChangeHistoryOut],
)
async def get_config_history(
    resource_id: str,
    org_id: str = Depends(require_org_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[ConfigChangeHistoryOut]:
    """Get configuration change history for a resource."""
    try:
        q = select(ConfigChangeHistoryModel).where(
            ConfigChangeHistoryModel.organization_id == org_id,
            ConfigChangeHistoryModel.resource_id == resource_id,
        )
        q = q.order_by(ConfigChangeHistoryModel.changed_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [ConfigChangeHistoryOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("get_config_history error: %s", e)
        return []


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/drift/alerts — List correlated alerts
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/drift/alerts", response_model=list[CorrelatedAlertOut])
async def list_alerts(
    org_id: str = Depends(require_org_id),
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[CorrelatedAlertOut]:
    """List correlated security alerts with optional status and severity filters."""
    try:
        q = select(CorrelatedAlertModel).where(
            CorrelatedAlertModel.organization_id == org_id
        )
        if status:
            q = q.where(CorrelatedAlertModel.status == status.lower())
        if severity:
            q = q.where(CorrelatedAlertModel.combined_severity == severity.upper())

        q = q.order_by(CorrelatedAlertModel.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [CorrelatedAlertOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_alerts error: %s", e)
        return []


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/drift/correlation-rules — Create correlation rule
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/cspm/drift/correlation-rules",
    response_model=CorrelationRuleOut,
    status_code=201,
)
async def create_correlation_rule(
    payload: CorrelationRuleRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> CorrelationRuleOut:
    """Create a new event correlation rule."""
    try:
        import uuid
        from datetime import datetime, timezone

        rule = CorrelationRuleModel(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            name=payload.name,
            description=payload.description,
            group_by=payload.group_by,
            event_types=payload.event_types,
            time_window_seconds=payload.time_window_seconds,
            min_events=payload.min_events,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return CorrelationRuleOut.model_validate(rule)
    except Exception as e:
        logger.error("create_correlation_rule error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create correlation rule")


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/drift/correlation-rules — List correlation rules
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/cspm/drift/correlation-rules", response_model=list[CorrelationRuleOut]
)
async def list_correlation_rules(
    org_id: str = Depends(require_org_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[CorrelationRuleOut]:
    """List all correlation rules for the organization."""
    try:
        q = select(CorrelationRuleModel).where(
            CorrelationRuleModel.organization_id == org_id
        )
        q = q.order_by(CorrelationRuleModel.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [CorrelationRuleOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_correlation_rules error: %s", e)
        return []
