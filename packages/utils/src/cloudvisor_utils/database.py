"""
Shared database utilities with Row-Level Security (RLS) support.

Every tenant-scoped DB session MUST call SET LOCAL app.current_org_id
before executing any query. This is enforced here — not in application code.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def create_engine(database_url: str, pool_size: int = 20, max_overflow: int = 10) -> Any:
    """Create an async SQLAlchemy engine."""
    return create_async_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        poolclass=AsyncAdaptedQueuePool,
        echo=False,
        pool_pre_ping=True,
    )


def create_session_factory(engine: Any) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@asynccontextmanager
async def rls_session(
    session_factory: async_sessionmaker[AsyncSession],
    organization_id: str | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager that opens a DB session and sets the RLS context.

    If organization_id is provided, executes:
        SET LOCAL app.current_org_id = '<org_id>'

    This activates PostgreSQL Row-Level Security policies on all
    tenant-scoped tables, ensuring a user can only see their own data.

    Usage:
        async with rls_session(session_factory, org_id) as session:
            result = await session.execute(select(FindingModel))
    """
    async with session_factory() as session:
        if organization_id:
            # SET LOCAL is transaction-scoped — automatically cleared on commit/rollback
            await session.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"),
                {"org_id": str(organization_id)},
            )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def system_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for system-level operations (no RLS).
    Use ONLY for: table creation, seeding built-in data, admin operations.
    Never use for tenant data queries.
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
