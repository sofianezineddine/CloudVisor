"""FastAPI dependency injection for the graph service."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

import redis.asyncio as redis
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from cloudvisor_utils.config import CloudvisorSettings

from .config import GraphSettings, get_graph_settings
from .database import create_engine, create_session, create_db_session

logger = logging.getLogger(__name__)

_neo4j_client = None
_elasticsearch_client = None
_redis_client = None
_engine = None
_session_factory = None
_resource_consumer = None
_finding_consumer = None


async def init_dependencies(settings: CloudvisorSettings, graph_settings: GraphSettings) -> None:
    """Initialize all dependencies at app startup."""
    global _neo4j_client, _elasticsearch_client, _redis_client
    global _engine, _session_factory, _resource_consumer, _finding_consumer

    from .database import create_engine, create_session
    from ..clients.neo4j import Neo4jClient
    from ..clients.elasticsearch import ElasticsearchClient
    from ..services.snapshots import SnapshotBase

    # ── PostgreSQL (for snapshots) ────────────────────────────────────────────
    _engine = create_engine(settings.db.url)
    _session_factory = create_session(_engine)

    # Create snapshot tables
    async with _engine.begin() as conn:
        await conn.run_sync(SnapshotBase.metadata.create_all)

    # Attempt to convert asset_snapshots to a TimescaleDB hypertable for
    # efficient time-range queries and automatic compression. Non-fatal if
    # TimescaleDB extension is not installed (plain PostgreSQL still works).
    try:
        from sqlalchemy import text
        async with _engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))
            await conn.execute(text(
                "SELECT create_hypertable('asset_snapshots', 'snapshot_timestamp', "
                "if_not_exists => TRUE, migrate_data => TRUE)"
            ))
        logger.info("TimescaleDB hypertable created for asset_snapshots")
    except Exception as e:
        logger.debug(f"TimescaleDB hypertable setup skipped (non-fatal): {e}")

    logger.info("Graph snapshot tables created")

    # ── Redis ─────────────────────────────────────────────────────────────────
    _redis_client = redis.from_url(
        settings.redis.url,
        decode_responses=True,
    )

    # ── Neo4j ─────────────────────────────────────────────────────────────────
    _neo4j_client = Neo4jClient(
        uri=graph_settings.neo4j_uri,
        user=graph_settings.neo4j_user,
        password=graph_settings.neo4j_password,
        database=graph_settings.neo4j_database,
        max_connection_lifetime=graph_settings.neo4j_max_connection_lifetime,
        max_connection_pool_size=graph_settings.neo4j_max_connection_pool_size,
    )
    try:
        await _neo4j_client.connect()
        logger.info("Neo4j connected")
    except Exception as e:
        logger.error(f"Neo4j connection failed: {e}")
        _neo4j_client = None

    # ── Elasticsearch ─────────────────────────────────────────────────────────
    _elasticsearch_client = ElasticsearchClient(
        url=graph_settings.elasticsearch_url,
        index_prefix=graph_settings.elasticsearch_index_prefix,
    )
    try:
        await _elasticsearch_client.connect()
        logger.info("Elasticsearch connected")
    except Exception as e:
        logger.warning(f"Elasticsearch connection failed (non-fatal): {e}")
        _elasticsearch_client = None

    # ── Kafka consumers ───────────────────────────────────────────────────────
    kafka_servers = settings.kafka.bootstrap_servers
    if _neo4j_client:
        from ..services.graph_service import GraphService
        from ..consumers.resource_events import ResourceEventConsumer, FindingEventConsumer
        from ..producers.graph_events import GraphEventProducer

        # Start Kafka producer for graph events
        graph_producer = GraphEventProducer(bootstrap_servers=kafka_servers)
        await graph_producer.start()

        graph_svc = GraphService(
            neo4j_client=_neo4j_client,
            elasticsearch_client=_elasticsearch_client,
            event_producer=graph_producer,
            db_session_factory=_session_factory,
            redis_client=_redis_client,
        )

        _resource_consumer = ResourceEventConsumer(
            bootstrap_servers=kafka_servers,
            graph_service=graph_svc,
        )
        _finding_consumer = FindingEventConsumer(
            bootstrap_servers=kafka_servers,
            graph_service=graph_svc,
        )

        try:
            await _resource_consumer.start()
            asyncio.create_task(_resource_consumer.run())
            logger.info("Resource event consumer started")
        except Exception as e:
            logger.warning(f"Resource consumer failed to start: {e}")

        try:
            await _finding_consumer.start()
            asyncio.create_task(_finding_consumer.run())
            logger.info("Finding event consumer started")
        except Exception as e:
            logger.warning(f"Finding consumer failed to start: {e}")

    logger.info("Graph service dependencies initialized")


async def shutdown_dependencies() -> None:
    """Clean up all dependencies at app shutdown."""
    global _neo4j_client, _elasticsearch_client, _redis_client, _engine
    global _resource_consumer, _finding_consumer

    if _resource_consumer:
        await _resource_consumer.stop()
    if _finding_consumer:
        await _finding_consumer.stop()

    if _neo4j_client:
        await _neo4j_client.disconnect()
        _neo4j_client = None

    if _elasticsearch_client:
        await _elasticsearch_client.disconnect()
        _elasticsearch_client = None

    if _redis_client:
        await _redis_client.close()
        _redis_client = None

    if _engine:
        await _engine.dispose()
        _engine = None

    logger.info("Graph service dependencies shut down")


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database sessions with RLS — org_id from JWT."""
    org_id = _extract_org_id(request)
    session_factory = request.app.state.session_factory
    async with create_db_session(session_factory, org_id) as session:
        yield session


def _extract_org_id(request: Request) -> str | None:
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


async def get_neo4j(request: Request):
    yield request.app.state.neo4j


async def get_elasticsearch(request: Request):
    yield request.app.state.elasticsearch


async def get_settings(request: Request):
    yield request.app.state.graph_settings


@lru_cache
def get_graph_settings_cached() -> GraphSettings:
    return get_graph_settings()
