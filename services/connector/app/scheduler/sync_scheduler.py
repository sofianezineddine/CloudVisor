"""Background sync scheduler for cloud accounts."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from ..core.dependencies import get_redis
from ..models import CloudAccountModel
from ..services.discovery import CloudDiscoveryService, DiscoveryResult
from ..producers import ResourceEventProducer
from ..metrics.prometheus import ConnectorMetrics

logger = logging.getLogger(__name__)


class SyncScheduler:
    """
    Schedules and executes recurring sync jobs for cloud accounts.

    Uses Redis for distributed locking and scheduling state.
    Supports different polling intervals per account (5/15/30/60 min).
    """

    def __init__(
        self,
        redis_client: Any,
        event_producer: ResourceEventProducer,
        db_session_factory: Any,
        vault_client: Any | None = None,
    ):
        self._redis = redis_client
        self._producer = event_producer
        self._db_session_factory = db_session_factory
        self._vault_client = vault_client
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
        """Re-register all active accounts from DB into Redis on startup."""
        try:
            async with self._db_session_factory() as session:
                stmt = select(CloudAccountModel).where(
                    CloudAccountModel.status.in_(["active", "pending"])
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

                logger.info(
                    f"Restored {len(accounts)} account schedules from DB into Redis"
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
        key = f"connector:schedule:{account_id}"
        await self._redis.hset(
            key,
            mapping={
                "interval_minutes": str(interval_minutes),
                "organization_id": organization_id,
                "provider": provider,
                "last_scheduled": datetime.utcnow().isoformat(),
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
        key = f"connector:schedule:{account_id}"
        await self._redis.delete(key)

        # Cancel running task if any
        if account_id in self._tasks:
            self._tasks[account_id].cancel()
            del self._tasks[account_id]

        logger.info(f"Cancelled sync for account {account_id}")

    async def trigger_sync(
        self,
        account: CloudAccountModel,
        sync_type: str = "on_demand",
    ) -> DiscoveryResult:
        """
        Trigger a sync for a specific account.

        Handles distributed locking to prevent concurrent syncs.
        """
        lock_key = f"connector:sync_lock:{account.id}"
        lock_acquired = await self._redis.set(lock_key, "1", nx=True, ex=300)  # 5 min lock

        if not lock_acquired:
            logger.warning(f"Sync already in progress for account {account.id}")
            return DiscoveryResult(
                errors=1,
                error_details=["Sync already in progress"],
            )

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
                result = await discovery.discover_full(
                    correlation_id=f"sync-{account.id}-{int(time.time())}"
                )
            else:
                result = await discovery.discover_incremental(
                    known_resources=known_resources,
                    correlation_id=f"sync-{account.id}-{int(time.time())}",
                )

            # Update account sync status
            await self._update_account_sync_status(account, result, sync_type)

            # Store known resources for next incremental sync
            if result.discovered > 0 or result.updated > 0:
                await self._save_known_resources(account.id, result)

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

                # Check if sync is due
                if last_sync_at:
                    last_sync_time = datetime.fromisoformat(last_sync_at)
                    next_sync_time = last_sync_time + timedelta(minutes=interval_minutes)
                    if datetime.utcnow() < next_sync_time:
                        continue  # Not due yet

                # Trigger sync
                async with self._db_session_factory() as session:
                    stmt = select(CloudAccountModel).where(CloudAccountModel.id == account_id)
                    result = await session.execute(stmt)
                    account = result.scalar_one_or_none()

                    if account and account.status == "active":
                        await self.trigger_sync(account, sync_type="incremental")
                        await self._redis.hset(key, "last_sync_at", datetime.utcnow().isoformat())

            except Exception as e:
                logger.error(f"Error checking schedule for {key}: {e}")

    async def _load_schedules(self) -> None:
        """Kept for backward compatibility — actual restore is in _restore_schedules_from_db."""
        keys = await self._redis.keys("connector:schedule:*")
        logger.info(f"Found {len(keys)} existing schedule keys in Redis")

    async def _load_known_resources(self, account_id: str) -> dict[str, dict]:
        """Load known resources from Redis for incremental sync."""
        key = f"connector:resources:{account_id}"
        data = await self._redis.get(key)
        if data:
            import json
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
                key = f"connector:resources:{account_id}"
                import json as _json
                await self._redis.set(key, _json.dumps(known), ex=3600)  # 1h TTL
                logger.debug(f"Saved {len(known)} resource hashes for account {account_id}")
        except Exception as e:
            logger.warning(f"Failed to save known resources for {account_id}: {e}")

    async def _update_account_sync_status(
        self,
        account: CloudAccountModel,
        result: DiscoveryResult,
        sync_type: str,
    ) -> None:
        """Update account sync status in database."""
        async with self._db_session_factory() as session:
            db_account = await session.get(CloudAccountModel, account.id)
            if db_account:
                db_account.last_sync_at = datetime.utcnow()
                if result.errors == 0:
                    db_account.last_successful_sync_at = datetime.utcnow()
                    db_account.consecutive_errors = 0
                    db_account.sync_status = "idle"
                    db_account.status = "active"
                    db_account.error_message = None

                    # Set resource_count to the actual count in DB (not cumulative)
                    from sqlalchemy import select, func
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
                    db_account.error_message = "; ".join(result.error_details)
                    db_account.sync_status = "error"

                    if "auth" in str(result.error_details).lower():
                        if db_account.consecutive_errors >= 3:
                            db_account.status = "auth_failed"

                await session.commit()
