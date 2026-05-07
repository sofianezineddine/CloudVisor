"""
CSPM proxy routes — forwards all CSPM requests to the CSPM service.

GET    /v1/cspm/stats
GET    /v1/cspm/posture
GET    /v1/cspm/posture/accounts
GET    /v1/cspm/posture/trend
GET    /v1/cspm/findings
GET    /v1/cspm/findings/{id}
GET    /v1/cspm/findings/{id}/remediation
PATCH  /v1/cspm/findings/{id}/status
GET    /v1/cspm/resources
GET    /v1/cspm/compliance
GET    /v1/cspm/compliance/{framework}
GET    /v1/cspm/scans
POST   /v1/cspm/scans
GET    /v1/cspm/scans/{id}
GET    /v1/cspm/scans/{id}/resources
GET    /v1/cspm/drift
GET    /v1/cspm/reports
POST   /v1/cspm/reports
GET    /v1/cspm/reports/{id}
GET    /v1/cspm/reports/{id}/download
GET    /v1/cspm/rules          (proxied to Policy service)
POST   /v1/cspm/rules/{id}/disable
POST   /v1/cspm/rules/{id}/enable
POST   /v1/cspm/rules/dry-run
"""

import os
import time
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_cspm_proxy, get_policy_proxy
from app.schemas.envelope import ok

router = APIRouter(prefix="/cspm", tags=["cspm"])


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    account_id: str | None = Query(None),
    provider: str | None = Query(None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id}
    if account_id:
        params["account_id"] = account_id
    if provider:
        params["provider"] = provider
    try:
        result = await cspm.get("/api/v1/cspm/stats", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


# ─── Posture ──────────────────────────────────────────────────────────────────

@router.get("/posture/trend")
async def get_posture_trend(
    days: int = Query(default=30, ge=7, le=90),
    account_id: str | None = Query(None),
    provider: str | None = Query(None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "days": days}
    if account_id:
        params["account_id"] = account_id
    if provider:
        params["provider"] = provider
    try:
        result = await cspm.get("/api/v1/cspm/posture/trend", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/posture/accounts")
async def get_account_posture(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(
            "/api/v1/cspm/posture/accounts",
            params={"org_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/posture")
async def get_posture(
    account_id: str | None = Query(None),
    provider: str | None = Query(None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id}
    if account_id:
        params["account_id"] = account_id
    if provider:
        params["provider"] = provider
    try:
        result = await cspm.get("/api/v1/cspm/posture", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


# ─── Drift ────────────────────────────────────────────────────────────────────

@router.get("/drift")
async def get_drift_findings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(
            "/api/v1/cspm/drift",
            params={"org_id": user.organization_id, "page": page, "page_size": page_size},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


# ─── Findings ─────────────────────────────────────────────────────────────────

@router.get("/findings/drift")
async def get_findings_drift(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(
            "/api/v1/cspm/findings/drift",
            params={"org_id": user.organization_id, "page": page, "page_size": page_size},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/findings")
async def list_findings(
    severity: str | None = Query(None),
    status: str | None = Query(None),
    provider: str | None = Query(None),
    account_id: str | None = Query(None),
    region: str | None = Query(None),
    rule_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {
        "org_id": user.organization_id,
        "page": page,
        "page_size": page_size,
    }
    if severity:
        params["severity"] = severity
    if status:
        params["status"] = status
    if provider:
        params["provider"] = provider
    if account_id:
        params["account_id"] = account_id
    if region:
        params["region"] = region
    if rule_id:
        params["rule_id"] = rule_id
    try:
        result = await cspm.get("/api/v1/cspm/findings", params=params)
        return ok(
            data=result,
            total=result.get("total", 0) if isinstance(result, dict) else 0,
            took_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/findings/{finding_id}/remediation")
async def get_finding_remediation(
    finding_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/findings/{finding_id}/remediation")
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/findings/{finding_id}")
async def get_finding(
    finding_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/findings/{finding_id}")
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


class FindingStatusUpdate(BaseModel):
    status: str


@router.patch("/findings/{finding_id}/status")
async def update_finding_status(
    finding_id: str,
    data: FindingStatusUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.patch(
            f"/api/v1/cspm/findings/{finding_id}/status",
            json={"status": data.status},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


# ─── Resources ────────────────────────────────────────────────────────────────

@router.get("/resources")
async def list_resources(
    provider: str | None = Query(None),
    account_id: str | None = Query(None),
    region: str | None = Query(None),
    resource_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {
        "org_id": user.organization_id,
        "page": page,
        "page_size": page_size,
    }
    if provider:
        params["provider"] = provider
    if account_id:
        params["account_id"] = account_id
    if region:
        params["region"] = region
    if resource_type:
        params["resource_type"] = resource_type
    try:
        result = await cspm.get("/api/v1/cspm/resources", params=params)
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


# ─── Compliance ───────────────────────────────────────────────────────────────

@router.get("/compliance")
async def get_compliance(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    policy = get_policy_proxy()
    try:
        result = await policy.get(
            "/policy/compliance",
            params={"x_org_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")


@router.get("/compliance/{framework}")
async def get_compliance_framework(
    framework: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    policy = get_policy_proxy()
    try:
        result = await policy.get(
            f"/policy/compliance/{framework}",
            params={"x_org_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")


# ─── Scans ────────────────────────────────────────────────────────────────────

@router.get("/scans/{scan_id}/resources")
async def get_scan_resources(
    scan_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(
            f"/api/v1/cspm/scans/{scan_id}/resources",
            params={"org_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/scans/{scan_id}")
async def get_scan(
    scan_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/scans/{scan_id}")
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/scans")
async def list_scans(
    account_id: str | None = Query(None),
    account_ids: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {
        "org_id": user.organization_id,
        "page": page,
        "page_size": page_size,
    }
    if account_id:
        params["account_id"] = account_id
    if account_ids:
        params["account_ids"] = account_ids
    try:
        result = await cspm.get("/api/v1/cspm/scans", params=params)
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


class ScanRequest(BaseModel):
    account_id: str | None = None
    scan_type: str = "on_demand"


@router.post("/scans")
async def trigger_scan(
    data: ScanRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.post(
            "/api/v1/cspm/scans",
            json={
                "organization_id": user.organization_id,
                "account_id": data.account_id,
                "scan_type": data.scan_type,
            },
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


# ─── Rules (proxied to Policy service) ───────────────────────────────────────

@router.post("/rules/dry-run")
async def dry_run_rule(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    policy = get_policy_proxy()
    body = await request.json()
    try:
        result = await policy.post(
            "/policy/evaluate/dry-run",
            json=body,
            params={"organization_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")


@router.post("/rules/{rule_id}/disable")
async def disable_rule(
    rule_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    policy = get_policy_proxy()
    body = await request.json()
    try:
        result = await policy.post(
            f"/policy/rules/{rule_id}/disable",
            json=body,
            params={"organization_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")


@router.post("/rules/{rule_id}/enable")
async def enable_rule(
    rule_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    policy = get_policy_proxy()
    try:
        result = await policy.post(
            f"/policy/rules/{rule_id}/enable",
            params={"organization_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")


@router.get("/rules")
async def list_rules(
    category: str = Query("cspm"),
    provider: str | None = Query(None),
    severity: str | None = Query(None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    policy = get_policy_proxy()
    params: dict[str, Any] = {
        "organization_id": user.organization_id,
        "x_org_id": user.organization_id,
        "category": category,
    }
    if provider:
        params["provider"] = provider
    if severity:
        params["severity"] = severity
    try:
        result = await policy.get("/policy/rules", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Policy service unavailable: {e}")


# ─── Reports ──────────────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    report_type: str = "findings_export"
    framework: str | None = None
    format: str = "csv"
    date_from: str | None = None
    date_to: str | None = None
    account_ids: list[str] = []


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> Any:
    """Proxy CSV download from CSPM service."""
    from fastapi.responses import StreamingResponse
    import httpx as _httpx
    cspm_url = os.environ.get("API_CSPM_SERVICE_URL", "http://cv-cspm:8006")
    try:
        async with _httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{cspm_url}/api/v1/cspm/reports/{report_id}/download",
                params={"org_id": user.organization_id},
            )
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "application/octet-stream")
                cd = resp.headers.get(
                    "content-disposition",
                    f'attachment; filename="report-{report_id}.csv"',
                )
                return StreamingResponse(
                    iter([resp.content]),
                    media_type=content_type,
                    headers={"Content-Disposition": cd},
                )
            raise HTTPException(status_code=resp.status_code, detail="Download failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/reports/{report_id}")
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/reports")
async def list_reports(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(
            "/api/v1/cspm/reports",
            params={"org_id": user.organization_id},
        )
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.post("/reports", status_code=201)
async def create_report(
    data: ReportRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.post(
            "/api/v1/cspm/reports",
            json=data.model_dump(exclude_none=True),
            params={"org_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")
