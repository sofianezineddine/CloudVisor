"""
GET /v1/modules/summary  — Per-module finding counts and last scan timestamp

Spec §3.6 Dashboard page: "Protection modules" section shows per-module
(CSPM, CWPP, CI/CD, CIEM, KSPM, CDR) finding counts and last scan time.
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_alert_proxy, get_cspm_proxy
from app.schemas.envelope import ok

router = APIRouter(prefix="/modules", tags=["modules"])

# All modules defined in the spec
MODULES = ["cspm", "cwpp", "cicd", "ciem", "kspm", "dspm", "cdr"]


@router.get("/summary")
async def get_modules_summary(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get per-module finding counts and last scan timestamp.

    Returns a list of module summaries used by the dashboard's
    "Protection modules" section.
    """
    t0 = time.monotonic()
    alert = get_alert_proxy()
    cspm = get_cspm_proxy()

    # Get finding stats (includes by_module and by_severity breakdown)
    stats: dict[str, Any] = {}
    by_severity: dict[str, int] = {}
    try:
        stats_result = await alert.get(
            "/internal/findings/stats",
            params={"x_org_id": user.organization_id},
            headers=user.auth_headers,
        )
        stats = stats_result.get("by_module", {})
        by_severity = stats_result.get("by_severity", {})
    except Exception:
        pass  # Non-fatal

    # Get last scan time from CSPM
    last_scan_at: str | None = None
    try:
        posture = await cspm.get(
            "/api/v1/cspm/posture",
            params={"org_id": user.organization_id},
        )
        last_scan_at = posture.get("last_scan_at")
    except Exception:
        pass  # Non-fatal

    modules_summary = []
    for module in MODULES:
        finding_count = stats.get(module, 0)
        # Estimate critical count proportionally from overall severity distribution
        total_findings = sum(by_severity.values()) or 1
        critical_ratio = by_severity.get("CRITICAL", 0) / total_findings
        critical_count = round(finding_count * critical_ratio)
        modules_summary.append({
            "module": module,
            "display_name": module.upper(),
            "finding_count": finding_count,
            "critical_count": critical_count,
            "last_scan_at": last_scan_at,
            "status": "active" if finding_count >= 0 else "inactive",
        })

    return ok(
        data=modules_summary,
        total=len(modules_summary),
        took_ms=int((time.monotonic() - t0) * 1000),
    )
