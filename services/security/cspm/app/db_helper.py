"""Async PostgreSQL database helper for CSPM service — matches other foundation services."""
import os
from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

DATABASE_URL: str = os.environ["DB_URL"]  # Required — no fallback, same as other services


engine = create_async_engine(
    DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=10,
    max_overflow=5,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async DB sessions.

    NOTE: This dependency does NOT set the RLS org context because the org_id
    is not available at session creation time. Callers that need RLS enforcement
    must use get_db_for_org() instead, or call set_rls_context() explicitly.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_for_org(org_id: str) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that creates a DB session with PostgreSQL RLS context set.

    Sets `app.current_org_id` so that RLS policies on all tenant-scoped tables
    automatically filter rows to the requesting organization.

    Usage in route:
        db: AsyncSession = Depends(lambda: get_db_for_org(org_id))

    Or use the set_rls_context() helper after obtaining a session.
    """
    async with AsyncSessionLocal() as session:
        try:
            await set_rls_context(session, org_id)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def set_rls_context(session: AsyncSession, org_id: str) -> None:
    """Set the PostgreSQL RLS context for the current transaction.

    Must be called before any query on a tenant-scoped table.
    The setting is transaction-local (SET LOCAL) so it is automatically
    cleared when the transaction ends.
    """
    # Sanitize org_id to prevent SQL injection — it must be a UUID or alphanumeric string
    safe_org_id = str(org_id).replace("'", "").replace(";", "").replace("\\", "")
    await session.execute(
        text(f"SET LOCAL app.current_org_id = '{safe_org_id}'")
    )


async def init_db() -> None:
    """Create all CSPM tables on startup (checkfirst=True is the default for create_all)."""
    # Import ALL models so SQLAlchemy registers them with Base.metadata
    from app.models_db import (  # noqa: F401
        CSPMScanModel,
        CSPMFindingModel,
        CSPMResourcePostureModel,
        CSPMComplianceResultModel,
        CSPMPostureSnapshotModel,
        CSPMReportModel,
    )
    from app.models import (  # noqa: F401
        IAMAnalysisResultModel,
        IAMCrossAccountTrustModel,
        IAMEscalationPathModel,
        IAMServiceAccountModel,
        AttackPathModel,
        ToxicCombinationModel,
        IaCScanModel,
        IaCFindingModel,
        IaCWebhookConfigModel,
        DriftBaselineModel,
        DriftEventModel,
        ConfigChangeHistoryModel,
        BehavioralBaselineModel,
        AnomalyFindingModel,
        CorrelationRuleModel,
        CorrelatedAlertModel,
        CustomRegoRuleModel,
        RegoRuleVersionModel,
        PolicyHierarchyModel,
        PolicyExceptionModel,
        PolicyAuditLogModel,
    )
    async with engine.begin() as conn:
        # checkfirst=True (default) — only creates tables that don't exist yet
        await conn.run_sync(Base.metadata.create_all)
