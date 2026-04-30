"""Database configuration for Auth service with RLS support."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool


metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


def create_engine(database_url: str) -> Any:
    """Create async SQLAlchemy engine."""
    return create_async_engine(
        database_url,
        pool_size=20,
        max_overflow=10,
        poolclass=AsyncAdaptedQueuePool,
        echo=False,
        pool_pre_ping=True,
    )


def create_session(engine: Any) -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@asynccontextmanager
async def create_db_session(
    session_factory: async_sessionmaker[AsyncSession],
    organization_id: str | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Context manager with RLS context injection."""
    async with session_factory() as session:
        if organization_id:
            await session.execute(text(f"SET LOCAL app.current_org_id = '{organization_id}'"))
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def setup_rls_policies(engine: Any) -> None:
    """Create RLS policies for all tenant-scoped tables."""
    async with engine.begin() as conn:
        rls_policies = [
            """
            ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
            CREATE POLICY org_isolation ON organizations
                USING (id::text = current_setting('app.current_org_id', true)::text);
            """,
            """
            ALTER TABLE users ENABLE ROW LEVEL SECURITY;
            CREATE POLICY user_org_isolation ON users
                USING (organization_id::text = current_setting('app.current_org_id', true)::text);
            """,
            """
            ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
            CREATE POLICY role_org_isolation ON roles
                USING (organization_id::text = current_setting('app.current_org_id', true)::text);
            """,
            """
            ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
            CREATE POLICY session_org_isolation ON sessions
                USING (user_id IN (SELECT id FROM users WHERE organization_id::text = current_setting('app.current_org_id', true)::text));
            """,
            """
            ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
            CREATE POLICY api_key_org_isolation ON api_keys
                USING (user_id IN (SELECT id FROM users WHERE organization_id::text = current_setting('app.current_org_id', true)::text));
            """,
            """
            ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
            CREATE POLICY audit_org_isolation ON audit_log
                USING (organization_id::text = current_setting('app.current_org_id', true)::text);
            """,
        ]

        for policy in rls_policies:
            try:
                await conn.execute(text(policy))
            except Exception:
                pass
