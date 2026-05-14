"""Audit log repository — append-only audit log queries."""

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLogModel


class AuditRepository:
    """Database access layer for audit logs.

    Append-only: only create() and delete_before() are allowed.
    No update operations.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(
        self,
        organization_id: str,
        event_type: str,
        user_id: str | None = None,
        event_data: dict | None = None,
        success: bool = True,
        failure_reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLogModel:
        """Append a new audit log entry."""
        log = AuditLogModel(
            organization_id=organization_id,
            user_id=user_id,
            event_type=event_type,
            event_data=event_data or {},
            success=success,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
        )
        self._db.add(log)
        await self._db.commit()
        return log

    async def list_by_org(
        self,
        organization_id: str,
        limit: int = 100,
        offset: int = 0,
        event_type: str | None = None,
        user_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[AuditLogModel]:
        """List audit log entries for an organization with optional filters."""
        stmt = select(AuditLogModel).where(
            AuditLogModel.organization_id == organization_id
        )
        if event_type:
            stmt = stmt.where(AuditLogModel.event_type == event_type)
        if user_id:
            stmt = stmt.where(AuditLogModel.user_id == user_id)
        if since:
            stmt = stmt.where(AuditLogModel.timestamp >= since)
        if until:
            stmt = stmt.where(AuditLogModel.timestamp <= until)

        stmt = stmt.order_by(AuditLogModel.timestamp.desc()).limit(limit).offset(offset)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_org(self, organization_id: str) -> int:
        """Count total audit log entries for an organization."""
        result = await self._db.execute(
            select(func.count(AuditLogModel.id)).where(
                AuditLogModel.organization_id == organization_id
            )
        )
        return result.scalar() or 0

    async def delete_before(self, cutoff: datetime) -> int:
        """Delete audit log entries older than cutoff (retention enforcement only).

        Returns the number of rows deleted.
        """
        result = await self._db.execute(
            delete(AuditLogModel).where(AuditLogModel.timestamp < cutoff)
        )
        await self._db.commit()
        return result.rowcount or 0

    async def get_stats(self) -> dict[str, Any]:
        """Return aggregate stats for the audit log table."""
        result = await self._db.execute(
            select(
                func.count(AuditLogModel.id).label("total"),
                func.min(AuditLogModel.timestamp).label("oldest"),
                func.max(AuditLogModel.timestamp).label("newest"),
            )
        )
        row = result.one()
        return {
            "total_entries": row.total or 0,
            "oldest_entry": row.oldest.isoformat() if row.oldest else None,
            "newest_entry": row.newest.isoformat() if row.newest else None,
        }
