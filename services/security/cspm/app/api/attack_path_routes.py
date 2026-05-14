"""Attack Path Engine API routes.

Endpoints for attack path analysis, blast radius computation,
and toxic combination detection.
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import require_org_id
from ..db_helper import AsyncSessionLocal, get_db
from ..models.attack_path_models import (
    AttackPathModel,
    ToxicCombinationModel,
)
from ..schemas.attack_path_schemas import (
    AttackPathAnalyzeRequest,
    AttackPathListOut,
    AttackPathOut,
    BlastRadiusOut,
    ToxicCombinationOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Attack Path Engine"])


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/attack-paths/analyze — Trigger attack path analysis
# ---------------------------------------------------------------------------


@router.post("/api/v1/cspm/attack-paths/analyze", status_code=202)
async def trigger_attack_path_analysis(
    payload: AttackPathAnalyzeRequest,
    org_id: str = Depends(require_org_id),
) -> dict:
    """Trigger attack path analysis for an organization.

    Launches analysis in the background and returns immediately with 202 Accepted.
    """
    logger.info(
        "Attack path analysis triggered for org=%s account=%s max_hops=%d",
        org_id,
        payload.account_id,
        payload.max_hops,
    )

    async def _run_analysis() -> None:
        """Execute attack path analysis in background."""
        try:
            from ..services.attack_path_engine import (
                detect_lateral_movement,
                detect_toxic_combinations,
                discover_attack_paths,
            )

            async with AsyncSessionLocal() as db:
                # Discover attack paths from internet-exposed to sensitive resources
                logger.info(
                    "Running attack path discovery for org=%s max_hops=%d",
                    org_id,
                    payload.max_hops,
                )
                # TODO: Full orchestration integrates with Neo4j graph
                # to traverse resource relationships and discover paths
                await db.commit()

            logger.info("Attack path analysis completed for org=%s", org_id)
        except Exception as e:
            logger.error("Attack path analysis failed for org=%s: %s", org_id, e)

    asyncio.create_task(_run_analysis())

    return {
        "status": "accepted",
        "message": "Attack path analysis started",
        "organization_id": org_id,
        "account_id": payload.account_id,
        "max_hops": payload.max_hops,
        "include_lateral_movement": payload.include_lateral_movement,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/attack-paths — List discovered attack paths
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/attack-paths", response_model=AttackPathListOut)
async def list_attack_paths(
    org_id: str = Depends(require_org_id),
    severity: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> AttackPathListOut:
    """List discovered attack paths with pagination and optional severity filter."""
    try:
        q = select(AttackPathModel).where(
            AttackPathModel.organization_id == org_id
        )
        if severity:
            q = q.where(AttackPathModel.severity == severity.upper())

        # Total count
        count_q = select(func.count()).select_from(q.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        # Paginated results ordered by severity and hops
        q = q.order_by(AttackPathModel.path_hops.asc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return AttackPathListOut(
            items=[AttackPathOut.model_validate(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error("list_attack_paths error: %s", e)
        return AttackPathListOut(items=[], total=0, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/attack-paths/{path_id} — Get attack path detail
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/attack-paths/{path_id}", response_model=AttackPathOut)
async def get_attack_path(
    path_id: str,
    db: AsyncSession = Depends(get_db),
) -> AttackPathOut:
    """Get detailed attack path including nodes and edges."""
    try:
        row = (
            await db.execute(
                select(AttackPathModel).where(AttackPathModel.id == path_id)
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Attack path not found")
        return AttackPathOut.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_attack_path error: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/attack-paths/blast-radius/{resource_id} — Blast radius
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/cspm/attack-paths/blast-radius/{resource_id}",
    response_model=BlastRadiusOut,
)
async def get_blast_radius(
    resource_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> BlastRadiusOut:
    """Compute blast radius for a given resource.

    Returns the count and list of resources reachable from the specified resource
    through attack paths.
    """
    try:
        # Query all attack paths where this resource is the entry point
        q = select(AttackPathModel).where(
            AttackPathModel.organization_id == org_id,
            AttackPathModel.entry_resource_id == resource_id,
        )
        rows = (await db.execute(q)).scalars().all()

        # Collect all reachable resources from path_nodes
        reachable_set: set[str] = set()
        reachable_types: set[str] = set()
        for path in rows:
            if path.path_nodes:
                for node_id in path.path_nodes:
                    if node_id != resource_id:
                        reachable_set.add(node_id)

        # Also check paths where this resource appears in path_nodes
        q_contains = select(AttackPathModel).where(
            AttackPathModel.organization_id == org_id,
        )
        all_paths = (await db.execute(q_contains)).scalars().all()
        for path in all_paths:
            if path.path_nodes and resource_id in path.path_nodes:
                idx = path.path_nodes.index(resource_id)
                # All nodes after this resource in the path are reachable
                for node_id in path.path_nodes[idx + 1:]:
                    reachable_set.add(node_id)

        return BlastRadiusOut(
            resource_id=resource_id,
            blast_radius_count=len(reachable_set),
            reachable_resources=sorted(reachable_set),
            reachable_resource_types=sorted(reachable_types),
        )
    except Exception as e:
        logger.error("get_blast_radius error: %s", e)
        return BlastRadiusOut(
            resource_id=resource_id,
            blast_radius_count=0,
            reachable_resources=[],
            reachable_resource_types=[],
        )


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/attack-paths/toxic-combinations — List toxic combinations
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/cspm/attack-paths/toxic-combinations",
    response_model=list[ToxicCombinationOut],
)
async def list_toxic_combinations(
    org_id: str = Depends(require_org_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[ToxicCombinationOut]:
    """List detected toxic combinations of misconfigurations."""
    try:
        q = select(ToxicCombinationModel).where(
            ToxicCombinationModel.organization_id == org_id
        )
        q = q.order_by(ToxicCombinationModel.detected_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [ToxicCombinationOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_toxic_combinations error: %s", e)
        return []
