"""API routes for cloud account management — tenant-isolated by organization_id.

Route handlers are intentionally thin: validate input, call the service layer,
return the result. All business logic lives in ``app/services/account_service.py``.
"""

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_redis
from app.core.auth import require_org_id
from app.core.config import get_connector_settings
from app.core.time_utils import utcnow
from app.models import CloudAccountModel
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
    CredentialRotateRequest,
    CredentialRotateResponse,
    ScanHistoryResponse,
    ScanHistoryEntry,
)
from app.services.account_service import AccountService, get_account_service
from app.services.credential_crypto import decrypt_credentials
from app.services.vault_client import VaultClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=CloudAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    request: Request,
    account_data: CloudAccountCreate,
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> CloudAccountResponse:
    """Register a new cloud account for the authenticated organization.

    For AWS accounts, a read-only IAM role is automatically provisioned in the
    customer's account using the provided access keys. The role ARN is stored
    instead of the raw keys. See ``AWSRoleSetupService`` for details.

    Credentials are envelope-encrypted with a per-org DEK before storage.
    """
    # Duplicate check — route layer responsibility (needs DB access)
    existing = await db.execute(
        select(CloudAccountModel).where(
            CloudAccountModel.organization_id == organization_id,
            CloudAccountModel.provider == account_data.provider,
            CloudAccountModel.account_id == account_data.account_id,
            CloudAccountModel.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Account {account_data.account_id} ({account_data.provider}) "
                "is already connected to your organization."
            ),
        )

    settings = get_connector_settings()
    service = get_account_service(db=db, settings=settings)

    try:
        result = await service.create_account(
            account_data=account_data,
            organization_id=organization_id,
        )
    except ValueError as e:
        # Raised by AWS role setup when credentials are invalid / missing perms
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not result.connectivity_ok and account_data.credentials:
        # Connectivity failed — surface it as a 400 so the UI can show a clear error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Could not connect to {account_data.provider} account. "
                "Please verify your credentials and permissions."
            ),
        )

    response = CloudAccountResponse(**result.account.to_dict())
    if result.warnings:
        logger.warning(
            f"Account {result.account.id} created with warnings: {result.warnings}"
        )
    return response


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
    service = get_account_service(db=db, settings=connector_settings)

    # ── 3. Clean up AWS IAM role (best-effort) ─────────────────────────────────
    if account.provider == "aws":
        credentials = await service._load_account_credentials(account, connector_settings)
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
    # We also emit a synthetic connector.sync_finished(status="cancelled") first
    # so downstream consumers can distinguish "sync never ran" from "account removed".
    correlation_id = str(uuid.uuid4())
    try:
        producer = getattr(_sync_scheduler, "_producer", None) if _sync_scheduler else None
        if producer:
            # Announce that any pending sync has been cancelled due to removal.
            try:
                await producer.emit_sync_finished(
                    account_id=account.id,
                    organization_id=organization_id,
                    provider=account.provider,
                    correlation_id=correlation_id,
                    status="cancelled",
                )
            except Exception as e:
                logger.debug(f"Failed to emit cancelled sync event: {e}")

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
    await service._emit_health_changed(
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


# ── Credential rotation ───────────────────────────────────────────────────────

@router.post(
    "/{account_id}/credentials/rotate",
    response_model=CredentialRotateResponse,
    summary="Rotate credentials for a cloud account",
    description=(
        "Replace the stored credentials for an account with new ones. "
        "For AWS, a new CloudVisorReadOnly role is provisioned if the new "
        "credentials have IAM permissions. Connectivity is validated before "
        "the old credentials are replaced."
    ),
)
async def rotate_credentials(
    account_id: str,
    body: CredentialRotateRequest,
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> CredentialRotateResponse:
    """Rotate credentials without disconnecting and reconnecting the account."""
    stmt = select(CloudAccountModel).where(
        CloudAccountModel.id == account_id,
        CloudAccountModel.organization_id == organization_id,
        CloudAccountModel.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    settings = get_connector_settings()
    service = get_account_service(db=db, settings=settings)

    try:
        rotate_result = await service.rotate_credentials(
            account=account,
            new_credentials=dict(body.credentials),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return CredentialRotateResponse(
        account_id=rotate_result.account_id,
        vault_stored=rotate_result.vault_stored,
        connectivity_ok=rotate_result.connectivity_ok,
        warnings=rotate_result.warnings,
    )


# ── Scan history ──────────────────────────────────────────────────────────────

@router.get(
    "/{account_id}/scans",
    response_model=ScanHistoryResponse,
    summary="List scan history for an account",
    description=(
        "Returns a paginated list of past sync operations for the account, "
        "newest first. Each entry includes resource counts, duration, and "
        "any error details."
    ),
)
async def list_scan_history(
    account_id: str,
    organization_id: str = Depends(require_org_id),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> ScanHistoryResponse:
    """Get paginated scan history for an account."""
    from sqlalchemy import select as sa_select, func
    from app.models import ScanHistoryModel

    # Verify account belongs to org
    stmt = sa_select(CloudAccountModel).where(
        CloudAccountModel.id == account_id,
        CloudAccountModel.organization_id == organization_id,
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    # Count
    count_stmt = sa_select(func.count()).select_from(ScanHistoryModel).where(
        ScanHistoryModel.account_id == account_id,
        ScanHistoryModel.organization_id == organization_id,
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    # Fetch page
    history_stmt = (
        sa_select(ScanHistoryModel)
        .where(
            ScanHistoryModel.account_id == account_id,
            ScanHistoryModel.organization_id == organization_id,
        )
        .order_by(ScanHistoryModel.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(history_stmt)).scalars().all()

    return ScanHistoryResponse(
        account_id=account_id,
        total=total,
        scans=[
            ScanHistoryEntry(
                id=r.id,
                account_id=r.account_id,
                sync_type=r.sync_type,
                status=r.status,
                correlation_id=r.correlation_id,
                discovered=r.discovered,
                updated=r.updated,
                deleted=r.deleted,
                errors=r.errors,
                duration_seconds=r.duration_seconds,
                started_at=r.started_at,
                finished_at=r.finished_at,
                error_details=r.error_details or [],
            )
            for r in rows
        ],
    )
