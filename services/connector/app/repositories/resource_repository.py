"""Repository for discovered cloud resource data access."""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select, func, update, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.time_utils import utcnow
from ..models.cloud_account import DiscoveredResourceModel

logger = logging.getLogger(__name__)


class ResourceRepository:
    """Data access layer for discovered cloud resources."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, resource_id: str) -> DiscoveredResourceModel | None:
        """Get a resource by its internal UUID."""
        result = await self._session.execute(
            select(DiscoveredResourceModel).where(DiscoveredResourceModel.id == resource_id)
        )
        return result.scalar_one_or_none()

    async def get_by_cloud_id(
        self, cloud_resource_id: str, organization_id: str
    ) -> DiscoveredResourceModel | None:
        """Get a resource by its cloud-native ID (ARN, Azure ID, etc.)."""
        result = await self._session.execute(
            select(DiscoveredResourceModel).where(
                DiscoveredResourceModel.cloud_resource_id == cloud_resource_id,
                DiscoveredResourceModel.organization_id == organization_id,
                DiscoveredResourceModel.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_by_account(
        self,
        account_id: str,
        organization_id: str,
        provider: str | None = None,
        resource_type: str | None = None,
        region: str | None = None,
        is_public: bool | None = None,
        environment: str | None = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DiscoveredResourceModel]:
        """List resources for an account with optional filters."""
        stmt = select(DiscoveredResourceModel).where(
            DiscoveredResourceModel.account_id == account_id,
            DiscoveredResourceModel.organization_id == organization_id,
        )
        if not include_deleted:
            stmt = stmt.where(DiscoveredResourceModel.is_deleted == False)  # noqa: E712
        if provider:
            stmt = stmt.where(DiscoveredResourceModel.provider == provider)
        if resource_type:
            stmt = stmt.where(DiscoveredResourceModel.resource_type == resource_type)
        if region:
            stmt = stmt.where(DiscoveredResourceModel.region == region)
        if is_public is not None:
            stmt = stmt.where(DiscoveredResourceModel.is_public == is_public)
        if environment:
            stmt = stmt.where(DiscoveredResourceModel.environment == environment)

        stmt = stmt.order_by(DiscoveredResourceModel.last_seen_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_account(
        self, account_id: str, include_deleted: bool = False
    ) -> int:
        """Count resources for an account."""
        stmt = select(func.count()).select_from(DiscoveredResourceModel).where(
            DiscoveredResourceModel.account_id == account_id
        )
        if not include_deleted:
            stmt = stmt.where(DiscoveredResourceModel.is_deleted == False)  # noqa: E712
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def count_by_org(
        self, organization_id: str, include_deleted: bool = False
    ) -> int:
        """Count all resources for an organization."""
        stmt = select(func.count()).select_from(DiscoveredResourceModel).where(
            DiscoveredResourceModel.organization_id == organization_id
        )
        if not include_deleted:
            stmt = stmt.where(DiscoveredResourceModel.is_deleted == False)  # noqa: E712
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_summary_by_org(self, organization_id: str) -> dict[str, Any]:
        """
        Return aggregated resource counts grouped by provider and resource_type.
        Used for the /resources/summary endpoint.
        """
        stmt = (
            select(
                DiscoveredResourceModel.provider,
                DiscoveredResourceModel.resource_type,
                func.count().label("count"),
            )
            .where(
                DiscoveredResourceModel.organization_id == organization_id,
                DiscoveredResourceModel.is_deleted == False,  # noqa: E712
            )
            .group_by(
                DiscoveredResourceModel.provider,
                DiscoveredResourceModel.resource_type,
            )
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        summary: dict[str, Any] = {"by_provider": {}, "by_type": {}, "total": 0}
        for row in rows:
            summary["by_provider"][row.provider] = (
                summary["by_provider"].get(row.provider, 0) + row.count
            )
            summary["by_type"][row.resource_type] = (
                summary["by_type"].get(row.resource_type, 0) + row.count
            )
            summary["total"] += row.count

        return summary

    async def upsert(self, resource_data: dict[str, Any]) -> tuple[str, bool]:
        """
        Upsert a resource record.

        Returns (resource_id, was_created) where was_created=True means
        this is a new resource, False means it was updated.
        """
        stmt = (
            pg_insert(DiscoveredResourceModel)
            .values(**resource_data)
            .on_conflict_do_update(
                constraint="uq_resource_org",
                set_={
                    "name": resource_data["name"],
                    "tags": resource_data["tags"],
                    "raw": resource_data["raw"],
                    "is_public": resource_data["is_public"],
                    "environment": resource_data["environment"],
                    "resource_hash": resource_data["resource_hash"],
                    "last_seen_at": resource_data.get("last_seen_at", utcnow()),
                    "last_synced_at": utcnow(),
                    "is_deleted": False,
                    "deleted_at": None,
                },
            )
            .returning(
                DiscoveredResourceModel.id,
                DiscoveredResourceModel.first_seen_at,
            )
        )
        result = await self._session.execute(stmt)
        row = result.fetchone()
        resource_id = row[0]
        first_seen = row[1]
        # If first_seen_at equals the value we just inserted, it's a new record
        was_created = first_seen == resource_data.get("first_seen_at")
        return resource_id, was_created

    async def bulk_upsert(
        self, resources: list[dict[str, Any]]
    ) -> tuple[int, int]:
        """
        Bulk upsert a list of resource records.

        Returns (created_count, updated_count).
        Uses PostgreSQL INSERT ... ON CONFLICT for efficiency.
        """
        if not resources:
            return 0, 0

        created = 0
        updated = 0

        # Process in batches of 500 to avoid parameter limits
        batch_size = 500
        for i in range(0, len(resources), batch_size):
            batch = resources[i : i + batch_size]
            stmt = (
                pg_insert(DiscoveredResourceModel)
                .values(batch)
                .on_conflict_do_update(
                    constraint="uq_resource_org",
                    set_={
                        "name": pg_insert(DiscoveredResourceModel).excluded.name,
                        "tags": pg_insert(DiscoveredResourceModel).excluded.tags,
                        "raw": pg_insert(DiscoveredResourceModel).excluded.raw,
                        "is_public": pg_insert(DiscoveredResourceModel).excluded.is_public,
                        "environment": pg_insert(DiscoveredResourceModel).excluded.environment,
                        "resource_hash": pg_insert(DiscoveredResourceModel).excluded.resource_hash,
                        "last_seen_at": pg_insert(DiscoveredResourceModel).excluded.last_seen_at,
                        "last_synced_at": utcnow(),
                        "is_deleted": False,
                        "deleted_at": None,
                    },
                )
                .returning(
                    DiscoveredResourceModel.id,
                    DiscoveredResourceModel.first_seen_at,
                )
            )
            result = await self._session.execute(stmt)
            rows = result.fetchall()
            for row in rows:
                # Heuristic: if first_seen_at is very recent, it was just created.
                # Compare as naive UTC so both sides are consistent.
                first_seen = row[1]
                if first_seen.tzinfo is not None:
                    first_seen = first_seen.replace(tzinfo=None)
                age_seconds = (utcnow().replace(tzinfo=None) - first_seen).total_seconds()
                if age_seconds < 5:
                    created += 1
                else:
                    updated += 1

        return created, updated

    async def mark_deleted(
        self,
        cloud_resource_ids: list[str],
        organization_id: str,
    ) -> int:
        """
        Soft-delete resources that no longer exist in the cloud account.

        Returns the number of rows marked as deleted.
        """
        if not cloud_resource_ids:
            return 0

        now = utcnow()
        result = await self._session.execute(
            update(DiscoveredResourceModel)
            .where(
                DiscoveredResourceModel.cloud_resource_id.in_(cloud_resource_ids),
                DiscoveredResourceModel.organization_id == organization_id,
                DiscoveredResourceModel.is_deleted == False,  # noqa: E712
            )
            .values(is_deleted=True, deleted_at=now, last_synced_at=now)
        )
        return result.rowcount

    async def get_resource_hashes(
        self, account_id: str, organization_id: str
    ) -> dict[str, str]:
        """
        Return a mapping of cloud_resource_id → resource_hash for all
        non-deleted resources in an account.  Used for incremental sync
        change detection.
        """
        result = await self._session.execute(
            select(
                DiscoveredResourceModel.cloud_resource_id,
                DiscoveredResourceModel.resource_hash,
            ).where(
                DiscoveredResourceModel.account_id == account_id,
                DiscoveredResourceModel.organization_id == organization_id,
                DiscoveredResourceModel.is_deleted == False,  # noqa: E712
            )
        )
        return {row.cloud_resource_id: row.resource_hash for row in result.all()}
