"""API routes for policy management."""

from fastapi import APIRouter, Depends, HTTPException, Query
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


router = APIRouter(prefix="/policy", tags=["policy"])


def get_organization_id(x_org_id: str = Query(...)) -> str:
    return x_org_id


@router.get("/rules", response_model=RuleListResponse)
async def list_rules(
    organization_id: str = Depends(get_organization_id),
    category: str | None = None,
    provider: str | None = None,
    severity: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RuleListResponse:
    """List all rules with optional filtering."""
    policy_settings = get_policy_settings_cached()
    opa_service = OPAService(policy_settings.opa_url)

    rule_service = RuleManagementService(db, opa_service)
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
    policy_settings = get_policy_settings_cached()
    opa_service = OPAService(policy_settings.opa_url)

    rule_service = RuleManagementService(db, opa_service)
    rule = await rule_service.get_rule(rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return RuleResponse(**rule)


@router.post("/rules/custom", response_model=RuleResponse, status_code=201)
async def create_custom_rule(
    data: RuleCreateRequest,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    """Create a custom rule for an organization."""
    policy_settings = get_policy_settings_cached()
    opa_service = OPAService(policy_settings.opa_url)

    rule_service = RuleManagementService(db, opa_service)

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
        return RuleResponse(**rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/rules/custom/{rule_id}", response_model=RuleResponse)
async def update_custom_rule(
    rule_id: str,
    data: RuleUpdateRequest,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    """Update a custom rule."""
    policy_settings = get_policy_settings_cached()
    opa_service = OPAService(policy_settings.opa_url)

    rule_service = RuleManagementService(db, opa_service)

    try:
        rule = await rule_service.update_custom_rule(
            rule_id=rule_id,
            organization_id=organization_id,
            rego_code=data.rego_code,
            title=data.title,
            description=data.description,
            remediation=data.remediation,
            compliance_mapping=data.compliance_mapping,
        )
        if not rule:
            raise HTTPException(status_code=404, detail="Custom rule not found")
        return RuleResponse(**rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/rules/custom/{rule_id}")
async def delete_custom_rule(
    rule_id: str,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a custom rule."""
    policy_settings = get_policy_settings_cached()
    opa_service = OPAService(policy_settings.opa_url)

    rule_service = RuleManagementService(db, opa_service)

    success = await rule_service.delete_custom_rule(rule_id, organization_id)
    if not success:
        raise HTTPException(status_code=404, detail="Custom rule not found")

    return {"message": "Rule deleted successfully"}


@router.post("/rules/{rule_id}/disable")
async def disable_rule(
    rule_id: str,
    data: DisableRuleRequest,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Disable a rule for an organization."""
    from datetime import timedelta
    from datetime import datetime

    policy_settings = get_policy_settings_cached()
    opa_service = OPAService(policy_settings.opa_url)

    rule_service = RuleManagementService(db, opa_service)

    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=data.expires_in_days)

    success = await rule_service.disable_rule(
        rule_id=rule_id,
        organization_id=organization_id,
        reason=data.reason,
        disabled_by="current-user",
        expires_at=expires_at,
    )

    return {"message": "Rule disabled successfully"}


@router.post("/rules/{rule_id}/enable")
async def enable_rule(
    rule_id: str,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-enable a disabled rule."""
    policy_settings = get_policy_settings_cached()
    opa_service = OPAService(policy_settings.opa_url)

    rule_service = RuleManagementService(db, opa_service)
    success = await rule_service.enable_rule(rule_id, organization_id)

    return {"message": "Rule enabled successfully"}


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    data: EvaluateRequest,
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> EvaluateResponse:
    """Evaluate rules against resources."""
    policy_settings = get_policy_settings_cached()
    opa_service = OPAService(policy_settings.opa_url)

    eval_service = PolicyEvaluationService(db, opa_service, redis)

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
    policy_settings = get_policy_settings_cached()
    opa_service = OPAService(policy_settings.opa_url)

    eval_service = PolicyEvaluationService(db, opa_service)

    result = await eval_service.dry_run(
        rego_code=data.rego_code,
        resources=data.resources,
        organization_id=organization_id,
    )

    return DryRunResponse(**result)
