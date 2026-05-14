"""Policy Engine API routes.

Endpoints for custom Rego rule management, policy hierarchy resolution,
enforcement modes, exception management, and audit logging.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import require_org_id
from ..db_helper import get_db
from ..models.policy_models import (
    CustomRegoRuleModel,
    PolicyAuditLogModel,
    PolicyExceptionModel,
    PolicyHierarchyModel,
)
from ..schemas.policy_schemas import (
    CustomRuleOut,
    CustomRuleRequest,
    PolicyAuditLogOut,
    PolicyExceptionOut,
    PolicyExceptionRequest,
    PolicyHierarchyOut,
    PolicyHierarchyRequest,
    RuleTestOut,
    RuleTestRequest,
    RuleVersionOut,
)
from ..services.policy_manager import (
    apply_overrides,
    create_custom_rule,
    create_exception,
    expire_exceptions,
    get_effective_policies,
    list_rule_versions,
    rollback_rule,
    test_rule,
    update_rule,
    validate_rego_syntax,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Policy Engine"])


# ═══════════════════════════════════════════════════════════════════════════════
# Custom Rule Management
# ═══════════════════════════════════════════════════════════════════════════════


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/policies/rules — Create custom Rego rule
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/cspm/policies/rules",
    response_model=CustomRuleOut,
    status_code=201,
)
async def create_rule_endpoint(
    payload: CustomRuleRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> CustomRuleOut:
    """Create a new custom Rego rule after validating syntax via OPA."""
    try:
        rule = await create_custom_rule(
            db,
            organization_id=org_id,
            rule_id=payload.rule_id,
            name=payload.name,
            rego_content=payload.rego_content,
            description=payload.description,
            created_by="api",
        )
        await db.commit()
        await db.refresh(rule)
        return CustomRuleOut.model_validate(rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("create_rule_endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create rule")


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/policies/rules — List custom rules
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/policies/rules", response_model=list[CustomRuleOut])
async def list_rules_endpoint(
    org_id: str = Depends(require_org_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[CustomRuleOut]:
    """List all custom Rego rules for the organization."""
    try:
        q = (
            select(CustomRegoRuleModel)
            .where(
                CustomRegoRuleModel.organization_id == org_id,
                CustomRegoRuleModel.is_active == True,  # noqa: E712
            )
            .order_by(CustomRegoRuleModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await db.execute(q)).scalars().all()
        return [CustomRuleOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_rules_endpoint error: %s", e)
        return []


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/policies/rules/{rule_id} — Get rule detail
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/cspm/policies/rules/{rule_id}",
    response_model=CustomRuleOut,
)
async def get_rule_endpoint(
    rule_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> CustomRuleOut:
    """Get detailed information about a specific custom rule."""
    try:
        row = (
            await db.execute(
                select(CustomRegoRuleModel).where(
                    CustomRegoRuleModel.id == rule_id,
                    CustomRegoRuleModel.organization_id == org_id,
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Rule not found")
        return CustomRuleOut.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_rule_endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")


# ---------------------------------------------------------------------------
# PUT /api/v1/cspm/policies/rules/{rule_id} — Update rule (creates new version)
# ---------------------------------------------------------------------------


@router.put(
    "/api/v1/cspm/policies/rules/{rule_id}",
    response_model=CustomRuleOut,
)
async def update_rule_endpoint(
    rule_id: str,
    payload: CustomRuleRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> CustomRuleOut:
    """Update a custom rule, creating a new version and preserving history."""
    try:
        rule = await update_rule(
            db,
            rule_db_id=rule_id,
            organization_id=org_id,
            rego_content=payload.rego_content,
            updated_by="api",
        )
        await db.commit()
        await db.refresh(rule)
        return CustomRuleOut.model_validate(rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("update_rule_endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update rule")


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/policies/rules/{rule_id}/test — Test rule against sample input
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/cspm/policies/rules/{rule_id}/test",
    response_model=RuleTestOut,
)
async def test_rule_endpoint(
    rule_id: str,
    payload: RuleTestRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> RuleTestOut:
    """Test a custom rule against sample input without persisting findings."""
    try:
        # Fetch the rule to get its rego_content
        row = (
            await db.execute(
                select(CustomRegoRuleModel).where(
                    CustomRegoRuleModel.id == rule_id,
                    CustomRegoRuleModel.organization_id == org_id,
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Rule not found")

        result = await test_rule(row.rego_content, payload.input_data)
        return RuleTestOut(
            rule_id=row.rule_id,
            passed=result.get("passed", False),
            violations=result.get("violations", []),
            error=result.get("error"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("test_rule_endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to test rule")


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/policies/rules/{rule_id}/rollback — Rollback to previous version
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/cspm/policies/rules/{rule_id}/rollback",
    response_model=CustomRuleOut,
)
async def rollback_rule_endpoint(
    rule_id: str,
    org_id: str = Depends(require_org_id),
    target_version: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> CustomRuleOut:
    """Rollback a rule to a previous version."""
    try:
        rule = await rollback_rule(
            db,
            rule_db_id=rule_id,
            organization_id=org_id,
            target_version=target_version,
            rolled_back_by="api",
        )
        await db.commit()
        await db.refresh(rule)
        return CustomRuleOut.model_validate(rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("rollback_rule_endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to rollback rule")


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/policies/rules/{rule_id}/versions — List rule versions
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/cspm/policies/rules/{rule_id}/versions",
    response_model=list[RuleVersionOut],
)
async def list_rule_versions_endpoint(
    rule_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> list[RuleVersionOut]:
    """List version history for a custom rule."""
    try:
        # Verify rule exists
        row = (
            await db.execute(
                select(CustomRegoRuleModel).where(
                    CustomRegoRuleModel.id == rule_id,
                    CustomRegoRuleModel.organization_id == org_id,
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Rule not found")

        versions = await list_rule_versions(db, rule_db_id=rule_id)
        return [RuleVersionOut.model_validate(v) for v in versions]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_rule_versions_endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")


# ═══════════════════════════════════════════════════════════════════════════════
# Policy Hierarchy
# ═══════════════════════════════════════════════════════════════════════════════


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/policies/hierarchy — Set policy at hierarchy level
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/cspm/policies/hierarchy",
    response_model=PolicyHierarchyOut,
    status_code=201,
)
async def set_policy_hierarchy_endpoint(
    payload: PolicyHierarchyRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> PolicyHierarchyOut:
    """Set or override a policy at a specific hierarchy level."""
    try:
        policy = await apply_overrides(
            db,
            organization_id=org_id,
            level=payload.level,
            level_id=payload.level_id,
            rule_id=payload.rule_id,
            enforcement_mode=payload.enforcement_mode,
            overridden_by="api",
            justification=payload.override_justification or "Policy set via API",
        )
        await db.commit()
        await db.refresh(policy)
        return PolicyHierarchyOut.model_validate(policy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("set_policy_hierarchy_endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to set policy hierarchy")


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/policies/hierarchy — Get resolved policy hierarchy
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/cspm/policies/hierarchy",
    response_model=list[PolicyHierarchyOut],
)
async def get_policy_hierarchy_endpoint(
    org_id: str = Depends(require_org_id),
    team_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[PolicyHierarchyOut]:
    """Get the resolved (merged) policy hierarchy for a given context."""
    try:
        policies = await get_effective_policies(
            db,
            organization_id=org_id,
            team_id=team_id,
            project_id=project_id,
        )
        return [PolicyHierarchyOut.model_validate(p) for p in policies]
    except Exception as e:
        logger.error("get_policy_hierarchy_endpoint error: %s", e)
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# Policy Exceptions
# ═══════════════════════════════════════════════════════════════════════════════


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/policies/exceptions — Create policy exception
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/cspm/policies/exceptions",
    response_model=PolicyExceptionOut,
    status_code=201,
)
async def create_exception_endpoint(
    payload: PolicyExceptionRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> PolicyExceptionOut:
    """Create a policy exception with expiry and justification."""
    try:
        exception = await create_exception(
            db,
            organization_id=org_id,
            rule_id=payload.rule_id,
            resource_id=payload.resource_id,
            justification=payload.justification,
            granted_by="api",
            expires_at=payload.expires_at,
        )
        await db.commit()
        await db.refresh(exception)
        return PolicyExceptionOut.model_validate(exception)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("create_exception_endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create exception")


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/policies/exceptions — List active exceptions
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/cspm/policies/exceptions",
    response_model=list[PolicyExceptionOut],
)
async def list_exceptions_endpoint(
    org_id: str = Depends(require_org_id),
    rule_id: Optional[str] = Query(default=None),
    resource_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[PolicyExceptionOut]:
    """List active policy exceptions with optional filters."""
    try:
        q = select(PolicyExceptionModel).where(
            PolicyExceptionModel.organization_id == org_id,
            PolicyExceptionModel.is_active == True,  # noqa: E712
        )
        if rule_id:
            q = q.where(PolicyExceptionModel.rule_id == rule_id)
        if resource_id:
            q = q.where(PolicyExceptionModel.resource_id == resource_id)

        q = q.order_by(PolicyExceptionModel.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [PolicyExceptionOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_exceptions_endpoint error: %s", e)
        return []


# ---------------------------------------------------------------------------
# DELETE /api/v1/cspm/policies/exceptions/{exception_id} — Revoke exception
# ---------------------------------------------------------------------------


@router.delete(
    "/api/v1/cspm/policies/exceptions/{exception_id}",
    status_code=204,
)
async def revoke_exception_endpoint(
    exception_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke (deactivate) a policy exception."""
    try:
        row = (
            await db.execute(
                select(PolicyExceptionModel).where(
                    PolicyExceptionModel.id == exception_id,
                    PolicyExceptionModel.organization_id == org_id,
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Exception not found")

        row.is_active = False
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("revoke_exception_endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to revoke exception")


# ═══════════════════════════════════════════════════════════════════════════════
# Audit Log
# ═══════════════════════════════════════════════════════════════════════════════


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/policies/audit-log — Get policy audit log
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/cspm/policies/audit-log",
    response_model=list[PolicyAuditLogOut],
)
async def get_audit_log_endpoint(
    org_id: str = Depends(require_org_id),
    action: Optional[str] = Query(default=None),
    rule_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[PolicyAuditLogOut]:
    """Get the policy audit log with optional filters."""
    try:
        q = select(PolicyAuditLogModel).where(
            PolicyAuditLogModel.organization_id == org_id,
        )
        if action:
            q = q.where(PolicyAuditLogModel.action == action)
        if rule_id:
            q = q.where(PolicyAuditLogModel.rule_id == rule_id)

        q = q.order_by(PolicyAuditLogModel.timestamp.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [PolicyAuditLogOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("get_audit_log_endpoint error: %s", e)
        return []
