"""API routes for discovered resources — tenant-isolated by organization_id."""

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.auth import require_org_id
from app.models import DiscoveredResourceModel

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("")
async def list_resources(
    organization_id: str = Depends(require_org_id),
    account_id: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    region: str | None = Query(default=None),
    search: str | None = Query(default=None),
    is_public: bool | None = Query(default=None),
    environment: str | None = Query(default=None),
    freshness_state: str | None = Query(
        default=None,
        description="Filter by freshness state: fresh | stale | deleted",
    ),
    include_stale: bool = Query(
        default=True,
        description="Include stale resources in results (default: true). "
                    "Set false to see only confirmed-fresh resources.",
    ),
    limit: int = Query(default=100, le=2000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List discovered resources for the authenticated organization only."""

    # Always scope to the authenticated org — this is the core tenant isolation
    stmt = select(DiscoveredResourceModel).where(
        DiscoveredResourceModel.organization_id == organization_id,
        DiscoveredResourceModel.is_deleted == False,  # noqa: E712
    )

    if account_id:
        stmt = stmt.where(DiscoveredResourceModel.account_id == account_id)
    if provider:
        stmt = stmt.where(DiscoveredResourceModel.provider == provider)
    if resource_type:
        stmt = stmt.where(DiscoveredResourceModel.resource_type.ilike(f"%{resource_type}%"))
    if region:
        stmt = stmt.where(DiscoveredResourceModel.region == region)
    if is_public is not None:
        stmt = stmt.where(DiscoveredResourceModel.is_public == is_public)
    if environment:
        stmt = stmt.where(DiscoveredResourceModel.environment == environment)
    if search:
        stmt = stmt.where(DiscoveredResourceModel.name.ilike(f"%{search}%"))
    if freshness_state:
        stmt = stmt.where(DiscoveredResourceModel.freshness_state == freshness_state)
    elif not include_stale:
        stmt = stmt.where(DiscoveredResourceModel.freshness_state == "fresh")

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Order by resource_type first so diverse types are interleaved, then by name
    stmt = stmt.order_by(DiscoveredResourceModel.resource_type, DiscoveredResourceModel.name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    resources = result.scalars().all()

    return {
        "resources": [_resource_to_dict(r) for r in resources],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/summary")
async def get_resources_summary(
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get resource counts for the authenticated organization only."""

    base_filter = (
        DiscoveredResourceModel.organization_id == organization_id,
        DiscoveredResourceModel.is_deleted == False,  # noqa: E712
    )

    provider_stmt = (
        select(DiscoveredResourceModel.provider, func.count().label("count"))
        .where(*base_filter)
        .group_by(DiscoveredResourceModel.provider)
    )
    provider_result = await db.execute(provider_stmt)
    by_provider = {row.provider: row.count for row in provider_result}

    type_stmt = (
        select(DiscoveredResourceModel.resource_type, func.count().label("count"))
        .where(*base_filter)
        .group_by(DiscoveredResourceModel.resource_type)
        .order_by(func.count().desc())
        .limit(10)
    )
    type_result = await db.execute(type_stmt)
    by_type = {row.resource_type: row.count for row in type_result}

    freshness_stmt = (
        select(DiscoveredResourceModel.freshness_state, func.count().label("count"))
        .where(*base_filter)
        .group_by(DiscoveredResourceModel.freshness_state)
    )
    freshness_result = await db.execute(freshness_stmt)
    by_freshness = {row.freshness_state: row.count for row in freshness_result}

    total_stmt = select(func.count()).where(*base_filter)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0

    return {
        "total": total,
        "by_provider": by_provider,
        "by_type": by_type,
        "by_freshness": by_freshness,
    }


def _resource_to_dict(r: DiscoveredResourceModel) -> dict[str, Any]:
    return {
        "id": r.id,
        "cloud_resource_id": r.cloud_resource_id,
        "provider": r.provider,
        "account_id": r.account_id,
        "organization_id": r.organization_id,
        "region": r.region,
        "resource_type": r.resource_type,
        "name": r.name,
        "tags": r.tags or {},
        "is_public": r.is_public,
        "environment": r.environment,
        "freshness_state": getattr(r, "freshness_state", "fresh"),
        "missed_sync_count": getattr(r, "missed_sync_count", 0),
        "first_seen_at": r.first_seen_at.isoformat() if r.first_seen_at else None,
        "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
    }


# ── Resource-type catalog ─────────────────────────────────────────────────────

@router.get(
    "/catalog",
    summary="List supported resource types per provider",
    description=(
        "Returns the complete catalog of resource types the connector can "
        "discover, grouped by cloud provider. Downstream services and the UI "
        "use this to know what types to expect in the asset graph."
    ),
)
async def get_resource_type_catalog() -> dict[str, Any]:
    """Return the supported resource type catalog for all providers."""
    from app.clients.aws import AWSClient
    from app.clients.azure import AzureClient
    from app.clients.gcp import GCPClient
    from app.clients.oci import OCIClient

    def _extract_mapping(client_cls: type) -> dict[str, str]:
        """Extract RESOURCE_TYPE_MAPPING from a client class if it exists."""
        return dict(getattr(client_cls, "RESOURCE_TYPE_MAPPING", {}))

    aws_mapping = _extract_mapping(AWSClient)
    azure_mapping = _extract_mapping(AzureClient)
    gcp_mapping = _extract_mapping(GCPClient)
    oci_mapping = _extract_mapping(OCIClient)

    return {
        "providers": {
            "aws": {
                "display_name": "Amazon Web Services",
                "resource_types": [
                    {"service_key": k, "resource_type": v}
                    for k, v in sorted(aws_mapping.items())
                ],
                "total": len(aws_mapping),
            },
            "azure": {
                "display_name": "Microsoft Azure",
                "resource_types": [
                    {"service_key": k, "resource_type": v}
                    for k, v in sorted(azure_mapping.items())
                ],
                "total": len(azure_mapping),
            },
            "gcp": {
                "display_name": "Google Cloud Platform",
                "resource_types": [
                    {"service_key": k, "resource_type": v}
                    for k, v in sorted(gcp_mapping.items())
                ],
                "total": len(gcp_mapping),
            },
            "oci": {
                "display_name": "Oracle Cloud Infrastructure",
                "resource_types": [
                    {"service_key": k, "resource_type": v}
                    for k, v in sorted(oci_mapping.items())
                ],
                "total": len(oci_mapping),
            },
        },
        "total_types": len(aws_mapping) + len(azure_mapping) + len(gcp_mapping) + len(oci_mapping),
    }
