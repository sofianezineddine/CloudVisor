"""Audit log retention service — spec §3.3: retain 365 days minimum.

Runs as a background task on startup. Deletes audit_log rows older than
`audit_log_retention_days` (default 365, configurable up to 7 years).

The audit_log table is append-only (no updates, no deletes by application code)
EXCEPT for this retention job which enforces the configured TTL.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLogModel

logger = logging.getLogger(__name__)

# Run retention cleanup every 24 hours
_RETENTION_INTERVAL_SECONDS = 24 * 60 * 60


class AuditRetentionService:
    """Enforces audit log retention policy per spec §3.3."""

    def __init__(self, session_factory: Any, retention_days: int = 365):
        self._session_factory = session_factory
        self._retention_days = max(retention_days, 365)  # never less than 365 days
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Start the background retention loop."""
        self._task = asyncio.create_task(self._retention_loop())
        logger.info(
            f"Audit retention job started — retaining {self._retention_days} days of logs"
        )

    async def stop(self) -> None:
        """Cancel the background task on shutdown."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Audit retention job stopped")

    async def _retention_loop(self) -> None:
        """Run cleanup once per day."""
        # Wait 60 seconds after startup before first run (let DB settle)
        await asyncio.sleep(60)
        while True:
            try:
                deleted = await self.run_cleanup()
                logger.info(f"Audit retention: deleted {deleted} expired log entries")
            except Exception as e:
                logger.error(f"Audit retention cleanup failed: {e}")
            await asyncio.sleep(_RETENTION_INTERVAL_SECONDS)

    async def run_cleanup(self) -> int:
        """Delete audit log entries older than retention_days.

        Returns the number of rows deleted.
        """
        cutoff = datetime.utcnow() - timedelta(days=self._retention_days)

        async with self._session_factory() as session:
            # Count first for logging
            count_result = await session.execute(
                select(func.count(AuditLogModel.id)).where(
                    AuditLogModel.timestamp < cutoff
                )
            )
            count = count_result.scalar() or 0

            if count > 0:
                await session.execute(
                    delete(AuditLogModel).where(AuditLogModel.timestamp < cutoff)
                )
                await session.commit()
                logger.info(
                    f"Audit retention: purged {count} entries older than "
                    f"{cutoff.date()} (retention={self._retention_days}d)"
                )

        return count

    async def get_stats(self) -> dict:
        """Return audit log stats — total rows, oldest entry, retention config."""
        async with self._session_factory() as session:
            result = await session.execute(
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
                "retention_days": self._retention_days,
                "cutoff_date": (
                    datetime.utcnow() - timedelta(days=self._retention_days)
                ).date().isoformat(),
            }
