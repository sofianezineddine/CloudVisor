"""FastAPI dependency injection for the copilot service."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

import redis.asyncio as redis
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from cloudvisor_utils.config import CloudvisorSettings, get_settings
from cloudvisor_utils.database import create_engine, create_session_factory, rls_session

from .config import CopilotSettings, get_copilot_settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None
_engine: object | None = None
_session_factory: object | None = None
_kafka_producer: object | None = None


async def init_dependencies(settings: CloudvisorSettings, copilot_settings: CopilotSettings) -> None:
    """Initialize shared dependencies."""
    global _redis_client, _engine, _session_factory, _kafka_producer

    # Initialize database
    _engine = create_engine(settings.db.url)
    _session_factory = create_session_factory(_engine)

    # Create tables
    from ..models import Base

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created")

    # Initialize Redis
    _redis_client = redis.from_url(
        settings.redis.url,
        password=settings.redis.password,
        db=settings.redis.db,
        decode_responses=True,
    )

    logger.info("Redis client initialized")

    # Initialize Kafka producer for audit events
    try:
        kafka_servers = getattr(settings.kafka, "bootstrap_servers", "localhost:9092")
        from ..producers.audit_producer import AuditEventProducer

        _kafka_producer = AuditEventProducer(bootstrap_servers=kafka_servers)
        await _kafka_producer.start()
        logger.info("Kafka audit producer started")
    except Exception as e:
        logger.warning(f"Kafka producer failed to start (non-fatal): {e}")
        _kafka_producer = None

    logger.info("Copilot service dependencies initialized")


async def shutdown_dependencies() -> None:
    """Clean up dependencies."""
    global _redis_client, _engine, _kafka_producer

    if _kafka_producer:
        await _kafka_producer.stop()
        _kafka_producer = None

    if _redis_client:
        await _redis_client.close()
        _redis_client = None

    if _engine:
        await _engine.dispose()
        _engine = None

    logger.info("Dependencies shut down")


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database sessions with RLS."""
    org_id = request.headers.get("X-Org-ID")
    session_factory = getattr(request.app.state, "session_factory", None) or _session_factory

    if session_factory is None:
        raise RuntimeError("Database session factory is not initialized")

    async with rls_session(session_factory, org_id) as session:
        yield session


async def get_redis(request: Request) -> AsyncGenerator[redis.Redis, None]:
    """Dependency for Redis client."""
    client = getattr(request.app.state, "redis", None) or _redis_client

    if client is None:
        raise RuntimeError("Redis client is not initialized")

    yield client


async def get_kafka_producer(request: Request):
    """Dependency for Kafka audit producer."""
    producer = getattr(request.app.state, "kafka_producer", None) or _kafka_producer
    yield producer


@lru_cache
def get_copilot_settings_cached() -> CopilotSettings:
    """Get cached copilot settings."""
    return get_copilot_settings()
