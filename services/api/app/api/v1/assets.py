"""
GET /v1/assets          — List assets (filter by type, region, account, risk_score)
GET /v1/assets/{id}     — Get asset with properties and related asset IDs
GET /v1/assets/{id}/findings   — Get findings for a specific asset
GET /v1/assets/{id}/attack-paths — Get computed attack paths
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_connector_proxy, get_graph_proxy, get_alert_proxy
from app.schemas.envelope import ok, error

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("")
async def list_assets(
    provider: str | None = Query(None, description="Filter by cloud provider (aws/azure/gcp/oci)"),
    resource_type: str | None = Query(None, description="Filter by resource type (e.g. aws::ec2::instance)"),
    region: str | None = Query(None, description="Filter by region"),
    environment: str | None = Query(None, description="Filter by environment (prod/staging/dev)"),
    is_public: bool | None = Query(None, description="Filter by internet exposure"),
    account_id: str | None = Query(None, description="Filter by cloud account ID"),
    search: str | None = Query(None, description="Full-text search by name"),
    limit: int = Query(50, ge=1, le=500, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List discovered cloud assets for the authenticated organization."""
    t0 = time.monotonic()
    proxy = get_connector_proxy()

    params = {
        "limit": limit,
        "offset": offset,
    }
    if provider:
        params["provider"] = provider
    if resource_type:
        params["resource_type"] = resource_type
    if region:
        params["region"] = region
    if environment:
        params["environment"] = environment
    if is_public is not None:
        params["is_public"] = str(is_public).lower()
    if account_id:
        params["account_id"] = account_id
    if search:
        params["search"] = search

    try:
        result = await proxy.get(
            "/internal/resources",
            params=params,
            headers=user.auth_headers,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Asset service unavailable: {e}")

    took = int((time.monotonic() - t0) * 1000)
    return ok(
        data=result.get("resources", []),
        total=result.get("total", 0),
        took_ms=took,
    )


@router.get("/summary")
async def get_assets_summary(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get asset counts grouped by provider and type."""
    t0 = time.monotonic()
    proxy = get_connector_proxy()
    try:
        result = await proxy.get("/internal/resources/summary", headers=user.auth_headers)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Asset service unavailable: {e}")
    return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a single asset with all properties."""
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

    connector = get_connector_proxy()
    try:
        resources = await connector.get(
            "/internal/resources",
            params={"search": asset_id, "limit": 1},
            headers=user.auth_headers,
        )
        items = resources.get("resources", [])
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
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get computed attack paths to/from this asset."""
    t0 = time.monotonic()
    graph = get_graph_proxy()
    params = {"max_hops": max_hops}
    if target_id:
        params["target_id"] = target_id
    try:
        result = await graph.get(
            f"/internal/assets/{asset_id}/attack-paths",
            params=params,
            headers=user.auth_headers,
        )
        return ok(
            data=result.get("paths", []),
            total=result.get("total", 0),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Graph service unavailable: {e}")


@router.get("/{asset_id}/findings")
async def get_asset_findings(
    asset_id: str,
    status: str | None = Query(None),
    severity: str | None = Query(None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get all findings for a specific asset."""
    t0 = time.monotonic()
    alert = get_alert_proxy()
    params = {"resource_id": asset_id}
    if status:
        params["status"] = status
    if severity:
        params["severity"] = severity
    try:
        result = await alert.get(
            "/internal/findings",
            params={**params, "x_org_id": user.organization_id},
            headers=user.auth_headers,
        )
        findings = result.get("findings", [])
        return ok(
            data=findings,
            total=len(findings),
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alert service unavailable: {e}")
