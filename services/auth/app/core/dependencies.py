"""FastAPI dependency injection for the auth service."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

import redis.asyncio as redis
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from cloudvisor_utils.config import CloudvisorSettings, get_settings
from cloudvisor_utils.tracing import get_tracer

from .config import AuthSettings, get_auth_settings
from .database import create_engine, create_session, create_db_session

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None
_engine: object | None = None
_session_factory: object | None = None
_kafka_producer: object | None = None
_session_cleanup_task: asyncio.Task | None = None
_audit_retention_service: object | None = None  # Fix 3: audit log retention


async def init_dependencies(settings: CloudvisorSettings, auth_settings: AuthSettings) -> None:
    """Initialize shared dependencies."""
    global _redis_client, _engine, _session_factory, _kafka_producer, _session_cleanup_task

    _engine = create_engine(settings.db.url)
    _session_factory = create_session(_engine)
    from ..models import Base
    from ..models.admin import create_admin_tables, seed_default_admin
    from ..models.roles import RoleModel, UserRoleModel

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create roles tables
    try:
        async with _engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS roles (
                    id UUID PRIMARY KEY,
                    organization_id UUID NOT NULL REFERENCES organizations(id),
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    permissions JSON DEFAULT '[]',
                    is_builtin BOOLEAN DEFAULT FALSE,
                    is_default BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    UNIQUE(organization_id, name)
                )
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_roles (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id),
                    organization_id UUID NOT NULL REFERENCES organizations(id),
                    role_name VARCHAR(100) NOT NULL,
                    scope JSON,
                    created_at TIMESTAMP NOT NULL,
                    UNIQUE(user_id, role_name, organization_id)
                )
            """))
    except Exception as e:
        logger.debug(f"Roles tables: {e}")

    # Create admin tables and seed default admin
    await create_admin_tables(_engine)
    await seed_default_admin(_engine)

    # Apply RLS policies
    from .database import setup_rls_policies
    try:
        await setup_rls_policies(_engine)
        logger.info("RLS policies applied")
    except Exception as e:
        logger.debug(f"RLS policies (may already exist): {e}")

    _redis_client = redis.from_url(
        settings.redis.url,
        password=settings.redis.password,
        db=settings.redis.db,
        decode_responses=True,
    )

    # Initialize async Kafka producer for audit events
    try:
        kafka_servers = (
            getattr(settings.kafka, "bootstrap_servers", None)
            or getattr(settings.kafka, "brokers", None)
            or "cv-kafka:9092"
        )
        from ..producers.audit import AuditEventProducer
        _kafka_producer = AuditEventProducer(bootstrap_servers=kafka_servers)
        await _kafka_producer.start()
        logger.info("Audit Kafka producer started")
    except Exception as e:
        logger.warning(f"Kafka producer failed to start (non-fatal): {e}")
        _kafka_producer = None

    # Start background session cleanup task
    _session_cleanup_task = asyncio.create_task(_session_cleanup_loop())

    # Fix 3: Start audit log retention job (spec §3.3: 365 days minimum)
    from ..services.audit_retention import AuditRetentionService
    _audit_retention_service = AuditRetentionService(
        session_factory=_session_factory,
        retention_days=auth_settings.audit_log_retention_days,
    )
    _audit_retention_service.start()

    logger.info("Auth service dependencies initialized")


async def _session_cleanup_loop() -> None:
    """Background task: expire inactive sessions every 30 minutes."""
    while True:
        try:
            await asyncio.sleep(1800)  # 30 minutes
            await _cleanup_expired_sessions()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")


async def _cleanup_expired_sessions() -> None:
    """Mark sessions as inactive if they've expired or been inactive too long."""
    if not _session_factory:
        return
    try:
        from datetime import datetime
        from sqlalchemy import update
        from ..models import SessionModel

        async with _session_factory() as session:
            now = datetime.utcnow()
            stmt = (
                update(SessionModel)
                .where(
                    SessionModel.is_active == True,
                    SessionModel.expires_at < now,
                )
                .values(is_active=False)
            )
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount:
                logger.info(f"Expired {result.rowcount} sessions")
    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")


async def shutdown_dependencies() -> None:
    """Clean up dependencies."""
    global _redis_client, _engine, _kafka_producer, _session_cleanup_task, _audit_retention_service

    if _session_cleanup_task:
        _session_cleanup_task.cancel()
        try:
            await _session_cleanup_task
        except asyncio.CancelledError:
            pass
        _session_cleanup_task = None

    # Stop audit retention job
    if _audit_retention_service:
        await _audit_retention_service.stop()
        _audit_retention_service = None

    if _kafka_producer:
        await _kafka_producer.stop()
        _kafka_producer = None

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    if _engine:
        from .database import dispose_engine
        await dispose_engine(_engine)
        _engine = None


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database sessions with RLS."""
    org_id = request.headers.get("X-Org-ID")
    session_factory = getattr(request.app.state, "session_factory", None) or _session_factory
    if session_factory is None:
        raise RuntimeError("Database session factory is not initialized")
    async with create_db_session(session_factory, org_id) as session:
        yield session


async def get_redis(request: Request) -> AsyncGenerator[redis.Redis, None]:
    """Dependency for Redis client."""
    client = getattr(request.app.state, "redis", None) or _redis_client
    if client is None:
        raise RuntimeError("Redis client is not initialized")
    yield client


async def get_kafka_producer(request: Request):
    """Dependency for Kafka audit producer."""
    yield _kafka_producer


@lru_cache
def get_auth_settings_cached() -> AuthSettings:
    return get_auth_settings()


def get_tracer() -> object:
    """Get OpenTelemetry tracer."""
    return get_tracer("cloudvisor-auth")
