"""
GET /v1/risk/attack-paths  — All computed attack paths for the org
GET /v1/risk/top-assets    — Top N riskiest assets
POST /v1/assets/query      — Execute a read-only Cypher query
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_graph_proxy
from app.schemas.envelope import ok

router = APIRouter(tags=["risk"])


class CypherQueryRequest(BaseModel):
    query: str
    parameters: dict[str, Any] = Field(default_factory=dict)


@router.get("/risk/attack-paths")
async def get_attack_paths(
    max_hops: int = Query(6, ge=1, le=10),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get all computed attack paths for the organization."""
    t0 = time.monotonic()
    graph = get_graph_proxy()
    try:
        # Use Cypher to find attack paths from public assets
        result = await graph.post(
            "/internal/assets/query",
            json={
                "query": f"""
                MATCH path = (entry:Asset)-[*1..{max_hops}]->(target:Asset)
                WHERE entry.organization_id = $org_id
                  AND entry.is_public = true
                  AND target.risk_score > 50
                  AND entry.id <> target.id
                RETURN path, length(path) AS hops, target.risk_score AS target_risk
                ORDER BY target_risk DESC, hops ASC
                LIMIT 20
                """,
                "parameters": {"org_id": user.organization_id},
            },
            headers=user.auth_headers,
        )
        return ok(
            data=result.get("results", []),
            total=len(result.get("results", [])),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Graph service unavailable: {e}")


@router.get("/risk/top-assets")
async def get_top_risky_assets(
    limit: int = Query(10, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the top N riskiest assets by risk score."""
    t0 = time.monotonic()
    graph = get_graph_proxy()
    try:
        result = await graph.post(
            "/internal/assets/query",
            json={
                "query": """
                MATCH (a:Asset {organization_id: $org_id})
                WHERE a.risk_score > 0
                RETURN a
                ORDER BY a.risk_score DESC
                LIMIT $limit
                """,
                "parameters": {"org_id": user.organization_id, "limit": limit},
            },
            headers=user.auth_headers,
        )
        assets = [r.get("a", {}) for r in result.get("results", [])]
        return ok(
            data=assets,
            total=len(assets),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Graph service unavailable: {e}")


@router.post("/assets/query")
async def execute_graph_query(
    data: CypherQueryRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Execute a read-only Cypher query against the asset graph.

    Security: Only MATCH/RETURN queries are allowed. Write operations
    (CREATE, MERGE, SET, DELETE, DETACH, REMOVE, DROP) are rejected.
    The org_id parameter is always injected server-side for tenant isolation.
    """
    t0 = time.monotonic()

    # ── Security: reject write operations ─────────────────────────────────────
    _FORBIDDEN_KEYWORDS = [
        "CREATE", "MERGE", "SET", "DELETE", "DETACH", "REMOVE",
        "DROP", "CALL", "LOAD CSV", "FOREACH",
    ]
    query_upper = data.query.upper().strip()
    for keyword in _FORBIDDEN_KEYWORDS:
        if keyword in query_upper:
            raise HTTPException(
                status_code=403,
                detail=f"Write operations are not allowed in public API queries. Forbidden keyword: {keyword}",
            )

    # Ensure query starts with MATCH or RETURN (read-only)
    if not query_upper.startswith(("MATCH", "RETURN", "OPTIONAL", "WITH", "UNWIND")):
        raise HTTPException(
            status_code=400,
            detail="Query must start with MATCH, RETURN, OPTIONAL, WITH, or UNWIND",
        )

    graph = get_graph_proxy()
    # Inject org_id into parameters for tenant isolation — cannot be overridden by client
    params = {**data.parameters, "org_id": user.organization_id}
    try:
        result = await graph.post(
            "/internal/assets/query",
            json={"query": data.query, "parameters": params},
            headers=user.auth_headers,
        )
        return ok(
            data=result.get("results", []),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Graph service unavailable: {e}")
