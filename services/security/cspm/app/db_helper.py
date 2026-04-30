"""Async PostgreSQL database helper for CSPM service — matches other foundation services."""
import os
from collections.abc import AsyncGenerator

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
    """FastAPI dependency for async DB sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


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
    async with engine.begin() as conn:
        # checkfirst=True (default) — only creates tables that don't exist yet
        await conn.run_sync(Base.metadata.create_all)
