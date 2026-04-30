"""Integration tests for the Graph service.

Requires running Docker Compose stack:
  docker compose up -d postgres neo4j elasticsearch kafka redis

Run with:
  INTEGRATION_TESTS=1 pytest tests/integration/ -v --timeout=60
"""

import os
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("INTEGRATION_TESTS") != "1",
    reason="Set INTEGRATION_TESTS=1 to run integration tests",
)


@pytest.mark.asyncio
async def test_neo4j_connection():
    """Test Neo4j connection and basic query."""
    from app.clients.neo4j import Neo4jClient

    client = Neo4jClient(
        uri=os.getenv("GRAPH_NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("GRAPH_NEO4J_USER", "neo4j"),
        password=os.getenv("GRAPH_NEO4J_PASSWORD", "password"),
    )
    await client.connect()
    try:
        result = await client.execute_query("RETURN 1 AS n")
        assert result[0]["n"] == 1
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_elasticsearch_connection():
    """Test Elasticsearch connection and index creation."""
    from app.clients.elasticsearch import ElasticsearchClient, ASSET_MAPPINGS

    client = ElasticsearchClient(
        url=os.getenv("GRAPH_ELASTICSEARCH_URL", "http://localhost:9200"),
        index_prefix="test-cloudvisor",
    )
    await client.connect()
    try:
        await client.create_index("assets", ASSET_MAPPINGS)
        stats = await client.get_stats()
        assert "indices" in stats or "status" in stats
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_asset_node_create_and_query():
    """Test creating an asset node and querying it back."""
    from app.clients.neo4j import Neo4jClient
    from app.services.graph_service import GraphService, AssetNode
    import uuid

    client = Neo4jClient(
        uri=os.getenv("GRAPH_NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("GRAPH_NEO4J_USER", "neo4j"),
        password=os.getenv("GRAPH_NEO4J_PASSWORD", "password"),
    )
    await client.connect()

    try:
        svc = GraphService(neo4j_client=client)
        asset_id = f"test-{uuid.uuid4().hex[:8]}"

        asset = AssetNode(
            id=asset_id,
            cloud_resource_id=f"arn:aws:ec2:us-east-1:123:instance/{asset_id}",
            provider="aws",
            account_id="123456789012",
            region="us-east-1",
            resource_type="aws::ec2::instance",
            name="integration-test-server",
            organization_id="test-org",
            is_public=False,
            environment="dev",
        )

        await svc.create_asset_node(asset)

        # Query it back
        result = await client.execute_query(
            "MATCH (a:Asset {id: $id}) RETURN a", {"id": asset_id}
        )
        assert result, "Asset node should exist"
        assert result[0]["a"]["name"] == "integration-test-server"

        # Clean up
        await client.delete_node(asset_id)
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_risk_score_computation():
    """Test risk score computation and update."""
    from app.clients.neo4j import Neo4jClient
    from app.services.graph_service import GraphService, AssetNode
    import uuid

    client = Neo4jClient(
        uri=os.getenv("GRAPH_NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("GRAPH_NEO4J_USER", "neo4j"),
        password=os.getenv("GRAPH_NEO4J_PASSWORD", "password"),
    )
    await client.connect()

    try:
        svc = GraphService(neo4j_client=client)
        asset_id = f"test-risk-{uuid.uuid4().hex[:8]}"

        asset = AssetNode(
            id=asset_id,
            cloud_resource_id=f"arn:aws:s3:::test-bucket-{asset_id}",
            provider="aws",
            account_id="123456789012",
            region="global",
            resource_type="aws::s3bucket",
            name="test-bucket",
            organization_id="test-org",
            is_public=True,
            contains_pii=True,
            environment="prod",
        )

        await svc.create_asset_node(asset)

        # Set findings count
        await client.execute_write(
            "MATCH (a:Asset {id: $id}) SET a.critical_count = 1",
            {"id": asset_id},
        )

        score = await svc.compute_and_update_risk_score(asset_id)
        # 1 critical (40) + public (20) + pii (15) = 75 * 1.5 (prod) = 112 → capped at 100
        assert score == 100

        # Clean up
        await client.delete_node(asset_id)
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_snapshot_table_creation():
    """Test that snapshot tables are created in PostgreSQL."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    from app.services.snapshots import SnapshotBase

    db_url = os.getenv(
        "DB_URL",
        "postgresql+asyncpg://cvadmin:cvpassword@localhost:5432/cloudvisor",
    )
    engine = create_async_engine(db_url)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(SnapshotBase.metadata.create_all)

        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN ('asset_snapshots', 'relationship_snapshots')"
                )
            )
            tables = [row[0] for row in result]

        assert "asset_snapshots" in tables
        assert "relationship_snapshots" in tables
    finally:
        await engine.dispose()
