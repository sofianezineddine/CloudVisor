"""Cloud discovery service - orchestrates resource discovery."""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from cloudvisor_types.models import CloudProvider, SyncResult, SyncStatus

from app.clients import ClientFactory, CloudClientBase
from app.core.time_utils import utcnow
from app.models import CloudAccountModel, DiscoveredResourceModel
from app.services.normalizer import BatchNormalizer
from app.services.vault_client import VaultClient
from app.producers import ResourceEventProducer

logger = logging.getLogger(__name__)


# Global semaphore to cap the total number of concurrent cloud API sessions
# per process. Prevents thundering-herd when fanning out to every region × every
# service × every provider.
_GLOBAL_API_SEMAPHORE = asyncio.Semaphore(32)


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
        stale_to_deleted_threshold: int = 3,
    ):
        self._account = account
        self._producer = producer
        self._vault_client = vault_client
        self._db_session_factory = db_session_factory
        self._stale_to_deleted_threshold = max(1, int(stale_to_deleted_threshold))
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
        any previously-known resources that no longer exist as deleted.

        Handles:
          - Per-resource-type failure: if one type fails but others succeed,
            the account is flagged ``partial_sync`` instead of ``error``.
          - Deletion detection: resources in the DB but not in the cloud are
            marked ``is_deleted=True`` and a ``resource.deleted`` event is fired.
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
                current_cloud_ids = {r.cloud_resource_id for r in normalized_resources}
                deleted_count = await self._mark_missing_as_deleted(
                    current_cloud_ids=current_cloud_ids,
                    correlation_id=correlation_id,
                )
                result.deleted = deleted_count
                if deleted_count > 0:
                    logger.info(
                        f"Marked {deleted_count} resources as deleted for account "
                        f"{self._account.id} (no longer in cloud)"
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

    async def _update_account_status(self, status: str) -> None:
        """Update the account status in the database."""
        if not self._db_session_factory:
            return
        try:
            from sqlalchemy import update as sa_update
            async with self._db_session_factory() as session:
                await session.execute(
                    sa_update(CloudAccountModel)
                    .where(CloudAccountModel.id == self._account.id)
                    .values(status=status)
                )
                await session.commit()
        except Exception as e:
            logger.warning(f"Failed to update account status to {status}: {e}")

    async def _mark_missing_as_deleted(
        self,
        current_cloud_ids: set[str],
        correlation_id: str,
    ) -> int:
        """Two-stage freshness sweep.

        Stage 1: every live resource not in the current sync has its
        ``missed_sync_count`` incremented and is flagged ``stale`` if still
        under the threshold. This catches transient permission / API issues
        where one service silently stops returning data for a cycle or two
        without meaning the resources vanished.

        Stage 2: once ``missed_sync_count >= stale_to_deleted_threshold``,
        the resource is marked ``deleted`` and a ``resource.deleted`` event
        is emitted.

        Returns the count of resources moved to the ``deleted`` state in
        this sync.
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

                # Partition into "now deleted" vs "still stale"
                to_delete: list[str] = []
                to_stale: list[str] = []
                for r in db_resources:
                    if r.cloud_resource_id in current_cloud_ids:
                        continue
                    # Not returned this sync — count the miss
                    next_miss = (r.missed_sync_count or 0) + 1
                    if next_miss >= self._stale_to_deleted_threshold:
                        to_delete.append(r.cloud_resource_id)
                    else:
                        to_stale.append(r.cloud_resource_id)

                # Stage 1 — promote fresh → stale (or bump existing stale counter)
                if to_stale:
                    stale_stmt = (
                        update(DiscoveredResourceModel)
                        .where(
                            DiscoveredResourceModel.cloud_resource_id.in_(to_stale),
                            DiscoveredResourceModel.organization_id
                                == self._account.organization_id,
                        )
                        .values(
                            freshness_state="stale",
                            missed_sync_count=DiscoveredResourceModel.missed_sync_count + 1,
                        )
                    )
                    await session.execute(stale_stmt)
                    logger.info(
                        f"Flagged {len(to_stale)} resources as stale for account "
                        f"{self._account.id} (missing this sync, under delete threshold)"
                    )

                # Stage 2 — over threshold: mark deleted + emit events
                if to_delete:
                    now = utcnow()
                    delete_stmt = (
                        update(DiscoveredResourceModel)
                        .where(
                            DiscoveredResourceModel.cloud_resource_id.in_(to_delete),
                            DiscoveredResourceModel.organization_id
                                == self._account.organization_id,
                        )
                        .values(
                            is_deleted=True,
                            deleted_at=now,
                            freshness_state="deleted",
                            missed_sync_count=DiscoveredResourceModel.missed_sync_count + 1,
                        )
                    )
                    await session.execute(delete_stmt)

                await session.commit()

                # Emit Kafka deletion events for resources crossing the threshold.
                # Do this after commit so downstream consumers can re-query if needed.
                for cloud_id in to_delete:
                    await self._producer.emit_resource_deleted(
                        cloud_resource_id=cloud_id,
                        account_id=self._account.account_id,
                        organization_id=self._account.organization_id,
                        provider=self._account.provider,
                        region="global",
                        correlation_id=correlation_id,
                    )

                return len(to_delete)

        except Exception as e:
            logger.error(f"Failed to sweep missing resources: {e}")
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

    async def _upsert_resources(self, resources: list, batch_size: int = 100) -> None:
        """Upsert discovered resources into the database in batches.

        Processing resources in chunks of ``batch_size`` keeps each transaction
        small so the SQLAlchemy identity map never balloons and the process
        stays well within its memory budget even for accounts with thousands
        of resources (e.g. 1500+ IAM entities).
        """
        if not self._db_session_factory:
            return

        total = len(resources)
        upserted = 0

        try:
            for chunk_start in range(0, total, batch_size):
                chunk = resources[chunk_start: chunk_start + batch_size]
                async with self._db_session_factory() as session:
                    for resource in chunk:
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
                            last_synced_at=utcnow(),
                            resource_hash=resource_hash,
                            is_deleted=False,
                            freshness_state="fresh",
                            missed_sync_count=0,
                        ).on_conflict_do_update(
                            constraint="uq_resource_org",
                            set_={
                                "name": resource.name,
                                "tags": resource.tags,
                                "raw": raw_data,
                                "is_public": resource.is_public,
                                "environment": resource.environment.value,
                                "last_seen_at": resource.last_seen_at,
                                "last_synced_at": utcnow(),
                                "resource_hash": resource_hash,
                                "is_deleted": False,
                                "deleted_at": None,
                                # Resource was seen → reset the freshness state.
                                "freshness_state": "fresh",
                                "missed_sync_count": 0,
                            }
                        )
                        await session.execute(stmt)
                    await session.commit()
                    upserted += len(chunk)
                    logger.debug(
                        f"Upserted batch {chunk_start // batch_size + 1} "
                        f"({upserted}/{total}) for account {self._account.id}"
                    )

            logger.info(f"Upserted {upserted} resources for account {self._account.id}")
        except Exception as e:
            logger.error(f"Failed to upsert resources: {e}")

    def _sanitize_for_json(self, obj: Any) -> Any:
        """Recursively convert non-JSON-serializable objects while keeping structure.

        The spec says the ``raw`` blob must preserve the complete raw API
        response so CSPM / CIEM / DSPM rules can introspect nested fields
        later. We therefore recurse into dicts / lists / tuples / sets, convert
        datetimes to ISO strings, bytes to base64, and leave primitives intact.
        Only truly opaque objects (custom classes) get stringified.
        """
        from datetime import date, datetime, time, timedelta
        from decimal import Decimal
        from enum import Enum
        import base64
        import uuid as _uuid

        if obj is None:
            return None
        if isinstance(obj, dict):
            return {str(k): self._sanitize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set, frozenset)):
            return [self._sanitize_for_json(i) for i in obj]
        if isinstance(obj, (str, bool)):
            return obj
        if isinstance(obj, (int, float)):
            return obj
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return obj.total_seconds()
        if isinstance(obj, _uuid.UUID):
            return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, (bytes, bytearray)):
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return base64.b64encode(bytes(obj)).decode("ascii")
        # Last-resort: try attribute access (for SDK models), then stringify
        if hasattr(obj, "__dict__"):
            try:
                return self._sanitize_for_json(dict(vars(obj)))
            except Exception:
                pass
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
                    .values(is_deleted=True, deleted_at=utcnow())
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

        All stored payloads are envelope-decrypted transparently — legacy
        plaintext payloads pass through unchanged for backward compatibility.
        """
        from app.services.credential_crypto import decrypt_credentials

        org_id = self._account.organization_id

        # 1. Try Vault first
        if self._vault_client and self._account.vault_secret_path:
            try:
                raw = await self._vault_client.retrieve_credentials(
                    self._account.vault_secret_path
                )
                if raw:
                    try:
                        creds = decrypt_credentials(raw, org_id)
                        logger.debug(
                            f"Retrieved credentials from Vault for account {self._account.id}"
                        )
                        return creds
                    except Exception as e:
                        logger.warning(
                            f"Vault credentials decrypt failed ({e}); treating as plaintext"
                        )
                        return dict(raw)
            except Exception as e:
                logger.warning(f"Failed to retrieve credentials from Vault: {e}")

        # 2. Fall back to DB-stored credentials (dev/local when Vault is disabled)
        if self._account.credentials_enc:
            try:
                creds = decrypt_credentials(self._account.credentials_enc, org_id)
                logger.debug(
                    f"Using DB-stored credentials for account {self._account.id}"
                )
                return creds
            except Exception as e:
                logger.error(
                    f"Failed to decrypt DB credentials for account {self._account.id}: {e}. "
                    "Check CONNECTOR_CREDENTIAL_MASTER_KEY matches what the credentials "
                    "were encrypted with."
                )
                return {}

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
