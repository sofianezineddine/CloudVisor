"""Cloud discovery service - orchestrates resource discovery."""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from cloudvisor_types.models import CloudProvider, SyncResult, SyncStatus

from app.clients import ClientFactory, CloudClientBase
from app.models import CloudAccountModel, DiscoveredResourceModel
from app.services.normalizer import BatchNormalizer
from app.services.vault_client import VaultClient
from app.producers import ResourceEventProducer

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Result of a discovery operation."""

    discovered: int = 0
    updated: int = 0
    deleted: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    error_details: list[str] = field(default_factory=list)


class CloudDiscoveryService:
    """Service for discovering cloud resources across providers."""

    def __init__(
        self,
        account: CloudAccountModel,
        producer: ResourceEventProducer,
        vault_client: VaultClient | None = None,
        db_session_factory: Any | None = None,
    ):
        self._account = account
        self._producer = producer
        self._vault_client = vault_client
        self._db_session_factory = db_session_factory
        self._client: CloudClientBase | None = None
        self._normalizer = BatchNormalizer(account.organization_id)

    async def connect(self) -> bool:
        """Connect to the cloud provider."""
        credentials = await self._get_credentials()
        # Inject the cloud account ID into credentials so each provider client
        # can find it regardless of what key name was used during onboarding.
        if self._account.account_id:
            account_id = self._account.account_id
            provider = self._account.provider
            if provider == "oci":
                credentials.setdefault("tenancy_ocid", account_id)
                credentials.setdefault("account_id", account_id)
            elif provider == "azure":
                credentials.setdefault("subscription_id", account_id)
                credentials.setdefault("account_id", account_id)
            elif provider == "gcp":
                credentials.setdefault("project_id", account_id)
                credentials.setdefault("account_id", account_id)
            elif provider == "aws":
                credentials.setdefault("account_id", account_id)

        self._client = ClientFactory.create_client(
            provider=self._account.provider,
            credentials=credentials,
        )
        return await self._client.connect()

    async def disconnect(self) -> None:
        """Disconnect from the cloud provider."""
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def discover_full(self, correlation_id: str) -> DiscoveryResult:
        """
        Full resource discovery — upserts all current resources AND marks
        any previously-known resources that no longer exist in AWS as deleted.
        This ensures deleted resources disappear from the UI on the next sync.
        """
        start_time = time.time()
        result = DiscoveryResult()

        await self._producer.emit_sync_started(
            account_id=self._account.id,
            organization_id=self._account.organization_id,
            provider=self._account.provider,
            correlation_id=correlation_id,
        )

        try:
            if not self._client:
                await self.connect()

            raw_resources = await self._client.list_resources(region=self._account.region)

            normalized_resources = self._normalizer.normalize_batch(
                raw_resources,
                self._account.provider,
                self._account.account_id,
            )

            # Emit Kafka events for new/updated resources
            for resource in normalized_resources:
                await self._producer.emit_resource_discovered(
                    resource=resource,
                    correlation_id=correlation_id,
                )
                result.discovered += 1

            # Upsert all current resources to DB
            if self._db_session_factory:
                await self._upsert_resources(normalized_resources)

                # ── Deletion detection ────────────────────────────────────────
                # Find resources in DB that were NOT returned by AWS this sync.
                # These have been deleted in the cloud account.
                current_cloud_ids = {r.cloud_resource_id for r in normalized_resources}
                deleted_count = await self._mark_missing_as_deleted(
                    current_cloud_ids=current_cloud_ids,
                    correlation_id=correlation_id,
                )
                result.deleted = deleted_count
                if deleted_count > 0:
                    logger.info(
                        f"Marked {deleted_count} resources as deleted for account "
                        f"{self._account.id} (no longer in AWS)"
                    )

        except Exception as e:
            result.errors += 1
            result.error_details.append(str(e))
            logger.error(f"Full discovery failed for account {self._account.id}: {e}")

        result.duration_seconds = time.time() - start_time

        await self._producer.emit_sync_finished(
            account_id=self._account.id,
            organization_id=self._account.organization_id,
            provider=self._account.provider,
            correlation_id=correlation_id,
            discovered=result.discovered,
            updated=result.updated,
            deleted=result.deleted,
            errors=result.errors,
            duration_seconds=result.duration_seconds,
        )

        return result

    async def _mark_missing_as_deleted(
        self,
        current_cloud_ids: set[str],
        correlation_id: str,
    ) -> int:
        """
        Mark resources in the DB as deleted if they were not returned by the
        current sync. This handles resources deleted directly in the cloud console.
        Returns the number of resources marked as deleted.
        """
        if not self._db_session_factory:
            return 0

        from sqlalchemy import select, update

        try:
            async with self._db_session_factory() as session:
                # Find all non-deleted resources for this account in the DB
                stmt = select(DiscoveredResourceModel).where(
                    DiscoveredResourceModel.account_id == self._account.account_id,
                    DiscoveredResourceModel.organization_id == self._account.organization_id,
                    DiscoveredResourceModel.is_deleted == False,  # noqa: E712
                )
                result = await session.execute(stmt)
                db_resources = result.scalars().all()

                # Find which ones are no longer in AWS
                deleted_ids = [
                    r.cloud_resource_id
                    for r in db_resources
                    if r.cloud_resource_id not in current_cloud_ids
                ]

                if not deleted_ids:
                    return 0

                # Mark them as deleted
                now = datetime.utcnow()
                update_stmt = (
                    update(DiscoveredResourceModel)
                    .where(
                        DiscoveredResourceModel.cloud_resource_id.in_(deleted_ids),
                        DiscoveredResourceModel.organization_id == self._account.organization_id,
                    )
                    .values(is_deleted=True, deleted_at=now)
                )
                await session.execute(update_stmt)
                await session.commit()

                # Emit Kafka deletion events
                for cloud_id in deleted_ids:
                    await self._producer.emit_resource_deleted(
                        cloud_resource_id=cloud_id,
                        account_id=self._account.account_id,
                        organization_id=self._account.organization_id,
                        provider=self._account.provider,
                        region="global",
                        correlation_id=correlation_id,
                    )

                return len(deleted_ids)

        except Exception as e:
            logger.error(f"Failed to mark deleted resources: {e}")
            return 0

    async def discover_incremental(
        self,
        known_resources: dict[str, dict[str, Any]],
        correlation_id: str,
    ) -> DiscoveryResult:
        """Perform incremental discovery (delta sync)."""
        start_time = time.time()
        result = DiscoveryResult()

        try:
            if not self._client:
                await self.connect()

            raw_resources = await self._client.list_resources(region=self._account.region)

            normalized_resources = self._normalizer.normalize_batch(
                raw_resources,
                self._account.provider,
                self._account.account_id,
            )

            current_resource_ids = set()

            for resource in normalized_resources:
                current_resource_ids.add(resource.cloud_resource_id)

                resource_hash = self._compute_hash(resource)
                known = known_resources.get(resource.cloud_resource_id)

                if not known:
                    await self._producer.emit_resource_discovered(
                        resource=resource,
                        correlation_id=correlation_id,
                    )
                    result.discovered += 1
                elif known.get("resource_hash") != resource_hash:
                    await self._producer.emit_resource_updated(
                        resource=resource,
                        correlation_id=correlation_id,
                    )
                    result.updated += 1

            # Persist all to DB (upsert)
            if normalized_resources and self._db_session_factory:
                await self._upsert_resources(normalized_resources)

            # Handle deletions
            known_resource_ids = set(known_resources.keys())
            deleted_ids = known_resource_ids - current_resource_ids

            for deleted_id in deleted_ids:
                await self._producer.emit_resource_deleted(
                    cloud_resource_id=deleted_id,
                    account_id=self._account.account_id,
                    organization_id=self._account.organization_id,
                    provider=self._account.provider,
                    region=known_resources[deleted_id].get("region", "global"),
                    correlation_id=correlation_id,
                )
                result.deleted += 1

            if deleted_ids and self._db_session_factory:
                await self._mark_deleted(list(deleted_ids))

        except Exception as e:
            result.errors += 1
            result.error_details.append(str(e))
            logger.error(f"Incremental discovery failed for account {self._account.id}: {e}")

        result.duration_seconds = time.time() - start_time
        return result

    async def _upsert_resources(self, resources: list) -> None:
        """Upsert discovered resources into the database."""
        if not self._db_session_factory:
            return
        try:
            async with self._db_session_factory() as session:
                for resource in resources:
                    resource_hash = self._compute_hash(resource)

                    # Sanitize raw field — strip non-serializable objects (datetimes, etc.)
                    raw_data = self._sanitize_for_json(resource.raw)

                    stmt = pg_insert(DiscoveredResourceModel).values(
                        id=resource.id,
                        cloud_resource_id=resource.cloud_resource_id,
                        provider=resource.provider.value,
                        account_id=resource.account_id,
                        organization_id=resource.organization_id,
                        region=resource.region,
                        resource_type=resource.resource_type,
                        name=resource.name,
                        tags=resource.tags,
                        raw=raw_data,
                        is_public=resource.is_public,
                        environment=resource.environment.value,
                        first_seen_at=resource.first_seen_at,
                        last_seen_at=resource.last_seen_at,
                        last_synced_at=datetime.utcnow(),
                        resource_hash=resource_hash,
                        is_deleted=False,
                    ).on_conflict_do_update(
                        constraint="uq_resource_org",
                        set_={
                            "name": resource.name,
                            "tags": resource.tags,
                            "raw": raw_data,
                            "is_public": resource.is_public,
                            "environment": resource.environment.value,
                            "last_seen_at": resource.last_seen_at,
                            "last_synced_at": datetime.utcnow(),
                            "resource_hash": resource_hash,
                            "is_deleted": False,
                            "deleted_at": None,
                        }
                    )
                    await session.execute(stmt)
                await session.commit()
                logger.info(f"Upserted {len(resources)} resources for account {self._account.id}")
        except Exception as e:
            logger.error(f"Failed to upsert resources: {e}")

    def _sanitize_for_json(self, obj: Any) -> Any:
        """Recursively convert non-JSON-serializable objects to strings."""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(i) for i in obj]
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, (str, int, float, bool)):
            return obj
        # Fallback: convert anything else to string
        return str(obj)

    async def _mark_deleted(self, cloud_resource_ids: list[str]) -> None:
        """Mark resources as deleted in the database."""
        if not self._db_session_factory:
            return
        try:
            from sqlalchemy import update
            async with self._db_session_factory() as session:
                stmt = (
                    update(DiscoveredResourceModel)
                    .where(
                        DiscoveredResourceModel.cloud_resource_id.in_(cloud_resource_ids),
                        DiscoveredResourceModel.organization_id == self._account.organization_id,
                    )
                    .values(is_deleted=True, deleted_at=datetime.utcnow())
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to mark resources as deleted: {e}")

    def _compute_hash(self, resource: Any) -> str:
        content = json.dumps({
            "cloud_resource_id": resource.cloud_resource_id,
            "resource_type": resource.resource_type,
            "name": resource.name,
            "region": resource.region,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    async def _get_credentials(self) -> dict[str, Any]:
        """Get credentials for the cloud account.

        Priority:
        1. Vault (production) — if vault_client is available and vault_secret_path is set
        2. credentials_enc column (dev/local) — direct DB storage fallback
        3. Empty dict — no credentials available (sync will fail gracefully)
        """
        # 1. Try Vault first
        if self._vault_client and self._account.vault_secret_path:
            try:
                credentials = await self._vault_client.retrieve_credentials(
                    self._account.vault_secret_path
                )
                if credentials:
                    logger.debug(f"Retrieved credentials from Vault for account {self._account.id}")
                    return credentials
            except Exception as e:
                logger.warning(f"Failed to retrieve credentials from Vault: {e}")

        # 2. Fall back to DB-stored credentials (dev/local when Vault is disabled)
        if self._account.credentials_enc:
            logger.debug(
                f"Using DB-stored credentials for account {self._account.id} "
                "(Vault not available or not configured)"
            )
            return dict(self._account.credentials_enc)

        logger.warning(
            f"No credentials available for account {self._account.id} — "
            "discovery will fail. Check Vault config or re-connect the account."
        )
        return {}

    def get_account_id(self) -> str:
        """Get the cloud account ID."""
        if self._client:
            return self._client.get_account_id()
        return self._account.account_id


class DiscoveryScheduler:
    """Schedules and manages discovery jobs (simple Redis-based)."""

    def __init__(self, redis_client: Any):
        self._redis = redis_client

    async def schedule_sync(self, account_id: str, interval_minutes: int) -> None:
        key = f"connector:schedule:{account_id}"
        await self._redis.set(key, interval_minutes)

    async def cancel_sync(self, account_id: str) -> None:
        key = f"connector:schedule:{account_id}"
        await self._redis.delete(key)

    async def get_scheduled_accounts(self) -> list[str]:
        keys = await self._redis.keys("connector:schedule:*")
        return [k.split(":")[-1] for k in keys]
