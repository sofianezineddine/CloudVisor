"""SQLAlchemy ORM models for the Cloud Connector service."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Integer,
    String,
    Text,
    func,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all connector models."""
    pass


class CloudAccountModel(Base):
    """Cloud account configuration for connector service."""

    __tablename__ = "connector_cloud_accounts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False, default="global")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    # Valid statuses: pending | active | error | paused | auth_failed | partial_sync
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="idle")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_count: Mapped[int] = mapped_column(Integer, default=0)
    polling_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    vault_secret_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Fallback credential storage when Vault is not available (dev/local environments).
    # In production, credentials should always be in Vault and this column stays NULL.
    credentials_enc: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    # Soft-delete tombstone — set when an account is disconnected.
    # Spec §3.3: audit logs retained for 365 days minimum; keeping the account
    # row (with credentials wiped) lets audit queries resolve the account name.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint("organization_id", "provider", "account_id", name="uq_org_provider_account"),
        Index("idx_connector_accounts_org_status", "organization_id", "status"),
        Index("idx_connector_accounts_org_provider", "organization_id", "provider"),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "provider": self.provider,
            "name": self.name,
            "account_id": self.account_id,
            "region": self.region,
            "status": self.status,
            "sync_status": self.sync_status,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_successful_sync_at": (
                self.last_successful_sync_at.isoformat() if self.last_successful_sync_at else None
            ),
            "consecutive_errors": self.consecutive_errors,
            "error_message": self.error_message,
            "resource_count": self.resource_count,
            "polling_interval_minutes": self.polling_interval_minutes,
            "vault_secret_path": self.vault_secret_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class DiscoveredResourceModel(Base):
    """Discovered cloud resource - stores normalized CDM resources."""

    __tablename__ = "connector_discovered_resources"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    cloud_resource_id: Mapped[str] = mapped_column(String(512), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    account_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    environment: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    resource_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # ── Freshness state machine ──────────────────────────────────────────────
    # "fresh"   — resource was confirmed in the most recent sync
    # "stale"   — missing for ``missed_sync_count`` recent syncs but under the
    #             threshold at which we mark it deleted. Useful for catching
    #             IAM permission drift where one service silently stops
    #             returning data without meaning the resources vanished.
    # "deleted" — confirmed removed (either by missing for N cycles, or by
    #             explicit real-time deletion event).
    freshness_state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="fresh"
    )
    missed_sync_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("cloud_resource_id", "organization_id", name="uq_resource_org"),
        Index("idx_discovered_resources_org_provider", "organization_id", "provider"),
        Index("idx_discovered_resources_org_type", "organization_id", "resource_type"),
        Index("idx_discovered_resources_org_env", "organization_id", "environment"),
        Index("idx_discovered_resources_org_public", "organization_id", "is_public"),
        Index("idx_discovered_resources_hash", "resource_hash"),
        Index("idx_discovered_resources_account", "account_id"),
    )

    def to_cdm(self) -> dict:
        """Convert to Common Data Model format."""
        from cloudvisor_types.models import CloudResource, CloudProvider, Environment

        return CloudResource(
            id=self.id,
            cloud_resource_id=self.cloud_resource_id,
            provider=CloudProvider(self.provider),
            account_id=self.account_id,
            region=self.region,
            resource_type=self.resource_type,
            name=self.name,
            tags=self.tags or {},
            raw=self.raw or {},
            organization_id=self.organization_id,
            is_public=self.is_public,
            environment=Environment(self.environment),
            first_seen_at=self.first_seen_at,
            last_seen_at=self.last_seen_at,
        )


class ScanHistoryModel(Base):
    """Persisted record of each sync operation for an account.

    Written by the scheduler after every sync completes (success or failure).
    Provides the data for ``GET /accounts/{id}/scans``.
    """

    __tablename__ = "connector_scan_history"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    sync_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    discovered: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(nullable=False, default=0.0)
    error_details: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_scan_history_account", "account_id"),
        Index("idx_scan_history_org", "organization_id"),
        Index("idx_scan_history_started", "started_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "account_id": self.account_id,
            "sync_type": self.sync_type,
            "status": self.status,
            "correlation_id": self.correlation_id,
            "discovered": self.discovered,
            "updated": self.updated,
            "deleted": self.deleted,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "error_details": self.error_details or [],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


async def create_connector_tables(engine: Any) -> None:
    """Create all connector tables and ensure RLS policies exist.

    Postgres does NOT support `CREATE POLICY IF NOT EXISTS`, so we wrap each
    `CREATE POLICY` in a DO block that checks `pg_policies` first. This is
    fully idempotent across restarts.
    """
    import logging
    from sqlalchemy import text
    logger = logging.getLogger(__name__)

    # Create tables using the engine directly (not in a transaction)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Connector tables created successfully")

    # ── Column migrations (idempotent) ────────────────────────────────────────
    try:
        async with engine.begin() as conn:
            await conn.execute(text(
                "ALTER TABLE connector_cloud_accounts "
                "ADD COLUMN IF NOT EXISTS credentials_enc JSONB"
            ))
            # Soft-delete column for accounts (tombstone pattern for audit retention)
            await conn.execute(text(
                "ALTER TABLE connector_cloud_accounts "
                "ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ"
            ))
            # Freshness state columns for the stale-sweep feature
            await conn.execute(text(
                "ALTER TABLE connector_discovered_resources "
                "ADD COLUMN IF NOT EXISTS freshness_state VARCHAR(20) "
                "NOT NULL DEFAULT 'fresh'"
            ))
            await conn.execute(text(
                "ALTER TABLE connector_discovered_resources "
                "ADD COLUMN IF NOT EXISTS missed_sync_count INTEGER "
                "NOT NULL DEFAULT 0"
            ))
            logger.debug("Connector column migrations applied")
    except Exception as e:
        logger.warning(f"Column migration failed: {e}")

    # ── RLS policies (idempotent via pg_policies existence check) ─────────────
    _policies = [
        ("connector_cloud_accounts", "connector_accounts_tenant_isolation"),
        ("connector_discovered_resources", "connector_resources_tenant_isolation"),
    ]

    policy_sql_template = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE schemaname = 'public'
              AND tablename = '{table}'
              AND policyname = '{policy}'
        ) THEN
            EXECUTE format(
                'CREATE POLICY %I ON %I AS PERMISSIVE FOR ALL '
                'USING (organization_id::text = current_setting(''app.current_org_id'', true)::text) '
                'WITH CHECK (organization_id::text = current_setting(''app.current_org_id'', true)::text)',
                '{policy}', '{table}'
            );
        END IF;
    END $$;
    """

    for table, policy in _policies:
        try:
            async with engine.begin() as conn:
                # Enable RLS — safe to re-run
                await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
                # Create policy if missing
                await conn.execute(text(policy_sql_template.format(table=table, policy=policy)))
            logger.info(f"RLS policy ensured: {policy} on {table}")
        except Exception as e:
            # This is a HARD failure — log at ERROR because tenant isolation is
            # compromised if the policy doesn't exist.
            logger.error(
                f"Failed to apply RLS policy {policy} on {table}: {e}. "
                "Tenant isolation may be incomplete — investigate immediately."
            )
