"""GraphQL schema for the Asset Graph service.

Spec §3.2: "Expose a GraphQL endpoint for flexible, nested graph queries.
Support relationship traversal in GraphQL: asset { relatedAssets { findings } }"

This module defines the Strawberry GraphQL schema that wraps the existing
GraphService and Neo4j queries. It's mounted at /graphql in main.py.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import strawberry
from strawberry.types import Info

logger = logging.getLogger(__name__)


# ─── GraphQL Types ────────────────────────────────────────────────────────────

@strawberry.type
class AssetType:
    """A cloud resource node in the asset graph."""
    id: str
    cloud_resource_id: str
    provider: str
    account_id: str
    region: str
    resource_type: str
    name: str
    tags: strawberry.scalars.JSON
    environment: str
    is_public: bool
    risk_score: int
    open_findings_count: int
    last_seen_at: str

    @strawberry.field
    async def related_assets(
        self,
        info: Info,
        depth: int = 1,
        relationship_type: Optional[str] = None,
    ) -> list[RelatedAssetType]:
        """Traverse the graph to get related assets (spec: nested traversal)."""
        neo4j = info.context["neo4j"]
        if not neo4j:
            return []

        if relationship_type:
            query = f"""
            MATCH (a:Asset {{id: $id}})-[r:{relationship_type}]-(related:Asset)
            RETURN related, type(r) AS rel_type
            LIMIT 50
            """
        elif depth > 1:
            query = f"""
            MATCH p = (a:Asset {{id: $id}})-[rels*1..{depth}]-(related:Asset)
            WHERE related.id <> $id
            RETURN related, type(last(rels)) AS rel_type
            LIMIT 100
            """
        else:
            query = """
            MATCH (a:Asset {id: $id})-[r]-(related:Asset)
            RETURN related, type(r) AS rel_type
            LIMIT 50
            """

        results = await neo4j.execute_query(query, {"id": self.id})
        seen: set[str] = set()
        related: list[RelatedAssetType] = []
        for record in results:
            node = record.get("related", {})
            rid = node.get("id", "")
            if rid and rid not in seen:
                seen.add(rid)
                related.append(RelatedAssetType(
                    id=rid,
                    name=node.get("name", ""),
                    resource_type=node.get("resource_type", ""),
                    relationship_type=record.get("rel_type", "RELATED"),
                    risk_score=int(node.get("risk_score", 0) or 0),
                    provider=node.get("provider", ""),
                ))
        return related

    @strawberry.field
    async def findings(self, info: Info) -> list[FindingType]:
        """Get open findings linked to this asset."""
        neo4j = info.context["neo4j"]
        if not neo4j:
            return []

        query = """
        MATCH (a:Asset {id: $id})-[:HAS_FINDING]->(f:Finding)
        RETURN f
        ORDER BY f.severity DESC
        LIMIT 100
        """
        results = await neo4j.execute_query(query, {"id": self.id})
        return [
            FindingType(
                id=r.get("f", {}).get("id", ""),
                title=r.get("f", {}).get("title", ""),
                severity=r.get("f", {}).get("severity", "UNKNOWN"),
                status=r.get("f", {}).get("status", "open"),
                rule_id=r.get("f", {}).get("rule_id", ""),
            )
            for r in results
        ]

    @strawberry.field
    async def attack_paths(
        self, info: Info, max_hops: int = 6
    ) -> list[AttackPathType]:
        """Compute attack paths from/to this asset."""
        neo4j = info.context["neo4j"]
        if not neo4j:
            return []

        query = f"""
        MATCH path = (entry:Asset {{id: $id}})-[*1..{max_hops}]->(target:Asset)
        WHERE target.risk_score > 50 AND target.id <> $id
        WITH path, target, length(path) AS hops
        RETURN [n IN nodes(path) | {{
            id: n.id, name: n.name, resource_type: n.resource_type, risk_score: n.risk_score
        }}] AS path_nodes, hops
        ORDER BY hops ASC
        LIMIT 10
        """
        results = await neo4j.execute_query(query, {"id": self.id})
        return [
            AttackPathType(
                nodes=[
                    AttackPathNodeType(**n) for n in r.get("path_nodes", [])
                ],
                length=r.get("hops", 0),
            )
            for r in results
        ]


@strawberry.type
class RelatedAssetType:
    """A related asset in the graph."""
    id: str
    name: str
    resource_type: str
    relationship_type: str
    risk_score: int
    provider: str = ""


@strawberry.type
class FindingType:
    """A security finding linked to an asset."""
    id: str
    title: str
    severity: str
    status: str
    rule_id: str


@strawberry.type
class AttackPathNodeType:
    """A node in an attack path."""
    id: str
    name: str
    resource_type: str
    risk_score: int


@strawberry.type
class AttackPathType:
    """An attack path through the graph."""
    nodes: list[AttackPathNodeType]
    length: int


@strawberry.type
class GraphStatsType:
    """Graph statistics."""
    node_count: int
    edge_count: int
    by_provider: strawberry.scalars.JSON
    by_type: strawberry.scalars.JSON


# ─── Query Root ───────────────────────────────────────────────────────────────

@strawberry.type
class Query:
    """Root GraphQL query type for the Asset Graph."""

    @strawberry.field
    async def asset(self, info: Info, id: str) -> Optional[AssetType]:
        """Get a single asset by ID."""
        neo4j = info.context["neo4j"]
        if not neo4j:
            return None

        query = "MATCH (a:Asset {id: $id}) RETURN a"
        results = await neo4j.execute_query(query, {"id": id})
        if not results:
            return None

        node = results[0]["a"]
        return _node_to_asset_type(node)

    @strawberry.field
    async def assets(
        self,
        info: Info,
        org_id: str,
        provider: Optional[str] = None,
        resource_type: Optional[str] = None,
        region: Optional[str] = None,
        environment: Optional[str] = None,
        is_public: Optional[bool] = None,
        risk_score_min: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AssetType]:
        """List assets with filtering."""
        neo4j = info.context["neo4j"]
        if not neo4j:
            return []

        conditions = ["a.organization_id = $org_id"]
        params: dict[str, Any] = {"org_id": org_id, "skip": offset, "limit": limit}

        if provider:
            conditions.append("a.provider = $provider")
            params["provider"] = provider
        if resource_type:
            conditions.append("a.resource_type CONTAINS $resource_type")
            params["resource_type"] = resource_type
        if region:
            conditions.append("a.region = $region")
            params["region"] = region
        if environment:
            conditions.append("a.environment = $environment")
            params["environment"] = environment
        if is_public is not None:
            conditions.append("a.is_public = $is_public")
            params["is_public"] = is_public
        if risk_score_min is not None:
            conditions.append("a.risk_score >= $risk_score_min")
            params["risk_score_min"] = risk_score_min

        where = " AND ".join(conditions)
        query = f"""
        MATCH (a:Asset) WHERE {where}
        RETURN a ORDER BY a.risk_score DESC
        SKIP $skip LIMIT $limit
        """
        results = await neo4j.execute_query(query, params)
        return [_node_to_asset_type(r["a"]) for r in results]

    @strawberry.field
    async def graph_stats(self, info: Info, org_id: str) -> GraphStatsType:
        """Get graph statistics."""
        neo4j = info.context["neo4j"]
        if not neo4j:
            return GraphStatsType(node_count=0, edge_count=0, by_provider={}, by_type={})

        from ..services.graph_service import GraphService
        redis = info.context.get("redis")
        svc = GraphService(neo4j, redis_client=redis)

        stats = await svc.get_stats()
        by_provider = await svc.get_asset_counts_by_provider(org_id)
        by_type = await svc.get_asset_counts_by_type(org_id)

        return GraphStatsType(
            node_count=stats.get("node_count", 0),
            edge_count=stats.get("edge_count", 0),
            by_provider=by_provider,
            by_type=by_type,
        )

    @strawberry.field
    async def attack_paths(
        self,
        info: Info,
        org_id: str,
        max_hops: int = 6,
    ) -> list[AttackPathType]:
        """Find attack paths from internet-exposed to high-risk assets."""
        neo4j = info.context["neo4j"]
        if not neo4j:
            return []

        query = f"""
        MATCH path = (entry:Asset)-[*1..{max_hops}]->(target:Asset)
        WHERE entry.organization_id = $org_id
          AND entry.is_public = true
          AND target.risk_score > 50
          AND entry.id <> target.id
        WITH path, target, length(path) AS hops
        RETURN [n IN nodes(path) | {{
            id: n.id, name: n.name, resource_type: n.resource_type, risk_score: n.risk_score
        }}] AS path_nodes, hops
        ORDER BY target.risk_score DESC, hops ASC
        LIMIT 10
        """
        results = await neo4j.execute_query(query, {"org_id": org_id})
        return [
            AttackPathType(
                nodes=[AttackPathNodeType(**n) for n in r.get("path_nodes", [])],
                length=r.get("hops", 0),
            )
            for r in results
        ]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _node_to_asset_type(node: dict[str, Any]) -> AssetType:
    """Convert a Neo4j node dict to an AssetType."""
    tags = node.get("tags", "{}")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = {}

    return AssetType(
        id=node.get("id", ""),
        cloud_resource_id=node.get("cloud_resource_id", ""),
        provider=node.get("provider", ""),
        account_id=node.get("account_id", ""),
        region=node.get("region", ""),
        resource_type=node.get("resource_type", ""),
        name=node.get("name", ""),
        tags=tags,
        environment=node.get("environment", "unknown"),
        is_public=bool(node.get("is_public", False)),
        risk_score=int(node.get("risk_score", 0) or 0),
        open_findings_count=int(node.get("open_findings_count", 0) or 0),
        last_seen_at=node.get("last_seen_at", ""),
    )


# ─── Schema ───────────────────────────────────────────────────────────────────

schema = strawberry.Schema(query=Query)
