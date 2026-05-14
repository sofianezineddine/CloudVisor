"""Unit tests for Attack Path Engine business logic."""

import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from app.services.attack_path_engine import (
    assign_path_severity,
    compute_blast_radius,
    detect_lateral_movement,
    discover_attack_paths,
    map_to_mitre_attack,
    MITRE_ATTACK_MAPPING,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    _build_path_edges,
)


# ─── assign_path_severity ─────────────────────────────────────────────────────


class TestAssignPathSeverity:
    """Tests for assign_path_severity."""

    def test_one_hop_is_critical(self):
        assert assign_path_severity(1) == SEVERITY_CRITICAL

    def test_two_hops_is_critical(self):
        assert assign_path_severity(2) == SEVERITY_CRITICAL

    def test_three_hops_is_critical(self):
        """Exactly at the critical threshold (default 3) should be CRITICAL."""
        assert assign_path_severity(3) == SEVERITY_CRITICAL

    def test_four_hops_is_high(self):
        """One hop above critical threshold should be HIGH."""
        assert assign_path_severity(4) == SEVERITY_HIGH

    def test_five_hops_is_medium(self):
        assert assign_path_severity(5) == SEVERITY_MEDIUM

    def test_six_hops_is_medium(self):
        """At max_hops (default 6) should be MEDIUM."""
        assert assign_path_severity(6) == SEVERITY_MEDIUM

    def test_seven_hops_is_low(self):
        """Beyond max_hops should be LOW."""
        assert assign_path_severity(7) == SEVERITY_LOW

    def test_zero_hops_is_critical(self):
        """Zero hops (same resource) should be CRITICAL."""
        assert assign_path_severity(0) == SEVERITY_CRITICAL


# ─── map_to_mitre_attack ──────────────────────────────────────────────────────


class TestMapToMitreAttack:
    """Tests for map_to_mitre_attack."""

    def test_public_facing_application_maps_to_t1190(self):
        resource_types = ["load_balancer", "ec2_instance", "rds_instance"]
        rel_types = ["CONNECTS_TO", "HAS_ACCESS"]
        result = map_to_mitre_attack(resource_types, rel_types)
        assert result is not None
        assert result["id"] == "T1190"
        assert result["name"] == "Exploit Public-Facing Application"

    def test_credential_based_access_maps_to_t1078(self):
        """HAS_ACCESS without IAM resources in path maps to T1078."""
        resource_types = ["ec2_instance", "lambda_function"]
        rel_types = ["HAS_ACCESS"]
        result = map_to_mitre_attack(resource_types, rel_types)
        assert result is not None
        assert result["id"] == "T1078"

    def test_cloud_storage_maps_to_t1530(self):
        resource_types = ["ec2_instance", "s3_bucket"]
        rel_types = ["CONNECTS_TO"]
        result = map_to_mitre_attack(resource_types, rel_types)
        assert result is not None
        assert result["id"] == "T1530"

    def test_unsecured_credentials_maps_to_t1552(self):
        resource_types = ["ec2_instance", "secrets_manager"]
        rel_types = ["CONNECTS_TO"]
        result = map_to_mitre_attack(resource_types, rel_types)
        assert result is not None
        assert result["id"] == "T1552"

    def test_trust_with_storage_maps_to_t1537(self):
        resource_types = ["iam_role", "s3_bucket"]
        rel_types = ["TRUSTS"]
        result = map_to_mitre_attack(resource_types, rel_types)
        assert result is not None
        assert result["id"] == "T1537"

    def test_iam_access_maps_to_t1098(self):
        """Path with IAM resources and HAS_ACCESS maps to T1098."""
        resource_types = ["ec2_instance", "iam_role"]
        rel_types = ["HAS_ACCESS"]
        result = map_to_mitre_attack(resource_types, rel_types)
        assert result is not None
        assert result["id"] == "T1098"

    def test_no_match_returns_none(self):
        resource_types = ["unknown_type"]
        rel_types = ["UNKNOWN_REL"]
        result = map_to_mitre_attack(resource_types, rel_types)
        assert result is None

    def test_empty_inputs_returns_none(self):
        result = map_to_mitre_attack([], [])
        assert result is None


# ─── _build_path_edges ────────────────────────────────────────────────────────


class TestBuildPathEdges:
    """Tests for _build_path_edges helper."""

    def test_simple_path(self):
        node_ids = ["a", "b", "c"]
        rel_types = ["CONNECTS_TO", "HAS_ACCESS"]
        edges = _build_path_edges(node_ids, rel_types)
        assert edges == [
            {"from": "a", "to": "b", "relationship_type": "CONNECTS_TO"},
            {"from": "b", "to": "c", "relationship_type": "HAS_ACCESS"},
        ]

    def test_single_edge(self):
        node_ids = ["a", "b"]
        rel_types = ["TRUSTS"]
        edges = _build_path_edges(node_ids, rel_types)
        assert edges == [{"from": "a", "to": "b", "relationship_type": "TRUSTS"}]

    def test_empty_nodes(self):
        edges = _build_path_edges([], [])
        assert edges == []

    def test_single_node_no_edges(self):
        edges = _build_path_edges(["a"], [])
        assert edges == []

    def test_missing_relationship_types_uses_unknown(self):
        node_ids = ["a", "b", "c"]
        rel_types = ["CONNECTS_TO"]  # Only one rel type for two edges
        edges = _build_path_edges(node_ids, rel_types)
        assert edges[0]["relationship_type"] == "CONNECTS_TO"
        assert edges[1]["relationship_type"] == "UNKNOWN"


# ─── discover_attack_paths ────────────────────────────────────────────────────


class TestDiscoverAttackPaths:
    """Tests for discover_attack_paths (async, uses mocked graph client)."""

    @pytest.mark.asyncio
    async def test_discovers_paths_from_graph(self):
        mock_client = AsyncMock()
        mock_client.query.return_value = [
            {
                "hops": 2,
                "node_ids": ["entry-1", "middle-1", "sensitive-1"],
                "resource_types": ["load_balancer", "ec2_instance", "rds_instance"],
                "relationship_types": ["CONNECTS_TO", "HAS_ACCESS"],
                "entry_id": "entry-1",
                "sensitive_id": "sensitive-1",
            }
        ]

        paths = await discover_attack_paths(mock_client, "org-123")

        assert len(paths) == 1
        path = paths[0]
        assert path["entry_resource_id"] == "entry-1"
        assert path["target_resource_id"] == "sensitive-1"
        assert path["path_hops"] == 2
        assert path["severity"] == SEVERITY_CRITICAL
        assert path["organization_id"] == "org-123"
        assert path["mitre_technique_id"] == "T1190"

    @pytest.mark.asyncio
    async def test_deduplicates_paths_by_entry_target(self):
        mock_client = AsyncMock()
        mock_client.query.return_value = [
            {
                "hops": 2,
                "node_ids": ["entry-1", "mid", "sensitive-1"],
                "resource_types": ["api_gateway", "lambda", "s3_bucket"],
                "relationship_types": ["CONNECTS_TO", "HAS_ACCESS"],
                "entry_id": "entry-1",
                "sensitive_id": "sensitive-1",
            },
            {
                "hops": 3,
                "node_ids": ["entry-1", "mid1", "mid2", "sensitive-1"],
                "resource_types": ["api_gateway", "ec2", "lambda", "s3_bucket"],
                "relationship_types": ["CONNECTS_TO", "CONNECTS_TO", "HAS_ACCESS"],
                "entry_id": "entry-1",
                "sensitive_id": "sensitive-1",
            },
        ]

        paths = await discover_attack_paths(mock_client, "org-123")
        # Should deduplicate — same entry+target pair
        assert len(paths) == 1

    @pytest.mark.asyncio
    async def test_empty_results(self):
        mock_client = AsyncMock()
        mock_client.query.return_value = []

        paths = await discover_attack_paths(mock_client, "org-123")
        assert paths == []

    @pytest.mark.asyncio
    async def test_respects_max_hops_parameter(self):
        mock_client = AsyncMock()
        mock_client.query.return_value = []

        await discover_attack_paths(mock_client, "org-123", max_hops=4)

        # Verify the query was called with max_hops embedded
        call_args = mock_client.query.call_args
        cypher = call_args.kwargs.get("cypher") or call_args[1].get("cypher", call_args[0][0] if call_args[0] else "")
        assert "..4" in cypher


# ─── compute_blast_radius ─────────────────────────────────────────────────────


class TestComputeBlastRadius:
    """Tests for compute_blast_radius (async, uses mocked graph client)."""

    @pytest.mark.asyncio
    async def test_computes_blast_radius(self):
        mock_client = AsyncMock()
        mock_client.query.return_value = [
            {
                "blast_radius_ids": ["res-2", "res-3", "res-4"],
                "blast_radius_types": ["ec2_instance", "s3_bucket", "rds_instance"],
            }
        ]

        result = await compute_blast_radius(mock_client, "res-1", "org-123")

        assert result["resource_id"] == "res-1"
        assert result["blast_radius_count"] == 3
        assert set(result["reachable_resources"]) == {"res-2", "res-3", "res-4"}
        assert len(result["reachable_resource_types"]) == 3

    @pytest.mark.asyncio
    async def test_excludes_source_from_blast_radius(self):
        mock_client = AsyncMock()
        mock_client.query.return_value = [
            {
                "blast_radius_ids": ["res-1", "res-2", "res-3"],
                "blast_radius_types": ["ec2_instance", "s3_bucket"],
            }
        ]

        result = await compute_blast_radius(mock_client, "res-1", "org-123")

        # Source resource should be excluded
        assert "res-1" not in result["reachable_resources"]
        assert result["blast_radius_count"] == 2

    @pytest.mark.asyncio
    async def test_empty_blast_radius(self):
        mock_client = AsyncMock()
        mock_client.query.return_value = [
            {
                "blast_radius_ids": [],
                "blast_radius_types": [],
            }
        ]

        result = await compute_blast_radius(mock_client, "res-1", "org-123")

        assert result["blast_radius_count"] == 0
        assert result["reachable_resources"] == []

    @pytest.mark.asyncio
    async def test_no_records_returns_empty(self):
        mock_client = AsyncMock()
        mock_client.query.return_value = []

        result = await compute_blast_radius(mock_client, "res-1", "org-123")

        assert result["blast_radius_count"] == 0
        assert result["reachable_resources"] == []


# ─── detect_lateral_movement ──────────────────────────────────────────────────


class TestDetectLateralMovement:
    """Tests for detect_lateral_movement (async, uses mocked graph client)."""

    @pytest.mark.asyncio
    async def test_detects_shared_credentials(self):
        mock_client = AsyncMock()
        # First query (shared creds) returns results, others empty
        mock_client.query.side_effect = [
            [{"source_id": "res-1", "target_id": "res-2", "credential_id": "cred-1"}],
            [],  # permissive SGs
            [],  # instance profiles
        ]

        results = await detect_lateral_movement(mock_client, "org-123")

        assert len(results) == 1
        assert results[0]["movement_type"] == "shared_credentials"
        assert results[0]["source_id"] == "res-1"
        assert results[0]["target_id"] == "res-2"
        assert results[0]["severity"] == SEVERITY_HIGH

    @pytest.mark.asyncio
    async def test_detects_permissive_security_groups(self):
        mock_client = AsyncMock()
        mock_client.query.side_effect = [
            [],  # shared creds
            [{"source_id": "res-1", "target_id": "res-2", "security_group_id": "sg-1"}],
            [],  # instance profiles
        ]

        results = await detect_lateral_movement(mock_client, "org-123")

        assert len(results) == 1
        assert results[0]["movement_type"] == "permissive_security_group"

    @pytest.mark.asyncio
    async def test_detects_instance_profile_chains(self):
        mock_client = AsyncMock()
        mock_client.query.side_effect = [
            [],  # shared creds
            [],  # permissive SGs
            [{"source_id": "inst-1", "target_id": "res-1", "profile_id": "prof-1", "role_id": "role-1"}],
        ]

        results = await detect_lateral_movement(mock_client, "org-123")

        assert len(results) == 1
        assert results[0]["movement_type"] == "instance_profile_chain"

    @pytest.mark.asyncio
    async def test_combines_all_movement_types(self):
        mock_client = AsyncMock()
        mock_client.query.side_effect = [
            [{"source_id": "r1", "target_id": "r2", "credential_id": "c1"}],
            [{"source_id": "r3", "target_id": "r4", "security_group_id": "sg1"}],
            [{"source_id": "r5", "target_id": "r6", "profile_id": "p1", "role_id": "role1"}],
        ]

        results = await detect_lateral_movement(mock_client, "org-123")

        assert len(results) == 3
        movement_types = {r["movement_type"] for r in results}
        assert movement_types == {"shared_credentials", "permissive_security_group", "instance_profile_chain"}

    @pytest.mark.asyncio
    async def test_handles_query_failures_gracefully(self):
        """If one query fails, others should still be processed."""
        from app.core.graph_client import GraphClientError

        mock_client = AsyncMock()
        mock_client.query.side_effect = [
            GraphClientError("Connection failed"),  # shared creds fails
            [{"source_id": "r1", "target_id": "r2", "security_group_id": "sg1"}],
            [],  # instance profiles
        ]

        results = await detect_lateral_movement(mock_client, "org-123")

        # Should still return results from successful queries
        assert len(results) == 1
        assert results[0]["movement_type"] == "permissive_security_group"

    @pytest.mark.asyncio
    async def test_no_lateral_movement(self):
        mock_client = AsyncMock()
        mock_client.query.side_effect = [[], [], []]

        results = await detect_lateral_movement(mock_client, "org-123")
        assert results == []
