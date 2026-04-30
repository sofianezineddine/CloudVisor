"""Integration tests for cloud discovery service.

These tests require a running Docker Compose stack:
  docker compose up -d postgres redis kafka

Run with:
  pytest tests/integration/ -v --timeout=60
"""

import pytest
import os

# Skip all integration tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.getenv("INTEGRATION_TESTS") != "1",
    reason="Set INTEGRATION_TESTS=1 to run integration tests",
)


@pytest.mark.asyncio
async def test_database_connection():
    """Test PostgreSQL connection and table creation."""
    import asyncpg

    db_url = os.getenv("DB_URL", "postgresql://cvadmin:cvpassword@localhost:5432/cloudvisor")
    # Convert asyncpg URL format
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(db_url)
    try:
        result = await conn.fetchval("SELECT 1")
        assert result == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_redis_connection():
    """Test Redis connection."""
    import redis.asyncio as redis

    client = redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    try:
        await client.ping()
        await client.set("test:connector:ping", "pong", ex=10)
        val = await client.get("test:connector:ping")
        assert val == "pong"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_kafka_producer():
    """Test Kafka producer can connect and send a message."""
    from app.producers import ResourceEventProducer

    producer = ResourceEventProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    )
    await producer.start()
    try:
        await producer.emit_sync_started(
            account_id="test-account",
            organization_id="test-org",
            provider="aws",
            correlation_id="test-correlation",
        )
    finally:
        await producer.stop()


@pytest.mark.asyncio
async def test_connector_tables_created():
    """Test that connector tables are created on startup."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    db_url = os.getenv(
        "DB_URL",
        "postgresql+asyncpg://cvadmin:cvpassword@localhost:5432/cloudvisor",
    )
    engine = create_async_engine(db_url)

    try:
        from app.models import create_connector_tables
        await create_connector_tables(engine)

        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name LIKE 'connector_%'"
                )
            )
            tables = [row[0] for row in result]

        assert "connector_cloud_accounts" in tables
        assert "connector_discovered_resources" in tables
    finally:
        await engine.dispose()
