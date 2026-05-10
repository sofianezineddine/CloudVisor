"""Operational/admin endpoints for the connector service.

These are intentionally unscoped by tenant — they expose internal health
diagnostics (circuit breakers, queue health) for the platform team. Protect
them at the API gateway with an admin-only role.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.services.circuit_breaker import get_circuit_breaker_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/circuit-breakers")
async def list_circuit_breakers() -> dict[str, Any]:
    """Return current state of every circuit breaker.

    Each breaker name follows ``<provider>-<service>`` (e.g. ``aws-s3``,
    ``azure-compute``). Useful to see which cloud-API integrations are
    currently degraded.
    """
    registry = await get_circuit_breaker_registry()
    breakers = await registry.get_all_status()
    # Group by open/closed for quick UI rendering
    open_breakers = {k: v for k, v in breakers.items() if v.get("state") == "open"}
    half_open_breakers = {k: v for k, v in breakers.items() if v.get("state") == "half_open"}
    closed_breakers = {k: v for k, v in breakers.items() if v.get("state") == "closed"}
    return {
        "open": open_breakers,
        "half_open": half_open_breakers,
        "closed": closed_breakers,
        "total": len(breakers),
    }


@router.get("/circuit-breakers/{name}")
async def get_circuit_breaker(name: str) -> dict[str, Any]:
    """Get status of a specific circuit breaker."""
    registry = await get_circuit_breaker_registry()
    breaker = await registry.get(name)
    if breaker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circuit breaker '{name}' not found",
        )
    return breaker.get_status()


@router.post("/circuit-breakers/{name}/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_circuit_breaker(name: str) -> None:
    """Manually reset a circuit breaker to CLOSED.

    Only use when you know the underlying service has recovered — resetting
    an actually-broken breaker causes a thundering herd.
    """
    registry = await get_circuit_breaker_registry()
    breaker = await registry.get(name)
    if breaker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circuit breaker '{name}' not found",
        )
    await registry.reset(name)
    logger.info(f"Circuit breaker '{name}' manually reset via admin API")


@router.post("/circuit-breakers/reset-all", status_code=status.HTTP_204_NO_CONTENT)
async def reset_all_circuit_breakers() -> None:
    """Reset every circuit breaker. Very blunt — use with care."""
    registry = await get_circuit_breaker_registry()
    await registry.reset_all()
    logger.info("ALL circuit breakers reset via admin API")
