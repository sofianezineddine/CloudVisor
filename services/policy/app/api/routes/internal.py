"""Internal API routes for service-to-service communication."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_redis, get_policy_settings_cached
from app.opa import OPAService
from app.services import PolicyEvaluationService, RuleManagementService, ComplianceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/policy", tags=["internal"])

# Internal service token for service-to-service auth
import os
_INTERNAL_SERVICE_TOKEN = os.environ.get("POLICY_INTERNAL_SERVICE_TOKEN", "")


def _verify_service_token(x_service_token: str | None) -> None:
    """Verify inter-service token. Logs warning in dev if not configured."""
    if not _INTERNAL_SERVICE_TOKEN:
        logger.warning("POLICY_INTERNAL_SERVICE_TOKEN not set — internal endpoints unprotected")
        return
    if not x_service_token or x_service_token != _INTERNAL_SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing service token")


def _get_opa() -> OPAService:
    policy_settings = get_policy_settings_cached()
    return OPAService(policy_settings.opa_url)


# ─── Evaluation ───────────────────────────────────────────────────────────────

class InternalEvaluateRequest(BaseModel):
    resources: list[dict[str, Any]]
    org_id: str
    category: str | None = None
    rule_ids: list[str] | None = None


class InternalEvaluateResponse(BaseModel):
    findings: list[dict[str, Any]]
    evaluated_count: int


@router.post("/evaluate", response_model=InternalEvaluateResponse)
async def internal_evaluate(
    data: InternalEvaluateRequest,
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> InternalEvaluateResponse:
    """Internal endpoint for CSPM scanner to evaluate resources against policy rules."""
    _verify_service_token(x_service_token)
    try:
        eval_service = PolicyEvaluationService(db, _get_opa(), redis)
        findings = await eval_service.evaluate_resources(
            resources=data.resources,
            organization_id=data.org_id,
            category=data.category or "cspm",
            rule_ids=data.rule_ids,
        )
        return InternalEvaluateResponse(
            findings=findings,
            evaluated_count=len(data.resources),
        )
    except Exception as e:
        logger.error(f"Internal evaluate error: {e}")
        return InternalEvaluateResponse(findings=[], evaluated_count=len(data.resources))


@router.post("/evaluate/dry-run")
async def internal_dry_run(
    data: dict,
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Internal dry-run endpoint — test a custom rule without creating findings."""
    _verify_service_token(x_service_token)
    eval_service = PolicyEvaluationService(db, _get_opa())
    return await eval_service.dry_run(
        rego_code=data.get("rego_code", ""),
        resources=data.get("resources", []),
        organization_id=data.get("org_id", ""),
    )


# ─── Rule management (spec §3.4 internal endpoints) ──────────────────────────

@router.get("/rules")
async def internal_list_rules(
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    org_id: str | None = Query(default=None),
    category: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Internal: list all rules. Used by CSPM, CWPP, KSPM modules."""
    _verify_service_token(x_service_token)
    rule_service = RuleManagementService(db, _get_opa())
    rules = await rule_service.get_rules(
        organization_id=org_id,
        category=category,
        provider=provider,
        severity=severity,
    )
    return {"rules": rules, "total": len(rules)}


@router.get("/rules/{rule_id}")
async def internal_get_rule(
    rule_id: str,
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Internal: get a specific rule by ID."""
    _verify_service_token(x_service_token)
    rule_service = RuleManagementService(db, _get_opa())
    rule = await rule_service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


# ─── Compliance (spec §3.4 internal endpoints) ────────────────────────────────

@router.get("/compliance")
async def internal_compliance_summary(
    org_id: str = Query(...),
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Internal: overall compliance posture across all frameworks."""
    _verify_service_token(x_service_token)
    compliance_service = ComplianceService(db, redis)
    frameworks = await compliance_service.get_all_frameworks(org_id)
    return {"frameworks": frameworks}


@router.get("/compliance/{framework}")
async def internal_compliance_framework(
    framework: str,
    org_id: str = Query(...),
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Internal: control-by-control compliance breakdown for a framework."""
    _verify_service_token(x_service_token)
    compliance_service = ComplianceService(db, redis)
    return await compliance_service.get_compliance_posture(org_id, framework)


@router.get("/compliance/{framework}/evidence")
async def internal_compliance_evidence(
    framework: str,
    control_id: str = Query(...),
    org_id: str = Query(...),
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Internal: download evidence for a compliance control."""
    _verify_service_token(x_service_token)
    compliance_service = ComplianceService(db, redis)
    return await compliance_service.get_evidence(org_id, framework, control_id)
