"""
GET /v1/assets                      — List assets (cursor-based pagination)
GET /v1/assets/{id}                 — Get asset with properties and related asset IDs
GET /v1/assets/{id}/findings        — Get findings for a specific asset
GET /v1/assets/{id}/attack-paths    — Get computed attack paths to/from this asset

Query parameter conventions (spec §API Standards):
  filter[field]=value   — field filtering
  sort=field,-other     — sorting (prefix - for descending)
  fields[assets]=f1,f2  — sparse field sets
  cursor=<opaque>       — cursor-based pagination (NO offset)
  limit=50              — page size
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException, Request

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_graph_proxy, get_alert_proxy
from app.schemas.envelope import (
    ok,
    parse_filter_params,
    parse_sort_param,
    parse_fields_param,
    cursor_to_offset,
    make_next_cursor,
)

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("")
async def list_assets(
    request: Request,
    # Explicit convenience params (also accepted via filter[x]=y)
    provider: str | None = Query(None, description="Filter by cloud provider (aws/azure/gcp/oci)"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    region: str | None = Query(None, description="Filter by region"),
    account_id: str | None = Query(None, description="Filter by cloud account ID"),
    risk_score: str | None = Query(None, description="Filter by risk_score (e.g. >=50)"),
    search: str | None = Query(None, description="Full-text search by name"),
    # Cursor-based pagination
    cursor: str | None = Query(None, description="Opaque pagination cursor"),
    limit: int = Query(50, ge=1, le=500, description="Results per page"),
    # Sorting
    sort: str | None = Query(None, description="Sort fields, e.g. sort=risk_score,-created_at"),
    # Sparse field sets
    fields: str | None = Query(None, alias="fields[assets]", description="Comma-separated fields"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List discovered cloud assets for the authenticated organization."""
    t0 = time.monotonic()
    proxy = get_graph_proxy()

    # Parse filter[field]=value params from raw query string
    filters = parse_filter_params(str(request.url.query))

    # Merge explicit params into filters (explicit params take precedence)
    if provider:
        filters["provider"] = provider
    if resource_type:
        filters["resource_type"] = resource_type
    if region:
        filters["region"] = region
    if account_id:
        filters["account_id"] = account_id
    if risk_score:
        filters["risk_score"] = risk_score
    if search:
        filters["search"] = search

    # Decode cursor → offset for upstream (upstream uses offset internally)
    offset, _limit = cursor_to_offset(cursor, limit)

    # Ensure org_id is always included and not None
    if not user.organization_id:
        raise HTTPException(status_code=401, detail="Missing organization ID in token")

    params: dict[str, Any] = {
        "org_id": user.organization_id,  # Add org_id parameter for graph service
        "limit": limit,
        "offset": offset,
        **filters,
    }

    # Forward sort instructions
    sort_fields = parse_sort_param(sort)
    if sort_fields:
        params["sort"] = ",".join(
            f"-{f}" if d == "desc" else f for f, d in sort_fields
        )

    try:
        result = await proxy.get(
            "/internal/assets",
            params=params,
            headers=user.auth_headers,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Asset service unavailable: {e}")

    resources = result.get("assets", result.get("resources", []))
    total = result.get("total", 0)

    # Apply sparse field selection
    selected_fields = parse_fields_param(fields, "assets")
    if selected_fields:
        resources = [
            {k: v for k, v in item.items() if k in selected_fields}
            for item in resources
        ]

    took = int((time.monotonic() - t0) * 1000)
    return ok(
        data=resources,
        total=total,
        next_cursor=make_next_cursor(offset, limit, total),
        took_ms=took,
    )


@router.get("/summary")
async def get_assets_summary(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get asset counts grouped by provider and type."""
    t0 = time.monotonic()
    proxy = get_graph_proxy()
    try:
        result = await proxy.get(
            "/internal/assets/stats",
            params={"org_id": user.organization_id},
            headers=user.auth_headers,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Asset service unavailable: {e}")
    return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a single asset with all properties and related asset IDs."""
    t0 = time.monotonic()
    # Try graph service first (has relationships), fall back to connector
    graph = get_graph_proxy()
    try:
        result = await graph.get(
            f"/internal/assets/{asset_id}",
            headers=user.auth_headers,
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception:
        pass

    connector = get_graph_proxy()
    try:
        resources = await connector.get(
            "/internal/assets",
            params={"search": asset_id, "limit": 1},
            headers=user.auth_headers,
        )
        items = resources.get("assets", resources.get("resources", []))
        if not items:
            raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
        return ok(data=items[0], took_ms=int((time.monotonic() - t0) * 1000))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Asset service unavailable: {e}")


@router.get("/{asset_id}/related")
async def get_related_assets(
    asset_id: str,
    depth: int = Query(1, ge=1, le=3),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get related assets (graph neighbors up to depth hops)."""
    t0 = time.monotonic()
    graph = get_graph_proxy()
    try:
        result = await graph.get(
            f"/internal/assets/{asset_id}/related",
            params={"depth": depth},
            headers=user.auth_headers,
        )
        return ok(
            data=result.get("relationships", []),
            total=len(result.get("relationships", [])),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Graph service unavailable: {e}")


@router.get("/{asset_id}/attack-paths")
async def get_attack_paths(
    asset_id: str,
    target_id: str | None = Query(None),
    max_hops: int = Query(6, ge=1, le=10),
    cursor: str | None = Query(None, description="Opaque pagination cursor"),
    limit: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get computed attack paths to/from this asset."""
    t0 = time.monotonic()
    graph = get_graph_proxy()
    offset, _limit = cursor_to_offset(cursor, limit)
    params: dict[str, Any] = {"max_hops": max_hops, "limit": limit, "offset": offset}
    if target_id:
        params["target_id"] = target_id
    try:
        result = await graph.get(
            f"/internal/assets/{asset_id}/attack-paths",
            params=params,
            headers=user.auth_headers,
        )
        paths = result.get("paths", [])
        total = result.get("total", len(paths))
        return ok(
            data=paths,
            total=total,
            next_cursor=make_next_cursor(offset, limit, total),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Graph service unavailable: {e}")


@router.get("/{asset_id}/history")
async def get_asset_history(
    asset_id: str,
    start_time: str | None = Query(None, description="ISO timestamp for range start"),
    end_time: str | None = Query(None, description="ISO timestamp for range end"),
    limit: int = Query(100, ge=1, le=500),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get historical snapshots for an asset (time-travel queries)."""
    t0 = time.monotonic()
    graph = get_graph_proxy()
    params: dict[str, Any] = {"limit": limit}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    try:
        result = await graph.get(
            f"/internal/assets/{asset_id}/history",
            params=params,
            headers=user.auth_headers,
        )
        return ok(
            data=result.get("snapshots", []),
            total=result.get("total", 0),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Graph service unavailable: {e}")


@router.get("/{asset_id}/findings")
async def get_asset_findings(
    asset_id: str,
    request: Request,
    status: str | None = Query(None),
    severity: str | None = Query(None),
    cursor: str | None = Query(None, description="Opaque pagination cursor"),
    limit: int = Query(50, ge=1, le=500),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get all findings for a specific asset (cursor-based pagination)."""
    t0 = time.monotonic()
    alert = get_alert_proxy()

    filters = parse_filter_params(str(request.url.query))
    if status:
        filters["status"] = status
    if severity:
        filters["severity"] = severity

    offset, _limit = cursor_to_offset(cursor, limit)
    params: dict[str, Any] = {
        "resource_id": asset_id,
        "limit": limit,
        "offset": offset,
        **filters,
    }
    try:
        result = await alert.get(
            "/internal/findings",
            params={**params, "x_org_id": user.organization_id},
            headers=user.auth_headers,
        )
        findings = result.get("findings", [])
        total = result.get("total", len(findings))
        return ok(
            data=findings,
            total=total,
            next_cursor=make_next_cursor(offset, limit, total),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")
