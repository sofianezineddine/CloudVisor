"""API routes for cloud account management — tenant-isolated by organization_id."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_redis
from app.core.auth import require_org_id
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
from app.services.vault_client import VaultClient
from app.core.config import get_connector_settings

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/accounts", tags=["accounts"])


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

    # Store credentials in Vault (preferred) or directly in DB (dev/fallback)
    connector_settings = get_connector_settings()
    if credentials_to_store:
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
                        credentials=credentials_to_store,
                    )
                    account.vault_secret_path = vault_path
                    vault_stored = True
                    logger.info(f"Credentials stored in Vault for account {account.id}")
                else:
                    logger.warning("Vault unavailable/sealed — falling back to DB credential storage")
            except Exception as e:
                logger.warning(
                    f"Vault storage failed ({type(e).__name__}: {str(e)[:120]}) "
                    "— falling back to DB credential storage"
                )

        if not vault_stored:
            # Vault disabled, sealed, or unreachable — store directly in DB.
            # Safe for dev/local. In production, fix Vault or keep it enabled.
            account.credentials_enc = credentials_to_store
            logger.info(f"Credentials stored in DB for account {account.id}")

    account.status = "active"

    db.add(account)
    await db.commit()
    await db.refresh(account)

    # Schedule + trigger initial sync
    from app.core.dependencies import _sync_scheduler
    if _sync_scheduler is not None:
        await _sync_scheduler.schedule_account(
            account_id=account.id,
            organization_id=organization_id,
            provider=account.provider,
            interval_minutes=account.polling_interval_minutes,
        )
        asyncio.create_task(_sync_scheduler.trigger_sync(account, sync_type="full"))

    return CloudAccountResponse(**account.to_dict())


@router.get("", response_model=CloudAccountListResponse)
async def list_accounts(
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> CloudAccountListResponse:
    """List cloud accounts belonging to the authenticated organization only."""
    stmt = select(CloudAccountModel).where(
        CloudAccountModel.organization_id == organization_id
    ).order_by(CloudAccountModel.created_at.desc())
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
        CloudAccountModel.organization_id == organization_id,   # ← tenant check
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
        account.polling_interval_minutes = account_data.polling_interval_minutes

    account.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(account)

    return CloudAccountResponse(**account.to_dict())


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    organization_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a cloud account — must belong to the authenticated organization."""
    stmt = select(CloudAccountModel).where(
        CloudAccountModel.id == account_id,
        CloudAccountModel.organization_id == organization_id,
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    await db.delete(account)
    await db.commit()


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


@router.get("/onboarding/aws/template", response_model=OnboardingResponse)
async def get_aws_template() -> OnboardingResponse:
    template = """AWSTemplateFormatVersion: '2010-09-09'
Description: CloudVisor Read-Only Access Role
Resources:
  CloudVisorReadOnlyRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: CloudVisorReadOnly
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              AWS: arn:aws:iam::YOUR_CLOUDVISOR_ACCOUNT_ID:root
            Action: sts:AssumeRole
            Condition:
              StringEquals:
                sts:ExternalId: YOUR_EXTERNAL_ID
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/ReadOnlyAccess
Outputs:
  RoleArn:
    Value: !GetAtt CloudVisorReadOnlyRole.Arn
"""
    return OnboardingResponse(
        provider="aws",
        instructions="1. Replace YOUR_CLOUDVISOR_ACCOUNT_ID\n2. Replace YOUR_EXTERNAL_ID\n3. Create stack in CloudFormation\n4. Copy the Role ARN to CloudVisor",
        template=template,
    )


@router.get("/onboarding/azure/instructions", response_model=OnboardingResponse)
async def get_azure_instructions() -> OnboardingResponse:
    return OnboardingResponse(
        provider="azure",
        instructions="Create a Service Principal with Reader role on your subscription.",
    )


@router.get("/onboarding/gcp/instructions", response_model=OnboardingResponse)
async def get_gcp_instructions() -> OnboardingResponse:
    return OnboardingResponse(
        provider="gcp",
        instructions="Create a Service Account with Viewer role and download the JSON key.",
    )
