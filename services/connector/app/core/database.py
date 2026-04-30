"""Database configuration for Connector service with RLS support."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

from cloudvisor_utils.config import DatabaseSettings


def create_engine(settings: DatabaseSettings) -> Any:
    return create_async_engine(
        settings.url,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        poolclass=AsyncAdaptedQueuePool,
        echo=settings.echo,
        pool_pre_ping=True,
    )


def create_session(engine: Any) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine, class_=AsyncSession,
        expire_on_commit=False, autoflush=False, autocommit=False,
    )


async def dispose_engine(engine: Any) -> None:
    await engine.dispose()


@asynccontextmanager
async def create_db_session(
    session_factory: async_sessionmaker[AsyncSession],
    organization_id: str | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Session with optional RLS context. Always pass org_id for tenant queries."""
    async with session_factory() as session:
        if organization_id:
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
