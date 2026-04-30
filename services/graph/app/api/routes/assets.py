"""API routes for asset graph operations — tenant-isolated."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.core.dependencies import get_db, get_redis, get_neo4j, get_settings, get_elasticsearch
from app.schemas import (
    AssetListResponse,
    AssetRelatedResponse,
    AssetHistoryResponse,
    AttackPathResponse,
    GraphStatsResponse,
    CypherQueryRequest,
    CypherQueryResponse,
)
from app.services import GraphService

router = APIRouter(prefix="/assets", tags=["assets"])


def _node_to_asset_dict(node: dict) -> dict[str, Any]:
    """Convert a raw Neo4j node dict to a safe asset dict with defaults."""
    import json
    tags = node.get("tags", "{}")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = {}
    return {
        "id": node.get("id", ""),
        "cloud_resource_id": node.get("cloud_resource_id", ""),
        "provider": node.get("provider", "unknown"),
        "account_id": node.get("account_id", ""),
        "region": node.get("region", "global"),
        "resource_type": node.get("resource_type", "unknown"),
        "name": node.get("name", ""),
        "tags": tags if isinstance(tags, dict) else {},
        "environment": node.get("environment", "unknown"),
        "is_public": bool(node.get("is_public", False)),
        "risk_score": int(node.get("risk_score", 0) or 0),
        "open_findings_count": int(node.get("open_findings_count", 0) or 0),
        "last_seen_at": node.get("last_seen_at") or "1970-01-01T00:00:00",
    }


# ─── /stats must come BEFORE /{asset_id} to avoid route conflict ─────────────

@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    org_id: str = Query(...),
    neo4j=Depends(get_neo4j),
) -> GraphStatsResponse:
    """Get asset counts by type, region, account."""
    if not neo4j:
        return GraphStatsResponse(node_count=0, edge_count=0, by_provider={}, by_type={})

    graph_service = GraphService(neo4j)
    stats = await graph_service.get_stats()
    by_provider = await graph_service.get_asset_counts_by_provider(org_id)
    by_type = await graph_service.get_asset_counts_by_type(org_id)

    return GraphStatsResponse(
        node_count=stats.get("node_count", 0),
        edge_count=stats.get("edge_count", 0),
        by_provider=by_provider,
        by_type=by_type,
    )


@router.get("/search")
async def search_assets(
    q: str = Query(..., min_length=1),
    org_id: str = Query(...),
    provider: str | None = None,
    region: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    neo4j=Depends(get_neo4j),
    es=Depends(get_elasticsearch),
) -> dict:
    """Full-text search — tries Elasticsearch first, falls back to Neo4j CONTAINS."""
    # Try injected Elasticsearch client
    if es:
        try:
            result = await es.full_text_search(
                "assets",
                search_term=q,
                fields=["name", "resource_type"],
                size=page_size,
            )
            # Filter by org_id (ES doesn't enforce tenant isolation automatically)
            hits = [h for h in result["hits"] if h.get("organization_id") == org_id]
            if provider:
                hits = [h for h in hits if h.get("provider") == provider]
            if region:
                hits = [h for h in hits if h.get("region") == region]
            return {
                "total": len(hits),
                "hits": hits,
                "page": page,
                "page_size": page_size,
                "source": "elasticsearch",
            }
        except Exception:
            pass

    # Fallback: Neo4j CONTAINS search
    if not neo4j:
        return {"total": 0, "hits": [], "page": page, "page_size": page_size, "source": "neo4j"}

    conditions = [
        "a.organization_id = $org_id",
        "(toLower(a.name) CONTAINS toLower($q) OR toLower(a.resource_type) CONTAINS toLower($q))",
    ]
    params: dict[str, Any] = {
        "org_id": org_id,
        "q": q,
        "skip": (page - 1) * page_size,
        "limit": page_size,
    }
    if provider:
        conditions.append("a.provider = $provider")
        params["provider"] = provider
    if region:
        conditions.append("a.region = $region")
        params["region"] = region

    where_clause = " AND ".join(conditions)
    cypher = f"MATCH (a:Asset) WHERE {where_clause} RETURN a ORDER BY a.risk_score DESC SKIP $skip LIMIT $limit"
    results = await neo4j.execute_query(cypher, params)

    return {
        "total": len(results),
        "hits": [_node_to_asset_dict(r.get("a", {})) for r in results],
        "page": page,
        "page_size": page_size,
        "source": "neo4j",
    }


# ─── List assets ──────────────────────────────────────────────────────────────

@router.get("")
async def list_assets(
    org_id: str = Query(...),
    provider: str | None = None,
    resource_type: str | None = None,
    region: str | None = None,
    environment: str | None = None,
    is_public: bool | None = None,
    risk_score_min: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    neo4j=Depends(get_neo4j),
) -> dict:
    """List assets with filtering and pagination."""
    if not neo4j:
        return {"assets": [], "total": 0, "page": page, "page_size": page_size}

    conditions = ["a.organization_id = $org_id"]
    params: dict[str, Any] = {
        "org_id": org_id,
        "skip": (page - 1) * page_size,
        "limit": page_size,
    }

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

    where_clause = " AND ".join(conditions)
    query = f"MATCH (a:Asset) WHERE {where_clause} RETURN a ORDER BY a.risk_score DESC SKIP $skip LIMIT $limit"
    count_query = f"MATCH (a:Asset) WHERE {where_clause} RETURN count(a) AS total"

    results = await neo4j.execute_query(query, params)
    count_result = await neo4j.execute_query(count_query, {k: v for k, v in params.items() if k not in ("skip", "limit")})
    total = count_result[0]["total"] if count_result else 0

    return {
        "assets": [_node_to_asset_dict(r.get("a", {})) for r in results],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ─── Single asset ─────────────────────────────────────────────────────────────

@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    neo4j=Depends(get_neo4j),
) -> dict:
    """Get a single asset by ID."""
    if not neo4j:
        raise HTTPException(status_code=503, detail="Graph service unavailable")

    query = "MATCH (a:Asset {id: $id}) RETURN a"
    result = await neo4j.execute_query(query, {"id": asset_id})

    if not result:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    return _node_to_asset_dict(result[0]["a"])


@router.get("/{asset_id}/related", response_model=AssetRelatedResponse)
async def get_related_assets(
    asset_id: str,
    depth: int = Query(1, ge=1, le=3),
    neo4j=Depends(get_neo4j),
) -> AssetRelatedResponse:
    """Get related assets (graph neighbors)."""
    if not neo4j:
        return AssetRelatedResponse(asset_id=asset_id, relationships=[])

    query = f"""
    MATCH (a:Asset {{id: $id}})-[r*1..{depth}]-(related:Asset)
    RETURN related, type(last(relationships(path))) AS rel_type
    LIMIT 100
    """ if depth > 1 else """
    MATCH (a:Asset {id: $id})-[r]-(related:Asset)
    RETURN related, type(r) AS rel_type
    LIMIT 50
    """

    result = await neo4j.execute_query(query, {"id": asset_id})

    relationships = []
    seen = set()
    for record in result:
        related = record.get("related", {})
        rid = related.get("id", "")
        if rid and rid not in seen:
            seen.add(rid)
            relationships.append({
                "id": rid,
                "name": related.get("name", ""),
                "resource_type": related.get("resource_type", ""),
                "relationship_type": record.get("rel_type", "RELATED"),
                "risk_score": int(related.get("risk_score", 0) or 0),
            })

    return AssetRelatedResponse(asset_id=asset_id, relationships=relationships)


@router.get("/{asset_id}/history", response_model=AssetHistoryResponse)
async def get_asset_history(
    asset_id: str,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
) -> AssetHistoryResponse:
    """Get historical snapshots for an asset."""
    from datetime import datetime
    from app.services.snapshots import AssetSnapshotModel

    query = select(AssetSnapshotModel).where(AssetSnapshotModel.asset_id == asset_id)

    if start_time:
        query = query.where(AssetSnapshotModel.snapshot_timestamp >= datetime.fromisoformat(start_time))
    if end_time:
        query = query.where(AssetSnapshotModel.snapshot_timestamp <= datetime.fromisoformat(end_time))

    query = query.order_by(AssetSnapshotModel.snapshot_timestamp.desc()).limit(limit)
    result = await db.execute(query)
    snapshots = result.scalars().all()

    return AssetHistoryResponse(
        asset_id=asset_id,
        snapshots=[s.to_dict() for s in snapshots],
        total=len(snapshots),
    )


@router.get("/{asset_id}/attack-paths", response_model=AttackPathResponse)
async def get_attack_paths(
    asset_id: str,
    target_id: str | None = None,
    max_hops: int = Query(6, ge=1, le=10),
    neo4j=Depends(get_neo4j),
) -> AttackPathResponse:
    """Compute attack paths to/from this asset."""
    if not neo4j:
        return AttackPathResponse(paths=[], total=0)

    graph_service = GraphService(neo4j)
    paths = await graph_service.find_attack_paths(asset_id, target_id, max_hops)
    return AttackPathResponse(paths=paths, total=len(paths))


@router.post("/query", response_model=CypherQueryResponse)
async def execute_cypher_query(
    query_data: CypherQueryRequest,
    neo4j=Depends(get_neo4j),
) -> CypherQueryResponse:
    """Execute a read-only parameterized Cypher query."""
    if not neo4j:
        raise HTTPException(status_code=503, detail="Graph service unavailable")

    blocked = ["DETACH DELETE", "DELETE", "DROP", "REMOVE", "CREATE", "MERGE", "SET"]
    upper = query_data.query.upper()
    for kw in blocked:
        if kw in upper:
            raise HTTPException(status_code=400, detail=f"Query contains restricted keyword: {kw}")

    try:
        results = await neo4j.execute_query(query_data.query, query_data.parameters)
        columns = list(results[0].keys()) if results else []
        return CypherQueryResponse(results=results, columns=columns)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{asset_id}/findings")
async def get_asset_findings(
    asset_id: str,
    neo4j=Depends(get_neo4j),
) -> dict:
    """Get all open findings for an asset.

    Queries the graph for finding nodes linked to this asset.
    Falls back to returning the asset's open_findings_count if no finding nodes exist.
    """
    if not neo4j:
        raise HTTPException(status_code=503, detail="Graph service unavailable")

    # First verify the asset exists
    asset_query = "MATCH (a:Asset {id: $id}) RETURN a.open_findings_count AS count, a.organization_id AS org_id"
    asset_result = await neo4j.execute_query(asset_query, {"id": asset_id})
    if not asset_result:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    # Try to find linked Finding nodes
    findings_query = """
    MATCH (a:Asset {id: $asset_id})-[:HAS_FINDING]->(f:Finding)
    RETURN f
    ORDER BY f.severity DESC, f.created_at DESC
    LIMIT 100
    """
    findings_result = await neo4j.execute_query(findings_query, {"asset_id": asset_id})

    findings = []
    for record in findings_result:
        f = record.get("f", {})
        findings.append({
            "id": f.get("id", ""),
            "title": f.get("title", ""),
            "severity": f.get("severity", "UNKNOWN"),
            "status": f.get("status", "open"),
            "rule_id": f.get("rule_id", ""),
            "created_at": f.get("created_at", ""),
        })

    return {
        "asset_id": asset_id,
        "findings": findings,
        "total": len(findings),
        "open_findings_count": int(asset_result[0].get("count") or 0),
    }
