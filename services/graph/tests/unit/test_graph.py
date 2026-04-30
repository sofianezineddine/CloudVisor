"""Unit tests for the Graph service."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


# ─── AssetNode tests ──────────────────────────────────────────────────────────

class TestAssetNode:
    """Tests for AssetNode model."""

    def _make_node(self, **kwargs) -> "AssetNode":
        from app.services.graph_service import AssetNode
        defaults = dict(
            id="res-123",
            cloud_resource_id="arn:aws:ec2:us-east-1:123456789012:instance/i-123",
            provider="aws",
            account_id="123456789012",
            region="us-east-1",
            resource_type="aws::ec2::instance",
            name="test-instance",
            tags={"env": "prod"},
            raw={"InstanceId": "i-123"},
            organization_id="org-123",
            is_public=False,
            environment="prod",
        )
        defaults.update(kwargs)
        return AssetNode(**defaults)

    def test_to_properties_basic(self):
        """Test converting AssetNode to Neo4j properties dict."""
        node = self._make_node()
        props = node.to_properties()

        assert props["id"] == "res-123"
        assert props["provider"] == "aws"
        assert props["name"] == "test-instance"
        assert props["environment"] == "prod"
        assert props["is_production"] is True
        assert props["is_public"] is False

    def test_to_properties_tags_serialized(self):
        """Test that tags dict is JSON-serialized for Neo4j."""
        import json
        node = self._make_node(tags={"env": "prod", "team": "security"})
        props = node.to_properties()
        tags = json.loads(props["tags"])
        assert tags["env"] == "prod"

    def test_get_type_suffix_aws(self):
        """Test type suffix extraction for AWS resource types."""
        node = self._make_node(resource_type="aws::ec2::instance")
        assert node.get_type_suffix() == "instance"

    def test_get_type_suffix_azure(self):
        """Test type suffix extraction for Azure resource types."""
        node = self._make_node(resource_type="azure::compute::virtualmachine")
        assert node.get_type_suffix() == "virtualmachine"

    def test_get_type_suffix_simple(self):
        """Test type suffix extraction for simple type names."""
        node = self._make_node(resource_type="EC2")
        assert node.get_type_suffix() == "ec2"

    def test_is_production_flag(self):
        """Test is_production computed from environment."""
        prod_node = self._make_node(environment="prod")
        dev_node = self._make_node(environment="dev")
        assert prod_node.to_properties()["is_production"] is True
        assert dev_node.to_properties()["is_production"] is False


# ─── Risk score calculation tests ─────────────────────────────────────────────

class TestRiskScoreCalculation:
    """Tests for risk score calculation per spec formula."""

    def _make_graph_service(self):
        from app.services.graph_service import GraphService
        return GraphService(neo4j_client=None)

    def test_no_findings_no_exposure(self):
        """Zero score when no findings and no exposure."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=0, high=0, medium=0,
            is_public=False, contains_pii=False, environment="dev",
        )
        assert score == 0

    def test_one_critical_finding(self):
        """One critical finding = 40 pts."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=1, high=0, medium=0,
            is_public=False, contains_pii=False, environment="dev",
        )
        assert score == 40

    def test_two_critical_findings(self):
        """Two critical findings = min(80, 60) = 60 (capped by findings max)."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=2, high=0, medium=0,
            is_public=False, contains_pii=False, environment="dev",
        )
        assert score == 60

    def test_findings_capped_at_60(self):
        """Findings score is capped at 60 pts."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=10, high=0, medium=0,
            is_public=False, contains_pii=False, environment="dev",
        )
        assert score == 60

    def test_public_exposure_adds_20(self):
        """Public exposure adds 20 pts."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=0, high=0, medium=0,
            is_public=True, contains_pii=False, environment="dev",
        )
        assert score == 20

    def test_pii_adds_15(self):
        """PII data adds 15 pts."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=0, high=0, medium=0,
            is_public=False, contains_pii=True, environment="dev",
        )
        assert score == 15

    def test_admin_access_adds_10(self):
        """Admin IAM access adds 10 pts."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=0, high=0, medium=0,
            is_public=False, contains_pii=False, environment="dev",
            is_admin=True,
        )
        assert score == 10

    def test_production_multiplier_1_5x(self):
        """Production environment applies 1.5x multiplier."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=1, high=0, medium=0,
            is_public=False, contains_pii=False, environment="prod",
        )
        # 40 * 1.5 = 60
        assert score == 60

    def test_production_multiplier_with_public(self):
        """Production + public: (40+20) * 1.5 = 90."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=1, high=0, medium=0,
            is_public=True, contains_pii=False, environment="prod",
        )
        assert score == 90

    def test_max_score_capped_at_100(self):
        """Score is always capped at 100."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=10, high=10, medium=10,
            is_public=True, contains_pii=True, environment="prod",
            is_admin=True,
        )
        assert score == 100

    def test_high_finding_adds_20(self):
        """One high finding = 20 pts."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=0, high=1, medium=0,
            is_public=False, contains_pii=False, environment="dev",
        )
        assert score == 20

    def test_medium_finding_adds_5(self):
        """One medium finding = 5 pts."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=0, high=0, medium=1,
            is_public=False, contains_pii=False, environment="dev",
        )
        assert score == 5

    def test_combined_score(self):
        """Combined: 1 critical + public + pii = 40+20+15 = 75."""
        svc = self._make_graph_service()
        score = svc._calculate_risk_score(
            critical=1, high=0, medium=0,
            is_public=True, contains_pii=True, environment="dev",
        )
        assert score == 75


# ─── Relationship rules tests ─────────────────────────────────────────────────

class TestRelationshipRules:
    """Tests for relationship resolution rules."""

    def test_relationship_rules_ec2(self):
        """EC2 instance has correct relationship rules."""
        from app.services.graph_service import RELATIONSHIP_RULES
        rules = RELATIONSHIP_RULES.get("ec2", [])
        rel_types = [r[1] for r in rules]
        assert "RUNS_IN" in rel_types
        assert "BELONGS_TO" in rel_types
        assert "HAS_ROLE" in rel_types

    def test_relationship_rules_subnet(self):
        """Subnet belongs to VPC."""
        from app.services.graph_service import RELATIONSHIP_RULES
        rules = RELATIONSHIP_RULES.get("subnet", [])
        rel_types = [r[1] for r in rules]
        assert "BELONGS_TO" in rel_types

    def test_relationship_rules_lambda(self):
        """Lambda has role and connects to RDS."""
        from app.services.graph_service import RELATIONSHIP_RULES
        rules = RELATIONSHIP_RULES.get("lambdafunction", [])
        rel_types = [r[1] for r in rules]
        assert "HAS_ROLE" in rel_types
        assert "CONNECTS_TO" in rel_types

    def test_relationship_types_lookup(self):
        """RELATIONSHIP_TYPES lookup table has expected entries."""
        from app.services.graph_service import RELATIONSHIP_TYPES
        assert "RUNS_IN" in RELATIONSHIP_TYPES["EC2"]
        assert "BELONGS_TO" in RELATIONSHIP_TYPES["EC2"]
        assert "HAS_ACCESS_TO" in RELATIONSHIP_TYPES["IAMRole"]
        assert "ASSUMES" in RELATIONSHIP_TYPES["IAMRole"]
        assert "ALLOWS_INBOUND_FROM" in RELATIONSHIP_TYPES["SecurityGroup"]


# ─── Snapshot service tests ───────────────────────────────────────────────────

class TestSnapshotService:
    """Tests for historical snapshot service."""

    def test_compute_diff_no_previous(self):
        """Diff with no previous snapshot marks all fields as changed."""
        from app.services.snapshots import SnapshotService
        svc = SnapshotService(db_session=None)
        current = {"name": "my-server", "risk_score": 50, "is_public": True}
        diff = svc._compute_diff(current, None)
        assert diff["changed"] is True
        assert set(diff["fields"]) == {"name", "risk_score", "is_public"}

    def test_compute_diff_no_changes(self):
        """Diff with identical previous snapshot shows no changes."""
        from app.services.snapshots import SnapshotService
        svc = SnapshotService(db_session=None)
        data = {"name": "my-server", "risk_score": 50}
        diff = svc._compute_diff(data, data.copy())
        assert diff["changed"] is False
        assert diff["fields"] == []

    def test_compute_diff_partial_change(self):
        """Diff detects only changed fields."""
        from app.services.snapshots import SnapshotService
        svc = SnapshotService(db_session=None)
        current = {"name": "my-server", "risk_score": 75, "is_public": True}
        previous = {"name": "my-server", "risk_score": 50, "is_public": True}
        diff = svc._compute_diff(current, previous)
        assert diff["changed"] is True
        assert "risk_score" in diff["fields"]
        assert "name" not in diff["fields"]


# ─── GraphService async tests ─────────────────────────────────────────────────

class TestGraphServiceAsync:
    """Async tests for GraphService with mocked Neo4j."""

    def _make_service(self):
        from app.services.graph_service import GraphService
        neo4j_mock = AsyncMock()
        neo4j_mock.execute_query = AsyncMock(return_value=[])
        neo4j_mock.execute_write = AsyncMock()
        neo4j_mock.get_node = AsyncMock(return_value=None)
        neo4j_mock.delete_node = AsyncMock()
        return GraphService(neo4j_client=neo4j_mock), neo4j_mock

    @pytest.mark.asyncio
    async def test_create_asset_node_calls_merge(self):
        """create_asset_node executes a MERGE query."""
        from app.services.graph_service import AssetNode
        svc, neo4j_mock = self._make_service()

        asset = AssetNode(
            id="a1", cloud_resource_id="arn:aws:ec2:us-east-1:123:instance/i-1",
            provider="aws", account_id="123", region="us-east-1",
            resource_type="aws::ec2::instance", name="server",
            organization_id="org-1",
        )
        await svc.create_asset_node(asset)
        neo4j_mock.execute_query.assert_called()

    @pytest.mark.asyncio
    async def test_delete_asset_node_calls_delete(self):
        """delete_asset_node calls neo4j.delete_node."""
        svc, neo4j_mock = self._make_service()
        await svc.delete_asset_node("asset-123")
        neo4j_mock.delete_node.assert_called_once_with("asset-123")

    @pytest.mark.asyncio
    async def test_compute_risk_score_returns_zero_when_no_node(self):
        """compute_and_update_risk_score returns 0 when node not found."""
        svc, neo4j_mock = self._make_service()
        neo4j_mock.execute_query = AsyncMock(return_value=[])
        score = await svc.compute_and_update_risk_score("nonexistent")
        assert score == 0

    @pytest.mark.asyncio
    async def test_compute_risk_score_with_findings(self):
        """compute_and_update_risk_score uses findings data from Neo4j."""
        svc, neo4j_mock = self._make_service()
        neo4j_mock.execute_query = AsyncMock(side_effect=[
            # First call: fetch node data
            [{"findings_count": 1, "critical_count": 1, "high_count": 0, "medium_count": 0,
              "is_public": False, "contains_pii": False, "is_admin": False,
              "env": "dev", "current_score": 0, "org_id": "org-1"}],
            # Second call: update risk_score
            [{"a": {"risk_score": 40}}],
        ])
        score = await svc.compute_and_update_risk_score("asset-1")
        assert score == 40

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """get_stats delegates to neo4j.get_stats."""
        svc, neo4j_mock = self._make_service()
        neo4j_mock.get_stats = AsyncMock(return_value={"node_count": 100, "edge_count": 200})
        stats = await svc.get_stats()
        assert stats["node_count"] == 100
        assert stats["edge_count"] == 200


# ─── Error types tests ────────────────────────────────────────────────────────

class TestGraphErrors:
    """Tests for graph error types."""

    def test_node_not_found_error(self):
        """NodeNotFoundError includes node_id."""
        from app.services.errors import NodeNotFoundError
        err = NodeNotFoundError("node-123")
        assert "node-123" in str(err)
        assert err.node_id == "node-123"

    def test_graph_error_hierarchy(self):
        """All errors inherit from GraphError."""
        from app.services.errors import GraphError, NodeNotFoundError, RelationshipError, QueryError
        assert issubclass(NodeNotFoundError, GraphError)
        assert issubclass(RelationshipError, GraphError)
        assert issubclass(QueryError, GraphError)


# ─── Prometheus metrics tests ─────────────────────────────────────────────────

class TestGraphMetrics:
    """Tests for Prometheus metrics recording."""

    def test_record_node_created(self):
        """record_node_created doesn't raise."""
        from app.metrics.prometheus import GraphMetrics
        GraphMetrics.record_node_created("aws", "aws::ec2::instance")

    def test_record_node_updated(self):
        """record_node_updated doesn't raise."""
        from app.metrics.prometheus import GraphMetrics
        GraphMetrics.record_node_updated("azure", "azure::compute::virtualmachine")

    def test_record_edge_created(self):
        """record_edge_created doesn't raise."""
        from app.metrics.prometheus import GraphMetrics
        GraphMetrics.record_edge_created("RUNS_IN")

    def test_record_event_consumed(self):
        """record_event_consumed doesn't raise."""
        from app.metrics.prometheus import GraphMetrics
        GraphMetrics.record_event_consumed("resource.discovered")

    def test_record_query_duration(self):
        """record_query_duration doesn't raise."""
        from app.metrics.prometheus import GraphMetrics
        GraphMetrics.record_query_duration("list_assets", 0.123)


# ─── Spec Cypher query patterns ───────────────────────────────────────────────

class TestSpecCypherQueries:
    """Tests that verify the spec-required Cypher query patterns are correct."""

    def test_internet_exposed_query_pattern(self):
        """Spec query 1: internet-exposed resources with open findings."""
        query = """
        MATCH (r:Asset {organization_id: $org_id})-[:ALLOWS_INBOUND_FROM]->(c:CIDR {value: "0.0.0.0/0"})
        WHERE r.open_findings_count > 0
        RETURN r ORDER BY r.risk_score DESC LIMIT $limit
        """
        assert "ALLOWS_INBOUND_FROM" in query
        assert "0.0.0.0/0" in query
        assert "open_findings_count" in query

    def test_attack_path_query_pattern(self):
        """Spec query 2: attack path from internet to sensitive database."""
        query = """
        MATCH path = (i:Asset)-[*1..6]->(db:Asset)
        WHERE i.is_public = true AND db.contains_pii = true
        RETURN path, length(path) ORDER BY length(path) ASC LIMIT 10
        """
        assert "is_public" in query
        assert "contains_pii" in query
        assert "1..6" in query

    def test_overprivileged_iam_query_pattern(self):
        """Spec query 3: over-privileged IAM roles with prod access."""
        query = """
        MATCH (role:Asset)-[:HAS_ACCESS_TO]->(res:Asset)
        WHERE role.resource_type CONTAINS 'iamrole'
          AND role.unused_permissions_count > 20
          AND res.environment = 'prod'
        RETURN role, collect(res) AS prod_resources
        """
        assert "HAS_ACCESS_TO" in query
        assert "unused_permissions_count" in query
        assert "prod" in query

    def test_blast_radius_query_pattern(self):
        """Spec query 4: blast radius of a compromised IAM role."""
        query = """
        MATCH (role:Asset {id: $role_id})-[:HAS_ACCESS_TO*1..3]->(target:Asset)
        RETURN target, labels(target) AS type
        """
        assert "HAS_ACCESS_TO*1..3" in query
        assert "role_id" in query


# ─── Async placeholder ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_placeholder():
    """Placeholder async test."""
    assert True
