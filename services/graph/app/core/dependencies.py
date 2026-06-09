"""FastAPI dependency injection for the graph service."""

import asyncio
import base64
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from functools import lru_cache

import redis.asyncio as redis
from fastapi import Request
from sqlalchemy import text
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
_startup_sync_done = False


# ─── Startup bulk sync from connector DB ──────────────────────────────────────


async def run_startup_db_sync(neo4j_client, session_factory, log) -> None:
    """
    On startup, check if Neo4j is empty and if so bulk-import all resources
    from the connector PostgreSQL DB directly. This guarantees the graph is
    populated even when the Kafka consumer group has already committed offsets
    (i.e. after a container restart).
    """
    global _startup_sync_done
    if _startup_sync_done:
        log.info("Startup sync already completed — skipping")
        return

    # Small delay to let Kafka consumer settle first
    await asyncio.sleep(10)

    try:
        # Check if graph already has data
        result = await neo4j_client.execute_query(
            "MATCH (a:Asset) RETURN count(a) as cnt", {}
        )
        cnt = result[0]["cnt"] if result else 0
        if cnt > 0:
            log.info(f"Startup sync skipped — graph already has {cnt} nodes")
            _startup_sync_done = True
            return

        log.info("Graph is empty — running startup bulk sync from connector DB")

        if not session_factory:
            log.warning("No DB session factory — startup sync skipped")
            return

        from app.services.graph_service import GraphService, AssetNode

        graph_svc = GraphService(neo4j_client=neo4j_client)

        async with session_factory() as db:
            rows = await db.execute(
                text(
                    "SELECT cloud_resource_id, provider, account_id, region, "
                    "resource_type, name, tags, is_public, environment, organization_id "
                    "FROM connector_discovered_resources "
                    "WHERE freshness_state != 'deleted' "
                    "ORDER BY first_seen_at"
                )
            )
            resources = rows.fetchall()

        log.info(f"Startup sync: importing {len(resources)} resources from connector DB")
        synced = 0
        for row in resources:
            try:
                tags = row.tags or {}
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except Exception:
                        tags = {}
                asset = AssetNode(
                    id=row.cloud_resource_id,
                    cloud_resource_id=row.cloud_resource_id,
                    provider=row.provider,
                    account_id=row.account_id,
                    region=row.region or "global",
                    resource_type=row.resource_type,
                    name=row.name,
                    tags={str(k): str(v) for k, v in tags.items()},
                    raw={},
                    organization_id=row.organization_id or "",
                    is_public=bool(row.is_public),
                    environment=row.environment or "unknown",
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow(),
                )
                await graph_svc.create_asset_node(asset)
                synced += 1
                if synced % 200 == 0:
                    log.info(f"Startup sync progress: {synced}/{len(resources)}")
            except Exception as e:
                log.debug(f"Startup sync error for {row.cloud_resource_id}: {e}")

        log.info(f"Startup bulk sync complete: {synced} nodes created")
        _startup_sync_done = True
    except Exception as e:
        log.warning(f"Startup sync failed (non-fatal): {e}")


# ─── Post-Neo4j initialization ────────────────────────────────────────────────


async def _init_after_neo4j_connected(
    settings: CloudvisorSettings,
    graph_settings: GraphSettings,
    session_factory,
) -> None:
    """Start Kafka consumers and trigger startup sync after Neo4j connects."""
    global _resource_consumer, _finding_consumer

    from ..services.graph_service import GraphService
    from ..consumers.resource_events import ResourceEventConsumer, FindingEventConsumer
    from ..producers.graph_events import GraphEventProducer

    kafka_servers = settings.kafka.bootstrap_servers

    graph_producer = GraphEventProducer(bootstrap_servers=kafka_servers)
    await graph_producer.start()

    graph_svc = GraphService(
        neo4j_client=_neo4j_client,
        elasticsearch_client=_elasticsearch_client,
        event_producer=graph_producer,
        db_session_factory=session_factory,
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

    # Trigger startup sync (runs as background task)
    asyncio.create_task(run_startup_db_sync(_neo4j_client, session_factory, logger))


# ─── Background Neo4j recovery ────────────────────────────────────────────────


async def _background_neo4j_retry(
    settings: CloudvisorSettings,
    graph_settings: GraphSettings,
    session_factory,
) -> None:
    """Periodically retry Neo4j connection until it succeeds, then init downstream."""
    global _neo4j_client

    from ..clients.neo4j import Neo4jClient

    client = Neo4jClient(
        uri=graph_settings.neo4j_uri,
        user=graph_settings.neo4j_user,
        password=graph_settings.neo4j_password,
        database=graph_settings.neo4j_database,
        max_connection_lifetime=graph_settings.neo4j_max_connection_lifetime,
        max_connection_pool_size=graph_settings.neo4j_max_connection_pool_size,
    )

    retry_delay = 15
    while _neo4j_client is None:
        try:
            await client.connect()
            _neo4j_client = client
            logger.info("Neo4j connected via background recovery")
            await _init_after_neo4j_connected(settings, graph_settings, session_factory)
            return
        except Exception as e:
            logger.warning(f"Neo4j background retry in {retry_delay}s: {e}")
            await asyncio.sleep(retry_delay)


# ─── Main init ─────────────────────────────────────────────────────────────────


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

    # Retry Neo4j connection with exponential backoff
    retry_delays = [1, 2, 4, 8, 16]
    connected = False
    for attempt, delay in enumerate(retry_delays, 1):
        try:
            await _neo4j_client.connect()
            logger.info("Neo4j connected")
            connected = True
            break
        except Exception as e:
            if attempt < len(retry_delays):
                logger.warning(f"Neo4j connection attempt {attempt}/{len(retry_delays)} failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Neo4j connection failed after {len(retry_delays)} attempts: {e}")

    if not connected:
        _neo4j_client = None
        logger.warning("Neo4j unavailable at startup — starting background recovery")

    # ── Elasticsearch ─────────────────────────────────────────────────────────
    _elasticsearch_client = ElasticsearchClient(
        url=graph_settings.elasticsearch_url,
        index_prefix=graph_settings.elasticsearch_index_prefix,
        username=graph_settings.elasticsearch_username,
        password=graph_settings.elasticsearch_password,
    )
    try:
        await _elasticsearch_client.connect()
        logger.info("Elasticsearch connected")
    except Exception as e:
        logger.warning(f"Elasticsearch connection failed (non-fatal): {e}")
        _elasticsearch_client = None

    # Create ES index with proper mappings before startup sync runs,
    # otherwise the startup sync's bulk indexing auto-creates the index
    # with dynamic mapping (all text fields, making term queries fail).
    if _elasticsearch_client:
        try:
            from ..clients.elasticsearch import ASSET_MAPPINGS
            await _elasticsearch_client.create_index("assets", ASSET_MAPPINGS)
            logger.info("Elasticsearch asset index created with proper mappings")
        except Exception as e:
            logger.warning(f"Elasticsearch index creation failed (non-fatal): {e}")

    # ── Kafka consumers + startup sync (only if Neo4j connected) ──────────────
    if _neo4j_client:
        await _init_after_neo4j_connected(settings, graph_settings, _session_factory)
    else:
        asyncio.create_task(_background_neo4j_retry(settings, graph_settings, _session_factory))

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
    """Yield the module-level Neo4j client (may be None if not connected)."""
    yield _neo4j_client


async def get_elasticsearch(request: Request):
    yield request.app.state.elasticsearch


async def get_settings(request: Request):
    yield request.app.state.graph_settings


@lru_cache
def get_graph_settings_cached() -> GraphSettings:
    return get_graph_settings()
