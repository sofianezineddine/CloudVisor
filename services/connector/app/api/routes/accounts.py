"""API routes for cloud account management — tenant-isolated by organization_id."""

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_redis
from app.core.auth import require_org_id
from app.core.time_utils import utcnow
from app.schemas import (
    CloudAccountCreate,
    CloudAccountUpdate,
    CloudAccountResponse,
    CloudAccountListResponse,
    CloudAccountHealthResponse,
    SyncTriggerRequest,
    SyncTriggerResponse,
    OnboardingResponse,
    ErrorResponse,
)
from app.models import CloudAccountModel
from app.services.credential_crypto import (
    decrypt_credentials,
    encrypt_credentials,
)
from app.services.vault_client import VaultClient
from app.core.config import get_connector_settings

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/accounts", tags=["accounts"])


async def _load_account_credentials(
    account: CloudAccountModel,
    connector_settings: Any,
) -> dict[str, Any]:
    """Load and decrypt credentials for an account.

    Tries Vault first, then falls back to ``credentials_enc``. Handles both
    the new envelope-encrypted payload and legacy plaintext transparently.
    """
    # Try Vault
    if account.vault_secret_path and connector_settings.vault_enabled:
        try:
            vault = VaultClient(
                vault_url=connector_settings.vault_url,
                vault_token=connector_settings.vault_token,
                mount_point=connector_settings.vault_mount_point,
            )
            if await vault.initialize():
                raw = await vault.retrieve_credentials(account.vault_secret_path)
                if raw:
                    try:
                        return decrypt_credentials(raw, account.organization_id)
                    except Exception as e:
                        logger.warning(
                            f"Credential decryption failed for {account.id}: {e}. "
                            "Treating Vault payload as plaintext (legacy)."
                        )
                        return dict(raw)
        except Exception as e:
            logger.warning(f"Could not retrieve Vault credentials for {account.id}: {e}")

    # Fall back to DB
    if account.credentials_enc:
        try:
            return decrypt_credentials(account.credentials_enc, account.organization_id)
        except Exception as e:
            logger.error(
                f"Failed to decrypt DB credentials for {account.id}: {e}. "
                "Check CONNECTOR_CREDENTIAL_MASTER_KEY."
            )
            return {}

    return {}


async def _emit_health_change_if_needed(
    account: CloudAccountModel,
    previous_status: str,
    new_status: str,
    error_message: str | None = None,
) -> None:
    """Emit connector.health_changed when status transitions."""
    if previous_status == new_status:
        return
    try:
        from app.core.dependencies import _sync_scheduler
        producer = getattr(_sync_scheduler, "_producer", None) if _sync_scheduler else None
        if producer is None:
            return
        await producer.emit_health_changed(
            account_id=account.id,
            organization_id=account.organization_id,
            provider=account.provider,
            previous_status=previous_status,
            new_status=new_status,
            error_message=error_message,
            resource_count=account.resource_count,
        )
        logger.info(
            f"Emitted connector.health_changed: {account.id} "
            f"{previous_status} → {new_status}"
        )
    except Exception as e:
        # Never block on telemetry
        logger.warning(f"Failed to emit health_changed for {account.id}: {e}")


@router.post("", response_model=CloudAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    request: Request,
    account_data: CloudAccountCreate,
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> CloudAccountResponse:
    """Register a new cloud account for the authenticated organization."""
    # Check for duplicate (same provider + cloud account_id within this org)
    existing = await db.execute(
        select(CloudAccountModel).where(
            CloudAccountModel.organization_id == organization_id,
            CloudAccountModel.provider == account_data.provider,
            CloudAccountModel.account_id == account_data.account_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account {account_data.account_id} ({account_data.provider}) is already connected to your organization.",
        )

    account = CloudAccountModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,          # ← from JWT, not random
        provider=account_data.provider,
        name=account_data.name,
        account_id=account_data.account_id,
        region=account_data.region,
        status="pending",
        sync_status="idle",
        polling_interval_minutes=account_data.polling_interval_minutes,
    )

    # For AWS: automatically create a read-only role using the provided credentials,
    # then store the role ARN instead of the raw access keys.
    credentials_to_store = dict(account_data.credentials) if account_data.credentials else {}

    if account_data.provider == "aws" and credentials_to_store.get("access_key") and credentials_to_store.get("secret_key"):
        try:
            from app.services.aws_role_setup import AWSRoleSetupService
            setup = AWSRoleSetupService(
                access_key=credentials_to_store["access_key"],
                secret_key=credentials_to_store["secret_key"],
            )
            role_info = await setup.setup_role()

            # Store role ARN + external_id + original keys (needed to re-assume the role)
            # The original keys are kept so we can re-assume the role on each sync.
            credentials_to_store["role_arn"] = role_info["role_arn"]
            credentials_to_store["external_id"] = role_info["external_id"]

            # Update account_id with the verified AWS account ID
            account.account_id = role_info["account_id"]

            logger.info(
                f"Auto-provisioned CloudVisorReadOnly role in AWS account "
                f"{role_info['account_id']}: {role_info['role_arn']}"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            logger.warning(f"Role auto-setup failed, falling back to direct key usage: {e}")
            # Non-fatal: fall back to using the access key directly

    # Store credentials in Vault (preferred) or directly in DB (dev/fallback).
    # In BOTH paths, the credentials are envelope-encrypted with a per-org DEK
    # derived from CONNECTOR_CREDENTIAL_MASTER_KEY before persistence (spec §8).
    connector_settings = get_connector_settings()
    if credentials_to_store:
        encrypted_payload = encrypt_credentials(credentials_to_store, organization_id)
        vault_stored = False

        # Try Vault only if it's enabled
        if connector_settings.vault_enabled:
            try:
                vault = VaultClient(
                    vault_url=connector_settings.vault_url,
                    vault_token=connector_settings.vault_token,
                    mount_point=connector_settings.vault_mount_point,
                )
                initialized = await vault.initialize()
                if initialized:
                    vault_path = await vault.store_credentials(
                        account_id=account.id,
                        organization_id=organization_id,
                        provider=account.provider,
                        credentials=encrypted_payload,
                    )
                    account.vault_secret_path = vault_path
                    vault_stored = True
                    logger.info(f"Encrypted credentials stored in Vault for account {account.id}")
                else:
                    logger.warning("Vault unavailable/sealed — falling back to DB credential storage")
            except Exception as e:
                logger.warning(
                    f"Vault storage failed ({type(e).__name__}: {str(e)[:120]}) "
                    "— falling back to DB credential storage"
                )

        if not vault_stored:
            # Vault disabled, sealed, or unreachable — store encrypted blob in DB.
            account.credentials_enc = encrypted_payload
            logger.info(f"Encrypted credentials stored in DB for account {account.id}")

    # ── Validate connectivity before marking active (spec requirement) ─────────
    connectivity_ok = False
    if credentials_to_store:
        try:
            from app.clients import ClientFactory
            test_client = ClientFactory.create_client(
                provider=account_data.provider,
                credentials=credentials_to_store,
            )
            connectivity_ok = await test_client.connect()
            try:
                await test_client.disconnect()
            except Exception:
                pass
            if not connectivity_ok:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not connect to {account_data.provider} account. "
                           "Please verify your credentials and permissions.",
                )
            logger.info(f"Connectivity validated for {account_data.provider} account {account_data.account_id}")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Connectivity check failed: {e} — proceeding with pending status")
            connectivity_ok = False

    previous_status = account.status
    account.status = "active" if connectivity_ok else "pending"

    db.add(account)
    await db.commit()
    await db.refresh(account)

    # Emit connector.health_changed for the initial status transition
    await _emit_health_change_if_needed(
        account=account,
        previous_status=previous_status,
        new_status=account.status,
    )

    # Schedule + trigger initial sync
    from app.core.dependencies import _sync_scheduler, get_realtime_manager
    if _sync_scheduler is not None:
        await _sync_scheduler.schedule_account(
            account_id=account.id,
            organization_id=organization_id,
            provider=account.provider,
            interval_minutes=account.polling_interval_minutes,
        )
        asyncio.create_task(_sync_scheduler.trigger_sync(account, sync_type="full"))

    # Start real-time consumers for this account
    realtime_manager = get_realtime_manager()
    if realtime_manager is not None:
        started = await realtime_manager.add_account_consumers(
            account_id=account.id,
            organization_id=organization_id,
            provider=account.provider,
            cloud_account_id=account.account_id,
            credentials=credentials_to_store,
            region=account.region,
        )
        if started:
            logger.info(f"Started {started} real-time consumer(s) for account {account.id}")

    return CloudAccountResponse(**account.to_dict())


@router.get("", response_model=CloudAccountListResponse)
async def list_accounts(
    organization_id: str = Depends(require_org_id),
    include_deleted: bool = False,
    db: AsyncSession = Depends(get_db),
) -> CloudAccountListResponse:
    """List cloud accounts belonging to the authenticated organization only.

    Soft-deleted accounts are excluded by default. Pass ``include_deleted=true``
    to see them (audit / compliance use).
    """
    stmt = select(CloudAccountModel).where(
        CloudAccountModel.organization_id == organization_id
    )
    if not include_deleted:
        stmt = stmt.where(CloudAccountModel.deleted_at.is_(None))
    stmt = stmt.order_by(CloudAccountModel.created_at.desc())
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    return CloudAccountListResponse(
        accounts=[CloudAccountResponse(**a.to_dict()) for a in accounts],
        total=len(accounts),
    )


@router.get("/{account_id}", response_model=CloudAccountResponse)
async def get_account(
    account_id: str,
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> CloudAccountResponse:
    """Get a cloud account — must belong to the authenticated organization."""
    stmt = select(CloudAccountModel).where(
        CloudAccountModel.id == account_id,
        CloudAccountModel.organization_id == organization_id,
        CloudAccountModel.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    return CloudAccountResponse(**account.to_dict())


@router.patch("/{account_id}", response_model=CloudAccountResponse)
async def update_account(
    account_id: str,
    account_data: CloudAccountUpdate,
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> CloudAccountResponse:
    """Update cloud account config — must belong to the authenticated organization."""
    stmt = select(CloudAccountModel).where(
        CloudAccountModel.id == account_id,
        CloudAccountModel.organization_id == organization_id,
        CloudAccountModel.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    if account_data.name is not None:
        account.name = account_data.name
    if account_data.region is not None:
        account.region = account_data.region
    if account_data.polling_interval_minutes is not None:
        # Re-validate against allowed options
        allowed = get_connector_settings().polling_interval_options
        if account_data.polling_interval_minutes not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"polling_interval_minutes must be one of {allowed}",
            )
        account.polling_interval_minutes = account_data.polling_interval_minutes
        # Reschedule with new interval
        from app.core.dependencies import _sync_scheduler
        if _sync_scheduler is not None:
            await _sync_scheduler.schedule_account(
                account_id=account.id,
                organization_id=organization_id,
                provider=account.provider,
                interval_minutes=account.polling_interval_minutes,
            )

    account.updated_at = utcnow()
    await db.commit()
    await db.refresh(account)

    return CloudAccountResponse(**account.to_dict())


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    hard: bool = False,
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a cloud account — must belong to the authenticated organization.

    Default is SOFT delete (sets ``deleted_at``, wipes credentials, stops
    polling, emits ``resource.deleted`` events for all resources). The row
    stays for 365+ days to satisfy audit retention (spec §3.3).

    Pass ``hard=true`` to physically delete the row. Only use this for
    data-erasure / GDPR right-to-be-forgotten.
    """
    stmt = select(CloudAccountModel).where(
        CloudAccountModel.id == account_id,
        CloudAccountModel.organization_id == organization_id,
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    previous_status = account.status

    # ── 1. Cancel scheduled sync ───────────────────────────────────────────────
    from app.core.dependencies import _sync_scheduler
    if _sync_scheduler is not None:
        try:
            await _sync_scheduler.cancel_account(account_id)
        except Exception as e:
            logger.warning(f"Failed to cancel sync schedule for {account_id}: {e}")

    # ── 2. Stop real-time consumers ────────────────────────────────────────────
    from app.core.dependencies import get_realtime_manager
    realtime_manager = get_realtime_manager()
    if realtime_manager is not None:
        try:
            await realtime_manager.remove_account_consumers(account_id)
        except Exception as e:
            logger.warning(f"Failed to stop real-time consumers for {account_id}: {e}")

    connector_settings = get_connector_settings()

    # ── 3. Clean up AWS IAM role (best-effort) ─────────────────────────────────
    if account.provider == "aws":
        credentials = await _load_account_credentials(account, connector_settings)
        if credentials.get("access_key") and credentials.get("secret_key"):
            try:
                from app.services.aws_role_setup import AWSRoleSetupService
                deleted = await AWSRoleSetupService.delete_role(
                    access_key=credentials["access_key"],
                    secret_key=credentials["secret_key"],
                )
                if deleted:
                    logger.info(f"Cleaned up CloudVisorReadOnly role for account {account_id}")
            except Exception as e:
                logger.warning(f"AWS role cleanup failed (non-fatal): {e}")

    # ── 4. Delete credentials from Vault ──────────────────────────────────────
    if account.vault_secret_path:
        if connector_settings.vault_enabled:
            try:
                vault = VaultClient(
                    vault_url=connector_settings.vault_url,
                    vault_token=connector_settings.vault_token,
                    mount_point=connector_settings.vault_mount_point,
                )
                if await vault.initialize():
                    await vault.delete_credentials(account.vault_secret_path)
                    logger.info(f"Deleted Vault credentials for account {account_id}")
            except Exception as e:
                logger.warning(f"Failed to delete Vault credentials for {account_id}: {e}")

    # ── 5. Emit resource.deleted Kafka events for all account resources ────────
    # Spec: "Remove a cloud account (stops polling, emits deleted events)"
    try:
        producer = getattr(_sync_scheduler, "_producer", None) if _sync_scheduler else None
        if producer:
            from sqlalchemy import select as sa_select
            from app.models import DiscoveredResourceModel
            stmt_resources = sa_select(
                DiscoveredResourceModel.cloud_resource_id,
                DiscoveredResourceModel.region,
            ).where(
                DiscoveredResourceModel.account_id == account.account_id,
                DiscoveredResourceModel.organization_id == organization_id,
                DiscoveredResourceModel.is_deleted == False,  # noqa: E712
            )
            resource_rows = await db.execute(stmt_resources)
            rows = resource_rows.all()
            correlation_id = str(uuid.uuid4())
            emit_tasks = [
                producer.emit_resource_deleted(
                    cloud_resource_id=row.cloud_resource_id,
                    account_id=account.account_id,
                    organization_id=organization_id,
                    provider=account.provider,
                    region=row.region,
                    correlation_id=correlation_id,
                )
                for row in rows
            ]
            if emit_tasks:
                await asyncio.gather(*emit_tasks, return_exceptions=True)
                logger.info(
                    f"Emitted {len(emit_tasks)} resource.deleted events "
                    f"for account {account_id}"
                )
    except Exception as e:
        logger.warning(f"Failed to emit resource.deleted events for {account_id}: {e}")

    # ── 6. Soft or hard delete ────────────────────────────────────────────────
    if hard:
        await db.delete(account)
        await db.commit()
        logger.info(f"HARD-deleted cloud account {account_id} for org {organization_id}")
    else:
        account.deleted_at = utcnow()
        account.status = "paused"
        account.sync_status = "idle"
        # Wipe credentials on soft-delete — audit rows don't need secrets
        account.credentials_enc = None
        account.vault_secret_path = None
        await db.commit()
        logger.info(f"Soft-deleted cloud account {account_id} for org {organization_id}")

    # ── 7. Emit health_changed ────────────────────────────────────────────────
    await _emit_health_change_if_needed(
        account=account,
        previous_status=previous_status,
        new_status="paused" if not hard else "deleted",
    )


@router.post("/{account_id}/sync", response_model=SyncTriggerResponse)
async def trigger_sync(
    account_id: str,
    sync_data: SyncTriggerRequest | None = None,
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> SyncTriggerResponse:
    """Trigger an immediate sync — account must belong to the authenticated organization."""
    stmt = select(CloudAccountModel).where(
        CloudAccountModel.id == account_id,
        CloudAccountModel.organization_id == organization_id,
        CloudAccountModel.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    correlation_id = (
        sync_data.correlation_id if sync_data and sync_data.correlation_id
        else str(uuid.uuid4())
    )

    from app.core.dependencies import _sync_scheduler
    if _sync_scheduler is not None:
        asyncio.create_task(_sync_scheduler.trigger_sync(account, sync_type="full"))

    return SyncTriggerResponse(
        account_id=account_id,
        correlation_id=correlation_id,
        status="triggered",
        message="Sync triggered successfully",
    )


@router.get("/{account_id}/sync/status")
async def get_sync_status(
    account_id: str,
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the current sync progress for an account.

    Returns the in-flight or most-recent sync's progress — used by the UI's
    "Run scan" button (Page 1 Dashboard) to show live progress in a Flashbar.
    """
    stmt = select(CloudAccountModel).where(
        CloudAccountModel.id == account_id,
        CloudAccountModel.organization_id == organization_id,
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    from app.core.dependencies import _sync_scheduler
    progress = None
    if _sync_scheduler is not None:
        progress = await _sync_scheduler.get_sync_progress(account_id)

    # Build a response that's always populated even when no sync has run yet
    return {
        "account_id": account_id,
        "provider": account.provider,
        "account_status": account.status,
        "sync_status": account.sync_status,
        "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
        "last_successful_sync_at": (
            account.last_successful_sync_at.isoformat()
            if account.last_successful_sync_at else None
        ),
        "resource_count": account.resource_count,
        "consecutive_errors": account.consecutive_errors,
        "current_sync": progress,
    }


@router.get("/{account_id}/health", response_model=CloudAccountHealthResponse)
async def get_account_health(
    account_id: str,
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> CloudAccountHealthResponse:
    """Get account health — must belong to the authenticated organization."""
    stmt = select(CloudAccountModel).where(
        CloudAccountModel.id == account_id,
        CloudAccountModel.organization_id == organization_id,
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    error_rate = 0.0
    if account.consecutive_errors > 0:
        total = account.consecutive_errors + account.resource_count
        if total > 0:
            error_rate = account.consecutive_errors / total

    return CloudAccountHealthResponse(
        id=account.id,
        status=account.status,
        sync_status=account.sync_status,
        last_sync_at=account.last_sync_at,
        last_successful_sync_at=account.last_successful_sync_at,
        consecutive_errors=account.consecutive_errors,
        error_message=account.error_message,
        resource_count=account.resource_count,
        error_rate=error_rate,
    )


@router.get("/onboarding/aws/template", response_model=OnboardingResponse, deprecated=True)
async def get_aws_template() -> OnboardingResponse:
    """Deprecated: use ``/internal/onboarding/aws/template`` instead."""
    from app.services.onboarding_templates import AWS_CLOUDFORMATION_TEMPLATE
    return OnboardingResponse(
        provider="aws",
        instructions="Deprecated endpoint. Use /internal/onboarding/aws/template instead.",
        template=AWS_CLOUDFORMATION_TEMPLATE,
    )
