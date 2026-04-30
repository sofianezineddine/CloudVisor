"""Historical snapshot service for time-travel queries."""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


logger = logging.getLogger(__name__)


class SnapshotBase(DeclarativeBase):
    pass


class AssetSnapshotModel(SnapshotBase):
    """Stores historical snapshots of asset nodes."""

    __tablename__ = "asset_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[dict] = mapped_column(JSON, nullable=True)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    is_public: Mapped[bool] = mapped_column(Integer, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    open_findings_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    snapshot_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    snapshot_version: Mapped[int] = mapped_column(Integer, default=1)
    diff_from_previous: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "organization_id": self.organization_id,
            "provider": self.provider,
            "account_id": self.account_id,
            "region": self.region,
            "resource_type": self.resource_type,
            "name": self.name,
            "tags": self.tags,
            "environment": self.environment,
            "is_public": bool(self.is_public),
            "risk_score": self.risk_score,
            "open_findings_count": self.open_findings_count,
            "raw_data": self.raw_data,
            "snapshot_timestamp": self.snapshot_timestamp.isoformat()
            if self.snapshot_timestamp
            else None,
            "snapshot_version": self.snapshot_version,
            "diff_from_previous": self.diff_from_previous,
        }


class RelationshipSnapshotModel(SnapshotBase):
    """Stores historical snapshots of relationships."""

    __tablename__ = "relationship_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    properties: Mapped[dict] = mapped_column(JSON, nullable=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    snapshot_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(Integer, default=0)


class SnapshotService:
    """Service for managing asset snapshots."""

    def __init__(self, db_session):
        self._session = db_session

    async def create_snapshot(
        self,
        asset_data: dict[str, Any],
        previous_snapshot: dict[str, Any] | None = None,
    ) -> "AssetSnapshotModel":
        """Create a versioned snapshot of an asset state."""
        diff = self._compute_diff(asset_data, previous_snapshot)

        # Get next version number
        from sqlalchemy import select, func
        version_result = await self._session.execute(
            select(func.max(AssetSnapshotModel.snapshot_version)).where(
                AssetSnapshotModel.asset_id == asset_data.get("id", "")
            )
        )
        max_version = version_result.scalar() or 0

        snapshot = AssetSnapshotModel(
            asset_id=asset_data.get("id", ""),
            organization_id=asset_data.get("organization_id", ""),
            provider=asset_data.get("provider", ""),
            account_id=asset_data.get("account_id", ""),
            region=asset_data.get("region", ""),
            resource_type=asset_data.get("resource_type", ""),
            name=asset_data.get("name", ""),
            tags=asset_data.get("tags"),
            environment=asset_data.get("environment", "unknown"),
            is_public=1 if asset_data.get("is_public") else 0,
            risk_score=asset_data.get("risk_score", 0),
            open_findings_count=asset_data.get("open_findings_count", 0),
            raw_data=asset_data.get("raw"),
            snapshot_timestamp=datetime.utcnow(),
            snapshot_version=max_version + 1,
            diff_from_previous=diff,
        )

        self._session.add(snapshot)
        await self._session.flush()
        return snapshot

    def _compute_diff(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Compute diff between current and previous snapshot."""
        if not previous:
            return {"changed": True, "fields": list(current.keys())}

        diff = {"changed": False, "fields": []}

        for key, value in current.items():
            prev_value = previous.get(key)
            if value != prev_value:
                diff["changed"] = True
                diff["fields"].append(key)

        return diff

    async def get_snapshots(
        self,
        asset_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AssetSnapshotModel]:
        """Get historical snapshots for an asset."""
        from sqlalchemy import select, desc

        query = select(AssetSnapshotModel).where(AssetSnapshotModel.asset_id == asset_id)

        if start_time:
            query = query.where(AssetSnapshotModel.snapshot_timestamp >= start_time)
        if end_time:
            query = query.where(AssetSnapshotModel.snapshot_timestamp <= end_time)

        query = query.order_by(desc(AssetSnapshotModel.snapshot_timestamp)).limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_asset_at_time(
        self,
        asset_id: str,
        timestamp: datetime,
    ) -> AssetSnapshotModel | None:
        """Get asset state at a specific point in time."""
        from sqlalchemy import select

        query = (
            select(AssetSnapshotModel)
            .where(
                AssetSnapshotModel.asset_id == asset_id,
                AssetSnapshotModel.snapshot_timestamp <= timestamp,
            )
            .order_by(AssetSnapshotModel.snapshot_timestamp.desc())
            .limit(1)
        )

        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_snapshot(self, asset_id: str) -> AssetSnapshotModel | None:
        """Get the most recent snapshot for an asset."""
        from sqlalchemy import select, desc

        query = (
            select(AssetSnapshotModel)
            .where(
                AssetSnapshotModel.asset_id == asset_id,
            )
            .order_by(desc(AssetSnapshotModel.snapshot_timestamp))
            .limit(1)
        )

        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def cleanup_old_snapshots(self, retention_days: int = 90) -> int:
        """Delete snapshots older than retention period."""
        from datetime import timedelta
        from sqlalchemy import delete, select, func

        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        count_query = select(func.count(AssetSnapshotModel.id)).where(
            AssetSnapshotModel.snapshot_timestamp < cutoff
        )
        result = await self._session.execute(count_query)
        count = result.scalar() or 0

        delete_query = delete(AssetSnapshotModel).where(
            AssetSnapshotModel.snapshot_timestamp < cutoff
        )
        await self._session.execute(delete_query)
        await self._session.commit()

        return count

    async def get_snapshot_stats(self, organization_id: str) -> dict[str, Any]:
        """Get snapshot statistics."""
        from sqlalchemy import select, func

        query = select(
            func.count(AssetSnapshotModel.id).label("total_snapshots"),
            func.count(func.distinct(AssetSnapshotModel.asset_id)).label("unique_assets"),
            func.min(AssetSnapshotModel.snapshot_timestamp).label("oldest"),
            func.max(AssetSnapshotModel.snapshot_timestamp).label("newest"),
        ).where(AssetSnapshotModel.organization_id == organization_id)

        result = await self._session.execute(query)
        row = result.one()

        return {
            "total_snapshots": row.total_snapshots or 0,
            "unique_assets": row.unique_assets or 0,
            "oldest": row.oldest.isoformat() if row.oldest else None,
            "newest": row.newest.isoformat() if row.newest else None,
        }
