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


# ─── IAM Analysis ─────────────────────────────────────────────────────────────

@router.post("/iam/analyze", status_code=202)
async def trigger_iam_analysis(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    try:
        result = await cspm.post(
            "/api/v1/cspm/iam/analyze",
            json={**body, "organization_id": user.organization_id},
            params={"org_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/iam/identities/{identity_id}")
async def get_iam_identity(
    identity_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/iam/identities/{identity_id}", params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/iam/identities")
async def list_iam_identities(
    account_id: str | None = Query(None),
    identity_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if account_id:
        params["account_id"] = account_id
    if identity_type:
        params["identity_type"] = identity_type
    try:
        result = await cspm.get("/api/v1/cspm/iam/identities", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/iam/escalation-paths")
async def list_escalation_paths(
    severity: str | None = Query(None),
    account_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if severity:
        params["severity"] = severity
    if account_id:
        params["account_id"] = account_id
    try:
        result = await cspm.get("/api/v1/cspm/iam/escalation-paths", params=params)
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/iam/cross-account-trusts")
async def list_cross_account_trusts(
    account_id: str | None = Query(None),
    risk_level: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if account_id:
        params["account_id"] = account_id
    if risk_level:
        params["risk_level"] = risk_level
    try:
        result = await cspm.get("/api/v1/cspm/iam/cross-account-trusts", params=params)
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/iam/service-accounts")
async def list_service_accounts(
    account_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if account_id:
        params["account_id"] = account_id
    try:
        result = await cspm.get("/api/v1/cspm/iam/service-accounts", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/iam/dormant")
async def list_dormant_identities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get("/api/v1/cspm/iam/dormant", params={"org_id": user.organization_id, "page": page, "page_size": page_size})
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


# ─── Attack Paths ─────────────────────────────────────────────────────────────

@router.post("/attack-paths/analyze", status_code=202)
async def trigger_attack_path_analysis(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    try:
        result = await cspm.post(
            "/api/v1/cspm/attack-paths/analyze",
            json={**body, "organization_id": user.organization_id},
            params={"org_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/attack-paths/blast-radius/{resource_id}")
async def get_blast_radius(
    resource_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/attack-paths/blast-radius/{resource_id}", params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/attack-paths/toxic-combinations")
async def list_toxic_combinations(
    account_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if account_id:
        params["account_id"] = account_id
    try:
        result = await cspm.get("/api/v1/cspm/attack-paths/toxic-combinations", params=params)
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/attack-paths/{path_id}")
async def get_attack_path(
    path_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/attack-paths/{path_id}", params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/attack-paths")
async def list_attack_paths(
    severity: str | None = Query(None),
    is_lateral_movement: bool | None = Query(None),
    sort_by: str | None = Query(None),
    sort_dir: str | None = Query(None),
    account_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if severity:
        params["severity"] = severity
    if is_lateral_movement is not None:
        params["is_lateral_movement"] = is_lateral_movement
    if sort_by:
        params["sort_by"] = sort_by
    if sort_dir:
        params["sort_dir"] = sort_dir
    if account_id:
        params["account_id"] = account_id
    try:
        result = await cspm.get("/api/v1/cspm/attack-paths", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


# ─── IaC Security ─────────────────────────────────────────────────────────────

@router.post("/iac/scan")
async def submit_iac_scan(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json()
    try:
        result = await cspm.post(
            "/api/v1/cspm/iac/scan",
            json=body,
            params={"org_id": user.organization_id},
        )
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.post("/iac/webhook", status_code=202)
async def iac_webhook(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.body()
    headers = dict(request.headers)
    try:
        import httpx as _httpx
        cspm_url = os.environ.get("API_CSPM_SERVICE_URL", "http://cv-cspm:8006")
        async with _httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{cspm_url}/api/v1/cspm/iac/webhook",
                content=body,
                headers={k: v for k, v in headers.items() if k.lower() not in ("host", "content-length")},
                params={"org_id": user.organization_id},
            )
            return ok(data=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.post("/iac/webhook-configs", status_code=201)
async def create_iac_webhook_config(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json()
    try:
        result = await cspm.post("/api/v1/cspm/iac/webhook-configs", json=body, params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/iac/webhook-configs")
async def list_iac_webhook_configs(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get("/api/v1/cspm/iac/webhook-configs", params={"org_id": user.organization_id})
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/iac/scans/{scan_id}/findings")
async def get_iac_scan_findings(
    scan_id: str,
    severity: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if severity:
        params["severity"] = severity
    try:
        result = await cspm.get(f"/api/v1/cspm/iac/scans/{scan_id}/findings", params=params)
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/iac/scans/{scan_id}")
async def get_iac_scan(
    scan_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/iac/scans/{scan_id}", params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/iac/scans")
async def list_iac_scans(
    status: str | None = Query(None),
    template_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if status:
        params["status"] = status
    if template_type:
        params["template_type"] = template_type
    try:
        result = await cspm.get("/api/v1/cspm/iac/scans", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


# ─── Drift Detection ──────────────────────────────────────────────────────────

@router.get("/drift/events/{event_id}")
async def get_drift_event(
    event_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/drift/events/{event_id}", params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/drift/events")
async def list_drift_events(
    is_security_relevant: bool | None = Query(None),
    severity: str | None = Query(None),
    resource_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if is_security_relevant is not None:
        params["is_security_relevant"] = is_security_relevant
    if severity:
        params["severity"] = severity
    if resource_id:
        params["resource_id"] = resource_id
    try:
        result = await cspm.get("/api/v1/cspm/drift/events", params=params)
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.post("/drift/baselines", status_code=201)
async def create_drift_baseline(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json()
    try:
        result = await cspm.post("/api/v1/cspm/drift/baselines", json=body, params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/drift/baselines/{resource_id}")
async def get_drift_baseline(
    resource_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/drift/baselines/{resource_id}", params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/drift/baselines")
async def list_drift_baselines(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get("/api/v1/cspm/drift/baselines", params={"org_id": user.organization_id, "page": page, "page_size": page_size})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/drift/anomalies")
async def list_anomaly_findings(
    severity: str | None = Query(None),
    resource_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if severity:
        params["severity"] = severity
    if resource_id:
        params["resource_id"] = resource_id
    try:
        result = await cspm.get("/api/v1/cspm/drift/anomalies", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.put("/drift/alerts/{alert_id}")
async def update_alert_status(
    alert_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json()
    try:
        result = await cspm.put(f"/api/v1/cspm/drift/alerts/{alert_id}", json=body, params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/drift/alerts")
async def list_correlated_alerts(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if status:
        params["status"] = status
    if severity:
        params["severity"] = severity
    try:
        result = await cspm.get("/api/v1/cspm/drift/alerts", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.post("/drift/correlation-rules", status_code=201)
async def create_correlation_rule(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json()
    try:
        result = await cspm.post("/api/v1/cspm/drift/correlation-rules", json=body, params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/drift/correlation-rules")
async def list_correlation_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get("/api/v1/cspm/drift/correlation-rules", params={"org_id": user.organization_id, "page": page, "page_size": page_size})
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/drift/history/{resource_id}")
async def get_config_history(
    resource_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/drift/history/{resource_id}", params={"org_id": user.organization_id, "page": page, "page_size": page_size})
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


# ─── Policy Engine ────────────────────────────────────────────────────────────

@router.post("/policies/rules", status_code=201)
async def create_custom_rule(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json()
    try:
        result = await cspm.post("/api/v1/cspm/policies/rules", json=body, params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.put("/policies/rules/{rule_id}")
async def update_custom_rule(
    rule_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json()
    try:
        result = await cspm.put(f"/api/v1/cspm/policies/rules/{rule_id}", json=body, params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.post("/policies/rules/{rule_id}/test")
async def test_custom_rule(
    rule_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json()
    try:
        result = await cspm.post(f"/api/v1/cspm/policies/rules/{rule_id}/test", json=body, params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.post("/policies/rules/{rule_id}/rollback")
async def rollback_custom_rule(
    rule_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    try:
        result = await cspm.post(f"/api/v1/cspm/policies/rules/{rule_id}/rollback", json=body, params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/policies/rules/{rule_id}/versions")
async def list_rule_versions(
    rule_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/policies/rules/{rule_id}/versions", params={"org_id": user.organization_id})
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/policies/rules/{rule_id}")
async def get_custom_rule(
    rule_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get(f"/api/v1/cspm/policies/rules/{rule_id}", params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/policies/rules")
async def list_custom_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    try:
        result = await cspm.get("/api/v1/cspm/policies/rules", params={"org_id": user.organization_id, "page": page, "page_size": page_size})
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.post("/policies/hierarchy", status_code=201)
async def set_policy_hierarchy(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json()
    try:
        result = await cspm.post("/api/v1/cspm/policies/hierarchy", json=body, params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/policies/hierarchy")
async def get_policy_hierarchy(
    team_id: str | None = Query(None),
    project_id: str | None = Query(None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id}
    if team_id:
        params["team_id"] = team_id
    if project_id:
        params["project_id"] = project_id
    try:
        result = await cspm.get("/api/v1/cspm/policies/hierarchy", params=params)
        items = result if isinstance(result, list) else result.get("items", result)
        return ok(data=items, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.post("/policies/exceptions", status_code=201)
async def create_policy_exception(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    body = await request.json()
    try:
        result = await cspm.post("/api/v1/cspm/policies/exceptions", json=body, params={"org_id": user.organization_id})
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.delete("/policies/exceptions/{exception_id}", status_code=204)
async def revoke_policy_exception(
    exception_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    cspm = get_cspm_proxy()
    try:
        await cspm.delete(f"/api/v1/cspm/policies/exceptions/{exception_id}", params={"org_id": user.organization_id})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/policies/exceptions")
async def list_policy_exceptions(
    rule_id: str | None = Query(None),
    resource_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if rule_id:
        params["rule_id"] = rule_id
    if resource_id:
        params["resource_id"] = resource_id
    try:
        result = await cspm.get("/api/v1/cspm/policies/exceptions", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")


@router.get("/policies/audit-log")
async def get_policy_audit_log(
    action: str | None = Query(None),
    rule_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    t0 = time.monotonic()
    cspm = get_cspm_proxy()
    params: dict[str, Any] = {"org_id": user.organization_id, "page": page, "page_size": page_size}
    if action:
        params["action"] = action
    if rule_id:
        params["rule_id"] = rule_id
    try:
        result = await cspm.get("/api/v1/cspm/policies/audit-log", params=params)
        return ok(data=result, took_ms=int((time.monotonic() - t0) * 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSPM service unavailable: {e}")
