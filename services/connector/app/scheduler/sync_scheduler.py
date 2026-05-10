"""Background sync scheduler for cloud accounts."""

import asyncio
import json
import logging
import random
import time
from datetime import timedelta
from typing import Any

from sqlalchemy import select

from ..core.time_utils import utcnow
from ..models import CloudAccountModel
from ..services.discovery import CloudDiscoveryService, DiscoveryResult
from ..producers import ResourceEventProducer
from ..metrics.prometheus import ConnectorMetrics

logger = logging.getLogger(__name__)

# Redis key templates
_SCHEDULE_KEY = "connector:schedule:{account_id}"
_SYNC_LOCK_KEY = "connector:sync_lock:{account_id}"
_SYNC_PROGRESS_KEY = "connector:sync_progress:{account_id}"
_RESOURCES_CACHE_KEY = "connector:resources:{account_id}"


class SyncScheduler:
    """
    Schedules and executes recurring sync jobs for cloud accounts.

    Uses Redis for distributed locking and scheduling state.
    Supports different polling intervals per account (5/15/30/60 min).

    Thundering-herd protection: on startup, ``last_sync_at`` in each schedule
    is seeded with a randomised "recent" time so accounts are spread across
    the polling interval instead of all firing at once.
    """

    # Seconds added on top of the sync timeout when acquiring the Redis lock,
    # to give the sync clean shutdown headroom before the lock can be re-acquired.
    _LOCK_HEADROOM_SECONDS = 60

    def __init__(
        self,
        redis_client: Any,
        event_producer: ResourceEventProducer,
        db_session_factory: Any,
        vault_client: Any | None = None,
        sync_timeout_seconds: int = 300,
    ):
        self._redis = redis_client
        self._producer = event_producer
        self._db_session_factory = db_session_factory
        self._vault_client = vault_client
        self._sync_timeout_seconds = sync_timeout_seconds
        self._running = False
        self._tasks: dict[str, asyncio.Task] = {}

    async def start(self) -> None:
        """Start the sync scheduler and re-register all active accounts from DB."""
        self._running = True
        logger.info("Sync scheduler started")

        # Re-register all active accounts from DB into Redis.
        # This ensures schedules survive connector restarts.
        await self._restore_schedules_from_db()

        # Start monitoring loop
        asyncio.create_task(self._monitor_loop())

    async def _restore_schedules_from_db(self) -> None:
        """Re-register all active accounts from DB into Redis on startup.

        Each account's ``last_sync_at`` in Redis is seeded with a randomised
        time in the past ≤ polling_interval_minutes. This prevents all
        accounts from firing a sync simultaneously on a cold start and
        thundering-herding the cloud APIs.
        """
        try:
            async with self._db_session_factory() as session:
                stmt = select(CloudAccountModel).where(
                    CloudAccountModel.status.in_(["active", "pending"]),
                    CloudAccountModel.deleted_at.is_(None),
                )
                result = await session.execute(stmt)
                accounts = result.scalars().all()

                for account in accounts:
                    await self.schedule_account(
                        account_id=account.id,
                        organization_id=account.organization_id,
                        provider=account.provider,
                        interval_minutes=account.polling_interval_minutes,
                    )
                    # Seed last_sync_at with a random offset in [0, interval_minutes)
                    # minutes ago so accounts don't all fire at once on restart.
                    interval_seconds = account.polling_interval_minutes * 60
                    random_offset = random.uniform(0, interval_seconds)
                    seed_time = utcnow() - timedelta(seconds=interval_seconds - random_offset)
                    key = _SCHEDULE_KEY.format(account_id=account.id)
                    await self._redis.hset(
                        key, "last_sync_at", seed_time.isoformat()
                    )

                logger.info(
                    f"Restored {len(accounts)} account schedules from DB with "
                    f"randomised first-sync times"
                )
        except Exception as e:
            logger.error(f"Failed to restore schedules from DB: {e}")

    async def stop(self) -> None:
        """Stop the sync scheduler and cancel all running tasks."""
        self._running = False
        logger.info("Sync scheduler stopping...")

        # Cancel all running sync tasks
        for account_id, task in self._tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._tasks.clear()
        logger.info("Sync scheduler stopped")

    async def schedule_account(
        self,
        account_id: str,
        organization_id: str,
        provider: str,
        interval_minutes: int,
    ) -> None:
        """Schedule a recurring sync for an account."""
        key = _SCHEDULE_KEY.format(account_id=account_id)
        await self._redis.hset(
            key,
            mapping={
                "interval_minutes": str(interval_minutes),
                "organization_id": organization_id,
                "provider": provider,
                "last_scheduled": utcnow().isoformat(),
            },
        )
        # TTL = 7 days — long enough to survive any reasonable downtime.
        # The scheduler re-registers on startup anyway.
        await self._redis.expire(key, 7 * 24 * 60 * 60)

        logger.info(
            f"Scheduled sync for account {account_id} every {interval_minutes} minutes"
        )

    async def cancel_account(self, account_id: str) -> None:
        """Cancel scheduled sync for an account."""
        key = _SCHEDULE_KEY.format(account_id=account_id)
        await self._redis.delete(key)

        # Cancel running task if any
        if account_id in self._tasks:
            self._tasks[account_id].cancel()
            del self._tasks[account_id]

        logger.info(f"Cancelled sync for account {account_id}")

    # ── Sync progress tracking (Redis) ────────────────────────────────────────

    async def get_sync_progress(self, account_id: str) -> dict[str, Any] | None:
        """Return the in-memory progress snapshot for an active sync, or None."""
        key = _SYNC_PROGRESS_KEY.format(account_id=account_id)
        try:
            data = await self._redis.get(key)
            if not data:
                return None
            return json.loads(data)
        except Exception as e:
            logger.warning(f"Failed to read sync progress for {account_id}: {e}")
            return None

    async def _set_sync_progress(
        self,
        account_id: str,
        progress: dict[str, Any],
        ttl_seconds: int = 600,
    ) -> None:
        """Persist a progress snapshot. 10-min TTL covers clean-up on crash."""
        key = _SYNC_PROGRESS_KEY.format(account_id=account_id)
        try:
            await self._redis.set(key, json.dumps(progress, default=str), ex=ttl_seconds)
        except Exception as e:
            logger.debug(f"Failed to persist sync progress for {account_id}: {e}")

    async def trigger_sync(
        self,
        account: CloudAccountModel,
        sync_type: str = "on_demand",
    ) -> DiscoveryResult:
        """
        Trigger a sync for a specific account.

        Handles distributed locking to prevent concurrent syncs. The lock TTL
        is ``sync_timeout_seconds * 2 + headroom`` so it outlives the sync
        itself even under timeout pressure.
        """
        lock_key = _SYNC_LOCK_KEY.format(account_id=account.id)
        lock_ttl = self._sync_timeout_seconds * 2 + self._LOCK_HEADROOM_SECONDS
        lock_acquired = await self._redis.set(lock_key, "1", nx=True, ex=lock_ttl)

        if not lock_acquired:
            logger.warning(f"Sync already in progress for account {account.id}")
            return DiscoveryResult(
                errors=1,
                error_details=["Sync already in progress"],
            )

        correlation_id = f"sync-{account.id}-{int(time.time())}"

        # Track progress for the sync-status endpoint
        await self._set_sync_progress(account.id, {
            "account_id": account.id,
            "correlation_id": correlation_id,
            "sync_type": sync_type,
            "status": "running",
            "started_at": utcnow().isoformat(),
            "discovered": 0,
            "updated": 0,
            "deleted": 0,
            "errors": 0,
        }, ttl_seconds=lock_ttl)

        try:
            logger.info(f"Starting {sync_type} sync for account {account.id}")

            ConnectorMetrics.record_sync_start(
                organization_id=account.organization_id,
                account_id=account.id,
                provider=account.provider,
                sync_type=sync_type,
            )

            discovery = CloudDiscoveryService(
                account=account,
                producer=self._producer,
                vault_client=self._vault_client,
                db_session_factory=self._db_session_factory,
            )

            # Get known resources for incremental sync
            known_resources = {}
            if sync_type == "incremental":
                known_resources = await self._load_known_resources(account.id)

            # Execute discovery
            if sync_type == "full" or not known_resources:
                result = await discovery.discover_full(correlation_id=correlation_id)
            else:
                result = await discovery.discover_incremental(
                    known_resources=known_resources,
                    correlation_id=correlation_id,
                )

            # Update account sync status
            previous_status = account.status
            await self._update_account_sync_status(account, result, sync_type)

            # Emit health_changed if status transitioned
            if previous_status != account.status:
                try:
                    await self._producer.emit_health_changed(
                        account_id=account.id,
                        organization_id=account.organization_id,
                        provider=account.provider,
                        previous_status=previous_status,
                        new_status=account.status,
                        error_message="; ".join(result.error_details) if result.errors else None,
                        resource_count=account.resource_count,
                    )
                except Exception as e:
                    logger.warning(f"Failed to emit health_changed for {account.id}: {e}")

            # Store known resources for next incremental sync
            if result.discovered > 0 or result.updated > 0:
                await self._save_known_resources(account.id, result)

            # Final progress snapshot
            await self._set_sync_progress(account.id, {
                "account_id": account.id,
                "correlation_id": correlation_id,
                "sync_type": sync_type,
                "status": "completed" if result.errors == 0 else "failed",
                "finished_at": utcnow().isoformat(),
                "discovered": result.discovered,
                "updated": result.updated,
                "deleted": result.deleted,
                "errors": result.errors,
                "error_details": result.error_details[:5],
                "duration_seconds": result.duration_seconds,
            }, ttl_seconds=3600)

            logger.info(
                f"Sync completed for account {account.id}: "
                f"{result.discovered} discovered, {result.updated} updated, "
                f"{result.deleted} deleted, {result.errors} errors "
                f"({result.duration_seconds:.2f}s)"
            )

            ConnectorMetrics.record_sync_complete(
                organization_id=account.organization_id,
                account_id=account.id,
                provider=account.provider,
                sync_type=sync_type,
                status="completed" if result.errors == 0 else "failed",
                duration_seconds=result.duration_seconds,
                discovered=result.discovered,
                updated=result.updated,
                deleted=result.deleted,
                errors=result.errors,
                resource_count=account.resource_count,
            )

            return result

        except Exception as e:
            logger.error(f"Sync failed for account {account.id}: {e}")
            ConnectorMetrics.record_error(
                organization_id=account.organization_id,
                account_id=account.id,
                provider=account.provider,
                error_type=type(e).__name__,
            )
            await self._update_account_sync_status(
                account,
                DiscoveryResult(errors=1, error_details=[str(e)]),
                sync_type,
            )
            await self._set_sync_progress(account.id, {
                "account_id": account.id,
                "correlation_id": correlation_id,
                "sync_type": sync_type,
                "status": "failed",
                "finished_at": utcnow().isoformat(),
                "error": str(e)[:500],
            }, ttl_seconds=3600)
            raise

        finally:
            await self._redis.delete(lock_key)

    async def _monitor_loop(self) -> None:
        """
        Background loop that checks for accounts due for sync.
        Runs every 30 seconds — fine-grained enough for 1-minute polling intervals.
        """
        while self._running:
            try:
                await self._check_scheduled_syncs()
            except Exception as e:
                logger.error(f"Error in sync monitor loop: {e}")
            await asyncio.sleep(30)

    async def _check_scheduled_syncs(self) -> None:
        """Check all scheduled accounts and trigger syncs if due."""
        keys = await self._redis.keys("connector:schedule:*")

        for key in keys:
            try:
                account_id = key.split(":")[-1]
                schedule_data = await self._redis.hgetall(key)

                if not schedule_data:
                    continue

                interval_minutes = int(schedule_data.get("interval_minutes", 15))
                last_sync_at = schedule_data.get("last_sync_at")

                # If no last_sync_at has been seeded, skip this tick and seed
                # one now (prevents the classic "fire immediately on first seen"
                # bug — and thundering herd on restart).
                if not last_sync_at:
                    await self._redis.hset(
                        key, "last_sync_at", utcnow().isoformat()
                    )
                    continue

                last_sync_time = _parse_iso(last_sync_at)
                next_sync_time = last_sync_time + timedelta(minutes=interval_minutes)
                if utcnow() < next_sync_time:
                    continue  # Not due yet

                # Trigger sync
                async with self._db_session_factory() as session:
                    stmt = select(CloudAccountModel).where(
                        CloudAccountModel.id == account_id,
                        CloudAccountModel.deleted_at.is_(None),
                    )
                    result = await session.execute(stmt)
                    account = result.scalar_one_or_none()

                    if account and account.status == "active":
                        await self.trigger_sync(account, sync_type="incremental")
                        await self._redis.hset(key, "last_sync_at", utcnow().isoformat())
                    elif not account:
                        # Account was deleted — clear the stale schedule
                        await self._redis.delete(key)
                        logger.info(
                            f"Cleared stale schedule for deleted account {account_id}"
                        )

            except Exception as e:
                logger.error(f"Error checking schedule for {key}: {e}")

    async def _load_schedules(self) -> None:
        """Kept for backward compatibility — actual restore is in _restore_schedules_from_db."""
        keys = await self._redis.keys("connector:schedule:*")
        logger.info(f"Found {len(keys)} existing schedule keys in Redis")

    async def _load_known_resources(self, account_id: str) -> dict[str, dict]:
        """Load known resources from Redis for incremental sync."""
        key = _RESOURCES_CACHE_KEY.format(account_id=account_id)
        data = await self._redis.get(key)
        if data:
            return json.loads(data)
        return {}

    async def _save_known_resources(
        self,
        account_id: str,
        result: DiscoveryResult,
    ) -> None:
        """Save discovered resource hashes to Redis for next incremental sync.

        We store a mapping of cloud_resource_id → resource_hash so the next
        incremental sync can detect which resources actually changed.
        """
        if not self._db_session_factory:
            return

        try:
            from sqlalchemy import select
            from ..models import DiscoveredResourceModel

            async with self._db_session_factory() as session:
                stmt = select(
                    DiscoveredResourceModel.cloud_resource_id,
                    DiscoveredResourceModel.resource_hash,
                    DiscoveredResourceModel.region,
                ).where(
                    DiscoveredResourceModel.account_id == account_id,
                    DiscoveredResourceModel.is_deleted == False,  # noqa: E712
                )
                rows = await session.execute(stmt)
                known: dict[str, dict] = {
                    row.cloud_resource_id: {
                        "resource_hash": row.resource_hash,
                        "region": row.region,
                    }
                    for row in rows
                }

            if known:
                key = _RESOURCES_CACHE_KEY.format(account_id=account_id)
                await self._redis.set(key, json.dumps(known), ex=3600)  # 1h TTL
                logger.debug(f"Saved {len(known)} resource hashes for account {account_id}")
        except Exception as e:
            logger.warning(f"Failed to save known resources for {account_id}: {e}")

    async def _update_account_sync_status(
        self,
        account: CloudAccountModel,
        result: DiscoveryResult,
        sync_type: str,
    ) -> None:
        """Update account sync status in database. Mutates ``account`` in place
        so callers can compare ``account.status`` before/after and emit health
        events.
        """
        async with self._db_session_factory() as session:
            db_account = await session.get(CloudAccountModel, account.id)
            if not db_account:
                return
            now = utcnow()
            db_account.last_sync_at = now
            if result.errors == 0:
                db_account.last_successful_sync_at = now
                db_account.consecutive_errors = 0
                db_account.sync_status = "idle"
                db_account.status = "active"
                db_account.error_message = None

                # Set resource_count to the actual count in DB (not cumulative)
                from sqlalchemy import func
                from ..models import DiscoveredResourceModel
                count_result = await session.execute(
                    select(func.count())
                    .select_from(DiscoveredResourceModel)
                    .where(
                        DiscoveredResourceModel.account_id == account.account_id,
                        DiscoveredResourceModel.is_deleted == False,  # noqa: E712
                    )
                )
                db_account.resource_count = count_result.scalar() or 0
            else:
                db_account.consecutive_errors += 1
                db_account.error_message = "; ".join(result.error_details)[:2000]
                db_account.sync_status = "error"

                if "auth" in str(result.error_details).lower():
                    if db_account.consecutive_errors >= 3:
                        db_account.status = "auth_failed"
                elif result.discovered > 0:
                    # Some resources came through — partial success
                    db_account.status = "partial_sync"
                else:
                    db_account.status = "error"

            await session.commit()

            # Propagate the mutations back onto the in-memory account object so
            # callers that emit health_changed see the final state.
            account.status = db_account.status
            account.sync_status = db_account.sync_status
            account.consecutive_errors = db_account.consecutive_errors
            account.resource_count = db_account.resource_count
            account.last_sync_at = db_account.last_sync_at
            account.last_successful_sync_at = db_account.last_successful_sync_at
            account.error_message = db_account.error_message


def _parse_iso(ts: str) -> Any:
    """Parse an ISO-8601 timestamp tolerant of ``Z`` suffix and naive values.

    Returns a tz-aware datetime (UTC) so comparisons with ``utcnow()`` work.
    """
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        # Fall back to plain parsing
        dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
