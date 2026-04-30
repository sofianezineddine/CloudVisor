"""FastAPI dependency injection for the connector service."""

import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

import redis.asyncio as redis
from fastapi import Depends, Request
from prometheus_client import generate_latest
from sqlalchemy.ext.asyncio import AsyncSession

from cloudvisor_utils.config import CloudvisorSettings, get_settings
from cloudvisor_utils.tracing import get_tracer

from .config import ConnectorSettings, get_connector_settings
from .database import create_session, create_db_session

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None
_engine: object | None = None
_session_factory: object | None = None
_sync_scheduler: object | None = None


async def init_dependencies(settings: CloudvisorSettings) -> None:
    """Initialize shared dependencies at app startup."""
    global _redis_client, _engine, _session_factory, _sync_scheduler

    from .database import create_engine
    from ..models import create_connector_tables
    from ..producers import ResourceEventProducer
    from ..scheduler import SyncScheduler

    _engine = create_engine(settings.db)
    _session_factory = create_session(_engine)
    _redis_client = redis.from_url(
        settings.redis.url,
        password=settings.redis.password if hasattr(settings.redis, 'password') and settings.redis.password else None,
        db=settings.redis.db if hasattr(settings.redis, 'db') else 0,
        decode_responses=True,
    )

    # Create connector tables with RLS policies
    await create_connector_tables(_engine)

    # Initialize Vault client if enabled
    vault_client = None
    vault_enabled = (
        getattr(settings.vault, 'enabled', False) or 
        getattr(settings.vault, 'vault_enabled', False)
    )
    vault_url = getattr(settings.vault, 'url', '') or ''
    vault_token = getattr(settings.vault, 'token', None)
    
    # Also check connector-specific env vars
    from ..core.config import get_connector_settings
    conn_settings = get_connector_settings()
    if conn_settings.vault_enabled:
        vault_enabled = True
        vault_url = conn_settings.vault_url
        vault_token = conn_settings.vault_token
    
    if vault_enabled and vault_url:
        from ..services.vault_client import VaultClient
        vault_client = VaultClient(
            vault_url=vault_url,
            vault_token=vault_token,
            mount_point=conn_settings.vault_mount_point,
        )
        if await vault_client.initialize():
            logger.info("Vault client initialized successfully")
        else:
            logger.warning("Vault initialization failed - running without credential storage")
            vault_client = None

    # Initialize Kafka producer
    # Try multiple attribute names since the settings schema may vary
    kafka_servers = (
        getattr(settings.kafka, "bootstrap_servers", None)
        or getattr(settings.kafka, "brokers", None)
        or getattr(settings.kafka, "servers", None)
        or "cv-kafka:9092"
    )
    event_producer = ResourceEventProducer(
        bootstrap_servers=kafka_servers,
    )
    await event_producer.start()

    # Initialize sync scheduler
    _sync_scheduler = SyncScheduler(
        redis_client=_redis_client,
        event_producer=event_producer,
        db_session_factory=_session_factory,
        vault_client=vault_client,
    )
    await _sync_scheduler.start()

    logger.info("Connector dependencies initialized (tables created, scheduler started)")


async def shutdown_dependencies() -> None:
    """Clean up dependencies at app shutdown."""
    global _redis_client, _engine, _sync_scheduler

    if _sync_scheduler:
        await _sync_scheduler.stop()
        _sync_scheduler = None

    if _redis_client:
        await _redis_client.close()
        _redis_client = None

    if _engine:
        from .database import dispose_engine
        await dispose_engine(_engine)
        _engine = None

    logger.info("Connector dependencies shut down")


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database sessions with RLS — org_id from JWT."""
    from .auth import get_org_id_from_token
    org_id = get_org_id_from_token(request.headers.get("Authorization", ""))
    if not org_id:
        org_id = request.headers.get("X-Org-ID")
    session_factory = request.app.state.session_factory
    async with create_db_session(session_factory, org_id) as session:
        yield session


async def get_redis(request: Request) -> AsyncGenerator[redis.Redis, None]:
    """Dependency for Redis client."""
    client = request.app.state.redis
    yield client


@lru_cache
def get_connector_settings_cached() -> ConnectorSettings:
    return get_connector_settings()


def get_tracer() -> object:
    """Get OpenTelemetry tracer."""
    return get_tracer("cloudvisor-connector")
