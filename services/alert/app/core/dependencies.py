"""FastAPI dependency injection for the Alert service."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

import redis.asyncio as redis
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from cloudvisor_utils.config import CloudvisorSettings

from .config import AlertSettings, get_alert_settings
from .database import create_engine, create_session, create_db_session

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None
_redis_client = None
_finding_consumer = None
_resource_consumer = None


async def init_dependencies(settings: CloudvisorSettings, alert_settings: AlertSettings) -> None:
    """Initialize all dependencies at app startup."""
    global _engine, _session_factory, _redis_client
    global _finding_consumer, _resource_consumer

    from ..models import Base

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    _engine = create_engine(settings.db.url)
    _session_factory = create_session(_engine)

    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Alert tables created")

    # ── Redis ─────────────────────────────────────────────────────────────────
    _redis_client = redis.from_url(
        settings.redis.url,
        decode_responses=True,
    )

    # ── Kafka consumers ───────────────────────────────────────────────────────
    kafka_servers = settings.kafka.bootstrap_servers

    # Start Kafka producer for finding events (finding.created, finding.resolved, etc.)
    from aiokafka import AIOKafkaProducer
    import json as _json
    _kafka_producer = AIOKafkaProducer(
        bootstrap_servers=kafka_servers,
        value_serializer=lambda v: _json.dumps(v, default=str).encode("utf-8"),
        acks="all",
        retry_backoff_ms=500,
    )
    try:
        await _kafka_producer.start()
        logger.info("Alert Kafka producer started")
    except Exception as e:
        logger.warning(f"Alert Kafka producer failed to start: {e}")
        _kafka_producer = None

    from ..consumers.finding_events import FindingEventConsumer, ResourceEventConsumer
    from ..services import FindingService, NotificationService

    _finding_consumer = FindingEventConsumer(
        bootstrap_servers=kafka_servers,
        session_factory=_session_factory,
        redis_client=_redis_client,
        kafka_producer=_kafka_producer,
    )
    _resource_consumer = ResourceEventConsumer(
        bootstrap_servers=kafka_servers,
        session_factory=_session_factory,
    )

    try:
        await _finding_consumer.start()
        asyncio.create_task(_finding_consumer.run())
        logger.info("Finding event consumer started")
    except Exception as e:
        logger.warning(f"Finding consumer failed to start: {e}")

    try:
        await _resource_consumer.start()
        asyncio.create_task(_resource_consumer.run())
        logger.info("Resource event consumer started")
    except Exception as e:
        logger.warning(f"Resource consumer failed to start: {e}")

    logger.info("Alert service dependencies initialized")


async def shutdown_dependencies() -> None:
    global _redis_client, _engine, _finding_consumer, _resource_consumer

    if _finding_consumer:
        await _finding_consumer.stop()
    if _resource_consumer:
        await _resource_consumer.stop()

    if _redis_client:
        await _redis_client.close()
        _redis_client = None

    if _engine:
        await _engine.dispose()
        _engine = None

    logger.info("Alert service dependencies shut down")


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database sessions with RLS — org_id from JWT."""
    org_id = _extract_org_id(request)
    session_factory = request.app.state.session_factory
    async with create_db_session(session_factory, org_id) as session:
        yield session


def _extract_org_id(request: Request) -> str | None:
    """Extract organization_id from JWT Bearer token or X-Org-ID header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import base64, json
            token = auth[7:]
            parts = token.split(".")
            if len(parts) == 3:
                payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                return payload.get("org_id")
        except Exception:
            pass
    return request.headers.get("X-Org-ID")


async def get_redis(request: Request):
    yield request.app.state.redis


@lru_cache
def get_alert_settings_cached() -> AlertSettings:
    return get_alert_settings()
