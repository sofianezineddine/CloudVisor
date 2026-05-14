"""API routes for policy management."""

import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_redis, get_policy_settings_cached
from app.schemas import (
    RuleCreateRequest,
    RuleUpdateRequest,
    RuleResponse,
    RuleListResponse,
    EvaluateRequest,
    EvaluateResponse,
    DryRunRequest,
    DryRunResponse,
    CompliancePostureResponse,
    ComplianceSummaryResponse,
    DisableRuleRequest,
)
from app.services import RuleManagementService, PolicyEvaluationService, ComplianceService
from app.opa import OPAService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/policy", tags=["policy"])


def get_organization_id(x_org_id: str = Query(...)) -> str:
    return x_org_id


def _extract_user_id(request: Request) -> str:
    """Extract user ID from JWT Bearer token for audit logging."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import base64, json
            token = auth[7:]
            parts = token.split(".")
            if len(parts) == 3:
                payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                return payload.get("sub", "unknown")
        except Exception:
            pass
    return request.headers.get("X-User-ID", "unknown")


def _get_opa() -> OPAService:
    """Get OPA service from cached settings."""
    policy_settings = get_policy_settings_cached()
    return OPAService(policy_settings.opa_url)


@router.get("/rules", response_model=RuleListResponse)
async def list_rules(
    organization_id: str = Depends(get_organization_id),
    category: str | None = None,
    provider: str | None = None,
    severity: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RuleListResponse:
    """List all rules with optional filtering."""
    rule_service = RuleManagementService(db, _get_opa())
    rules = await rule_service.get_rules(
        organization_id=organization_id,
        category=category,
        provider=provider,
        severity=severity,
    )
    return RuleListResponse(rules=rules, total=len(rules))


@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    """Get a specific rule."""
    rule_service = RuleManagementService(db, _get_opa())
    rule = await rule_service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return RuleResponse(**rule)


@router.post("/rules/custom", response_model=RuleResponse, status_code=201)
async def create_custom_rule(
    data: RuleCreateRequest,
    request: Request,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    """Create a custom rule for an organization."""
    rule_service = RuleManagementService(db, _get_opa())
    try:
        rule = await rule_service.create_custom_rule(
            organization_id=organization_id,
            rego_code=data.rego_code,
            title=data.title,
            description=data.description,
            severity=data.severity,
            category=data.category,
            remediation=data.remediation,
            compliance_mapping=data.compliance_mapping,
            tags=data.tags,
        )
        # Emit rule.updated Kafka event (spec §3.4)
        await _emit_rule_event(request, rule["rule_id"], organization_id, "created")
        return RuleResponse(**rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/rules/custom/{rule_id}", response_model=RuleResponse)
async def update_custom_rule(
    rule_id: str,
    data: RuleUpdateRequest,
    request: Request,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    """Update a custom rule."""
    user_id = _extract_user_id(request)
    rule_service = RuleManagementService(db, _get_opa())
    try:
        rule = await rule_service.update_custom_rule(
            rule_id=rule_id,
            organization_id=organization_id,
            rego_code=data.rego_code,
            title=data.title,
            description=data.description,
            remediation=data.remediation,
            compliance_mapping=data.compliance_mapping,
            changed_by=user_id,
        )
        if not rule:
            raise HTTPException(status_code=404, detail="Custom rule not found")
        await _emit_rule_event(request, rule_id, organization_id, "updated")
        return RuleResponse(**rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/rules/custom/{rule_id}")
async def delete_custom_rule(
    rule_id: str,
    request: Request,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a custom rule."""
    rule_service = RuleManagementService(db, _get_opa())
    success = await rule_service.delete_custom_rule(rule_id, organization_id)
    if not success:
        raise HTTPException(status_code=404, detail="Custom rule not found")
    await _emit_rule_event(request, rule_id, organization_id, "deleted")
    return {"message": "Rule deleted successfully"}


@router.post("/rules/{rule_id}/disable")
async def disable_rule(
    rule_id: str,
    data: DisableRuleRequest,
    request: Request,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Disable a rule for an organization."""
    from datetime import timedelta, datetime

    # Extract actual user ID from JWT (not hardcoded)
    user_id = _extract_user_id(request)

    rule_service = RuleManagementService(db, _get_opa())

    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=data.expires_in_days)

    success = await rule_service.disable_rule(
        rule_id=rule_id,
        organization_id=organization_id,
        reason=data.reason,
        disabled_by=user_id,  # Fixed: use actual user ID, not hardcoded string
        expires_at=expires_at,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Emit rule.updated Kafka event (spec §3.4)
    await _emit_rule_event(request, rule_id, organization_id, "disabled")
    return {"message": "Rule disabled successfully"}


@router.post("/rules/{rule_id}/enable")
async def enable_rule(
    rule_id: str,
    request: Request,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-enable a disabled rule."""
    rule_service = RuleManagementService(db, _get_opa())
    await rule_service.enable_rule(rule_id, organization_id)
    # Emit rule.updated Kafka event (spec §3.4)
    await _emit_rule_event(request, rule_id, organization_id, "enabled")
    return {"message": "Rule enabled successfully"}


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    data: EvaluateRequest,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> EvaluateResponse:
    """Evaluate rules against resources."""
    eval_service = PolicyEvaluationService(db, _get_opa(), redis)
    findings = await eval_service.evaluate_resources(
        resources=data.resources,
        organization_id=organization_id,
        category=data.category,
        rule_ids=data.rule_ids,
    )
    return EvaluateResponse(findings=findings, evaluated_count=len(data.resources))


@router.post("/evaluate/dry-run", response_model=DryRunResponse)
async def dry_run(
    data: DryRunRequest,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> DryRunResponse:
    """Test a custom rule without creating findings."""
    eval_service = PolicyEvaluationService(db, _get_opa())
    result = await eval_service.dry_run(
        rego_code=data.rego_code,
        resources=data.resources,
        organization_id=organization_id,
    )
    return DryRunResponse(**result)


# ─── Rule rollback endpoints (spec §3.4) ──────────────────────────────────────

class RollbackRequest(BaseModel):
    target_version: str


@router.get("/rules/custom/{rule_id}/history")
async def get_rule_history(
    rule_id: str,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get version history for a custom rule."""
    rule_service = RuleManagementService(db, _get_opa())
    history = await rule_service.get_rule_history(rule_id, organization_id)
    return {"rule_id": rule_id, "history": history}


@router.post("/rules/custom/{rule_id}/rollback", response_model=RuleResponse)
async def rollback_rule(
    rule_id: str,
    data: RollbackRequest,
    request: Request,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    """Rollback a custom rule to a previous version — spec §3.4."""
    user_id = _extract_user_id(request)
    rule_service = RuleManagementService(db, _get_opa())
    try:
        rule = await rule_service.rollback_rule(rule_id, organization_id, data.target_version)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        await _emit_rule_event(request, rule_id, organization_id, f"rollback_to_{data.target_version}")
        return RuleResponse(**rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Kafka event helper ───────────────────────────────────────────────────────

async def _emit_rule_event(request: Request, rule_id: str, organization_id: str, action: str) -> None:
    """Emit rule.updated Kafka event (spec §3.4). Non-fatal if Kafka unavailable."""
    try:
        from app.producers.policy_events import PolicyEventProducer
        import app.core.dependencies as deps
        if hasattr(deps, '_kafka_producer') and deps._kafka_producer:
            producer = PolicyEventProducer.__new__(PolicyEventProducer)
            producer._producer = deps._kafka_producer
            await producer.emit_rule_updated(rule_id, organization_id, action)
    except Exception as e:
        logger.debug(f"rule.updated event failed (non-fatal): {e}")
