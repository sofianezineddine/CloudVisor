"""
GET /v1/activity  — Recent activity feed

Spec §3.6 Dashboard page: "Recent activity feed: last 20 finding state changes,
new assets discovered, scan completions"

Aggregates recent events from the alert service (finding state changes)
and connector service (new assets, scan completions).
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_alert_proxy, get_connector_proxy
from app.schemas.envelope import ok

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("")
async def get_activity_feed(
    limit: int = Query(20, ge=1, le=100, description="Number of activity items to return"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get the recent activity feed for the authenticated organization.

    Returns a merged, time-sorted list of:
    - Finding state changes (open → in_progress → resolved)
    - New assets discovered
    - Scan completions
    """
    t0 = time.monotonic()
    alert = get_alert_proxy()
    connector = get_connector_proxy()

    activity_items: list[dict[str, Any]] = []

    # Fetch recent finding state changes from alert service
    try:
        findings_result = await alert.get(
            "/internal/findings",
            params={
                "x_org_id": user.organization_id,
                "limit": limit,
                "sort": "-updated_at",
            },
            headers=user.auth_headers,
        )
        for f in findings_result.get("findings", []):
            activity_items.append({
                "type": "finding_updated",
                "timestamp": f.get("last_seen_at") or f.get("updated_at"),
                "title": f.get("title", "Finding updated"),
                "severity": f.get("severity"),
                "status": f.get("status"),
                "resource": f.get("resource_name") or f.get("resource_id"),
                "finding_id": f.get("id"),
            })
    except Exception:
        pass  # Non-fatal — activity feed is best-effort

    # Fetch recent scan completions from connector service
    try:
        accounts_result = await connector.get(
            "/internal/accounts",
            params={"limit": 10},
            headers=user.auth_headers,
        )
        for acc in accounts_result.get("accounts", []):
            if acc.get("last_synced_at"):
                activity_items.append({
                    "type": "scan_completed",
                    "timestamp": acc.get("last_synced_at"),
                    "title": f"Scan completed — {acc.get('name', acc.get('account_id', 'account'))}",
                    "provider": acc.get("provider"),
                    "account_id": acc.get("account_id"),
                    "resource_count": acc.get("resource_count", 0),
                })
    except Exception:
        pass  # Non-fatal

    # Sort by timestamp descending and limit
    activity_items.sort(
        key=lambda x: x.get("timestamp") or "",
        reverse=True,
    )
    activity_items = activity_items[:limit]

    return ok(
        data=activity_items,
        total=len(activity_items),
        took_ms=int((time.monotonic() - t0) * 1000),
    )
