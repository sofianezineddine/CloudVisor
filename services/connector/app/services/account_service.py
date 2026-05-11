"""Account service — orchestrates cloud account lifecycle.

This module owns all business logic for creating, updating, and deleting
cloud accounts. The route handlers in ``app/api/routes/accounts.py`` are
thin: they validate input, call this service, and return the result.

Responsibilities:
  - AWS IAM role auto-provisioning
  - Credential encryption + Vault/DB storage
  - Connectivity validation
  - Scheduler registration
  - Real-time consumer lifecycle
  - Kafka health-change events
  - Credential rotation
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ConnectorSettings
from app.core.time_utils import utcnow
from app.models import CloudAccountModel
from app.schemas import CloudAccountCreate, CloudAccountUpdate
from app.services.credential_crypto import decrypt_credentials, encrypt_credentials
from app.services.vault_client import VaultClient

logger = logging.getLogger(__name__)


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class AccountCreateResult:
    """Outcome of creating a cloud account."""
    account: CloudAccountModel
    connectivity_ok: bool
    role_auto_provisioned: bool = False
    vault_stored: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class CredentialRotateResult:
    """Outcome of rotating credentials for an account."""
    account_id: str
    vault_stored: bool
    connectivity_ok: bool
    warnings: list[str] = field(default_factory=list)


# ── Service ───────────────────────────────────────────────────────────────────

class AccountService:
    """Orchestrates cloud account lifecycle operations.

    Instantiate per-request with the current DB session and settings.
    All methods are async and safe to call from FastAPI route handlers.
    """

    def __init__(
        self,
        db: AsyncSession,
        settings: ConnectorSettings,
        sync_scheduler: Any | None = None,
        realtime_manager: Any | None = None,
        event_producer: Any | None = None,
    ):
        self._db = db
        self._settings = settings
        self._sync_scheduler = sync_scheduler
        self._realtime_manager = realtime_manager
        self._event_producer = event_producer

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_account(
        self,
        account_data: CloudAccountCreate,
        organization_id: str,
    ) -> AccountCreateResult:
        """Full account creation flow.

        Steps:
          1. Build the CloudAccountModel (not yet persisted)
          2. AWS: auto-provision CloudVisorReadOnly IAM role
          3. Encrypt credentials with per-org DEK
          4. Store encrypted credentials in Vault (or DB fallback)
          5. Validate connectivity
          6. Persist to DB
          7. Emit connector.health_changed
          8. Register with scheduler + start real-time consumers
        """
        warnings: list[str] = []
        role_auto_provisioned = False
        vault_stored = False

        account = CloudAccountModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            provider=account_data.provider,
            name=account_data.name,
            account_id=account_data.account_id,
            region=account_data.region,
            status="pending",
            sync_status="idle",
            polling_interval_minutes=account_data.polling_interval_minutes,
        )

        credentials_to_store = dict(account_data.credentials) if account_data.credentials else {}

        # ── Step 2: AWS role auto-provisioning ────────────────────────────────
        if (
            account_data.provider == "aws"
            and credentials_to_store.get("access_key")
            and credentials_to_store.get("secret_key")
        ):
            credentials_to_store, account, role_auto_provisioned, role_warnings = (
                await self._provision_aws_role(credentials_to_store, account)
            )
            warnings.extend(role_warnings)

        # ── Step 3: Encrypt credentials ───────────────────────────────────────
        encrypted_payload = encrypt_credentials(credentials_to_store, organization_id)

        # ── Step 4: Store credentials ─────────────────────────────────────────
        vault_stored, store_warnings = await self._store_credentials(
            account=account,
            organization_id=organization_id,
            encrypted_payload=encrypted_payload,
        )
        warnings.extend(store_warnings)
        if not vault_stored:
            account.credentials_enc = encrypted_payload

        # ── Step 5: Validate connectivity ─────────────────────────────────────
        connectivity_ok = await self._validate_connectivity(
            provider=account_data.provider,
            credentials=credentials_to_store,
        )
        account.status = "active" if connectivity_ok else "pending"

        # ── Step 6: Persist ───────────────────────────────────────────────────
        self._db.add(account)
        await self._db.commit()
        await self._db.refresh(account)

        # ── Step 7: Emit health_changed ───────────────────────────────────────
        await self._emit_health_changed(
            account=account,
            previous_status="pending",
            new_status=account.status,
        )

        # ── Step 8: Scheduler + real-time consumers ───────────────────────────
        await self._register_with_scheduler(account, organization_id)
        await self._start_realtime_consumers(
            account=account,
            organization_id=organization_id,
            credentials=credentials_to_store,
        )

        return AccountCreateResult(
            account=account,
            connectivity_ok=connectivity_ok,
            role_auto_provisioned=role_auto_provisioned,
            vault_stored=vault_stored,
            warnings=warnings,
        )

    # ── Credential rotation ───────────────────────────────────────────────────

    async def rotate_credentials(
        self,
        account: CloudAccountModel,
        new_credentials: dict[str, Any],
    ) -> CredentialRotateResult:
        """Rotate credentials for an existing account.

        Encrypts the new credentials, stores them in Vault (or DB fallback),
        validates connectivity with the new credentials, and updates the
        account record.

        Does NOT restart real-time consumers — the next sync cycle will pick
        up the new credentials automatically.
        """
        warnings: list[str] = []
        org_id = account.organization_id

        # For AWS: re-run role setup with new keys so the trust policy is updated
        if account.provider == "aws" and new_credentials.get("access_key"):
            new_credentials, account, _, role_warnings = await self._provision_aws_role(
                new_credentials, account
            )
            warnings.extend(role_warnings)

        encrypted_payload = encrypt_credentials(new_credentials, org_id)

        # Rotate in Vault if available
        vault_stored = False
        if account.vault_secret_path and self._settings.vault_enabled:
            try:
                vault = self._make_vault_client()
                if await vault.initialize():
                    await vault.rotate_credentials(
                        account_id=account.id,
                        organization_id=org_id,
                        provider=account.provider,
                        new_credentials=encrypted_payload,
                    )
                    vault_stored = True
                    logger.info(f"Credentials rotated in Vault for account {account.id}")
            except Exception as e:
                warnings.append(f"Vault rotation failed: {e}. Falling back to DB.")

        if not vault_stored:
            account.credentials_enc = encrypted_payload
            account.vault_secret_path = None

        # Validate connectivity with new credentials
        connectivity_ok = await self._validate_connectivity(
            provider=account.provider,
            credentials=new_credentials,
        )
        if connectivity_ok:
            account.status = "active"
            account.consecutive_errors = 0
            account.error_message = None
        else:
            warnings.append(
                "Connectivity check failed with new credentials. "
                "Account status set to pending."
            )
            account.status = "pending"

        account.updated_at = utcnow()
        await self._db.commit()
        await self._db.refresh(account)

        await self._emit_health_changed(
            account=account,
            previous_status="active",
            new_status=account.status,
        )

        return CredentialRotateResult(
            account_id=account.id,
            vault_stored=vault_stored,
            connectivity_ok=connectivity_ok,
            warnings=warnings,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _provision_aws_role(
        self,
        credentials: dict[str, Any],
        account: CloudAccountModel,
    ) -> tuple[dict[str, Any], CloudAccountModel, bool, list[str]]:
        """Auto-provision CloudVisorReadOnly IAM role. Returns updated credentials,
        account, provisioned flag, and any warnings."""
        warnings: list[str] = []
        provisioned = False
        try:
            from app.services.aws_role_setup import AWSRoleSetupService
            setup = AWSRoleSetupService(
                access_key=credentials["access_key"],
                secret_key=credentials["secret_key"],
            )
            role_info = await setup.setup_role()
            credentials = {
                **credentials,
                "role_arn": role_info["role_arn"],
                "external_id": role_info["external_id"],
            }
            account.account_id = role_info["account_id"]
            provisioned = True
            logger.info(
                f"Auto-provisioned CloudVisorReadOnly role in AWS account "
                f"{role_info['account_id']}: {role_info['role_arn']}"
            )
        except ValueError as e:
            # Re-raise validation errors (bad credentials, missing permissions)
            raise
        except Exception as e:
            warnings.append(
                f"AWS role auto-setup failed ({type(e).__name__}: {str(e)[:120]}). "
                "Falling back to direct key usage."
            )
            logger.warning(f"Role auto-setup failed: {e}")
        return credentials, account, provisioned, warnings

    async def _store_credentials(
        self,
        account: CloudAccountModel,
        organization_id: str,
        encrypted_payload: dict[str, Any] | None,
    ) -> tuple[bool, list[str]]:
        """Store encrypted credentials in Vault. Returns (vault_stored, warnings)."""
        warnings: list[str] = []
        if not encrypted_payload:
            return False, warnings

        if not self._settings.vault_enabled:
            return False, warnings

        try:
            vault = self._make_vault_client()
            if await vault.initialize():
                vault_path = await vault.store_credentials(
                    account_id=account.id,
                    organization_id=organization_id,
                    provider=account.provider,
                    credentials=encrypted_payload,
                )
                account.vault_secret_path = vault_path
                logger.info(f"Encrypted credentials stored in Vault for account {account.id}")
                return True, warnings
            else:
                warnings.append("Vault unavailable/sealed — credentials stored in DB.")
        except Exception as e:
            warnings.append(
                f"Vault storage failed ({type(e).__name__}: {str(e)[:120]}) "
                "— credentials stored in DB."
            )
        return False, warnings

    async def _validate_connectivity(
        self,
        provider: str,
        credentials: dict[str, Any],
    ) -> bool:
        """Test connectivity to the cloud provider. Returns True if successful."""
        if not credentials:
            return False
        try:
            from app.clients import ClientFactory
            client = ClientFactory.create_client(provider=provider, credentials=credentials)
            ok = await client.connect()
            try:
                await client.disconnect()
            except Exception:
                pass
            if ok:
                logger.info(f"Connectivity validated for {provider}")
            return ok
        except Exception as e:
            logger.warning(f"Connectivity check failed for {provider}: {e}")
            return False

    async def _register_with_scheduler(
        self,
        account: CloudAccountModel,
        organization_id: str,
    ) -> None:
        """Register account with the sync scheduler and trigger initial full sync."""
        if self._sync_scheduler is None:
            return
        try:
            await self._sync_scheduler.schedule_account(
                account_id=account.id,
                organization_id=organization_id,
                provider=account.provider,
                interval_minutes=account.polling_interval_minutes,
            )
            asyncio.create_task(
                self._sync_scheduler.trigger_sync(account, sync_type="full")
            )
        except Exception as e:
            logger.warning(f"Failed to register account {account.id} with scheduler: {e}")

    async def _start_realtime_consumers(
        self,
        account: CloudAccountModel,
        organization_id: str,
        credentials: dict[str, Any],
    ) -> None:
        """Start real-time event consumers for the account."""
        if self._realtime_manager is None:
            return
        try:
            started = await self._realtime_manager.add_account_consumers(
                account_id=account.id,
                organization_id=organization_id,
                provider=account.provider,
                cloud_account_id=account.account_id,
                credentials=credentials,
                region=account.region,
            )
            if started:
                logger.info(
                    f"Started {started} real-time consumer(s) for account {account.id}"
                )
        except Exception as e:
            logger.warning(
                f"Failed to start real-time consumers for account {account.id}: {e}"
            )

    async def _emit_health_changed(
        self,
        account: CloudAccountModel,
        previous_status: str,
        new_status: str,
        error_message: str | None = None,
    ) -> None:
        """Emit connector.health_changed when status transitions."""
        if previous_status == new_status or self._event_producer is None:
            return
        try:
            await self._event_producer.emit_health_changed(
                account_id=account.id,
                organization_id=account.organization_id,
                provider=account.provider,
                previous_status=previous_status,
                new_status=new_status,
                error_message=error_message,
                resource_count=account.resource_count,
            )
        except Exception as e:
            logger.warning(f"Failed to emit health_changed for {account.id}: {e}")

    def _make_vault_client(self) -> VaultClient:
        return VaultClient(
            vault_url=self._settings.vault_url,
            vault_token=self._settings.vault_token,
            mount_point=self._settings.vault_mount_point,
        )


def get_account_service(
    db: AsyncSession,
    settings: ConnectorSettings,
) -> AccountService:
    """Factory that wires in the global scheduler/manager/producer singletons.

    Call this from route handlers instead of constructing AccountService directly.
    """
    from app.core.dependencies import _sync_scheduler, _realtime_manager

    # Get the event producer from the scheduler (it owns the producer instance)
    event_producer = getattr(_sync_scheduler, "_producer", None) if _sync_scheduler else None

    return AccountService(
        db=db,
        settings=settings,
        sync_scheduler=_sync_scheduler,
        realtime_manager=_realtime_manager,
        event_producer=event_producer,
    )
