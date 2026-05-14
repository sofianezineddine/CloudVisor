"""Policy Engine — custom rule management, hierarchy, enforcement, and exceptions.

Provides lifecycle management for custom Rego rules, three-level policy hierarchy
resolution (organization → team → project), enforcement mode routing, and
policy exception management with audit logging.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_cspm_settings
from ..core.opa_client import OPAClient, OPAClientError
from ..models.policy_models import (
    CustomRegoRuleModel,
    PolicyAuditLogModel,
    PolicyExceptionModel,
    PolicyHierarchyModel,
    RegoRuleVersionModel,
)
from ..producers.finding_producer import FindingProducer

logger = logging.getLogger(__name__)
settings = get_cspm_settings()


# ═══════════════════════════════════════════════════════════════════════════════
# Task 10.1 — Custom Rule Management
# ═══════════════════════════════════════════════════════════════════════════════


async def validate_rego_syntax(rego_content: str) -> dict[str, Any]:
    """Validate Rego rule syntax by calling the OPA compiler.

    Args:
        rego_content: The Rego source code to validate.

    Returns:
        Dict with 'valid' (bool) and optional 'errors' list.
    """
    opa = OPAClient()
    try:
        result = await opa.compile_rule(rego_content)
        is_valid = result.get("valid", False)
        errors = result.get("errors", [])
        return {"valid": is_valid, "errors": errors}
    except OPAClientError as e:
        logger.error("OPA syntax validation failed: %s", e)
        return {"valid": False, "errors": [str(e)]}


async def create_custom_rule(
    db: AsyncSession,
    *,
    organization_id: str,
    rule_id: str,
    name: str,
    rego_content: str,
    description: str | None = None,
    created_by: str | None = None,
) -> CustomRegoRuleModel:
    """Create a new custom Rego rule after validating syntax.

    Args:
        db: Async database session.
        organization_id: The owning organization.
        rule_id: User-defined rule identifier.
        name: Human-readable rule name.
        rego_content: Rego policy source code.
        description: Optional rule description.
        created_by: Actor who created the rule.

    Returns:
        The persisted CustomRegoRuleModel instance.

    Raises:
        ValueError: If Rego syntax is invalid.
    """
    # Validate Rego syntax via OPA compiler
    validation = await validate_rego_syntax(rego_content)
    if not validation["valid"]:
        raise ValueError(
            f"Invalid Rego syntax: {validation['errors']}"
        )

    now = datetime.now(timezone.utc)
    rule = CustomRegoRuleModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        rule_id=rule_id,
        name=name,
        description=description,
        rego_content=rego_content,
        version=1,
        is_active=True,
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    db.add(rule)

    # Store initial version in history
    version_record = RegoRuleVersionModel(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        organization_id=organization_id,
        version=1,
        rego_content=rego_content,
        created_by=created_by,
        created_at=now,
    )
    db.add(version_record)

    # Audit log
    await record_audit_log(
        db,
        organization_id=organization_id,
        action="rule_created",
        rule_id=rule_id,
        actor=created_by or "system",
        details={"name": name, "version": 1},
    )

    await db.flush()
    return rule


async def test_rule(
    rego_content: str,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a Rego rule against sample input and return the result.

    Args:
        rego_content: The Rego source code to test.
        input_data: Sample input document for evaluation.

    Returns:
        Dict with 'passed' (bool), 'result', and optional 'error'.
    """
    opa = OPAClient()
    try:
        result = await opa.test_rule(rego_content, input_data)
        return {
            "passed": result.get("passed", False),
            "result": result.get("result"),
            "violations": result.get("violations", []),
            "error": result.get("error"),
        }
    except OPAClientError as e:
        logger.error("Rule test failed: %s", e)
        return {"passed": False, "result": None, "violations": [], "error": str(e)}


async def update_rule(
    db: AsyncSession,
    *,
    rule_db_id: str,
    organization_id: str,
    rego_content: str,
    updated_by: str | None = None,
) -> CustomRegoRuleModel:
    """Update a rule by creating a new version and storing the previous one.

    Args:
        db: Async database session.
        rule_db_id: The database primary key of the rule.
        organization_id: The owning organization.
        rego_content: New Rego source code.
        updated_by: Actor performing the update.

    Returns:
        The updated CustomRegoRuleModel instance.

    Raises:
        ValueError: If Rego syntax is invalid or rule not found.
    """
    # Validate new Rego content
    validation = await validate_rego_syntax(rego_content)
    if not validation["valid"]:
        raise ValueError(
            f"Invalid Rego syntax: {validation['errors']}"
        )

    # Fetch existing rule
    result = await db.execute(
        select(CustomRegoRuleModel).where(
            CustomRegoRuleModel.id == rule_db_id,
            CustomRegoRuleModel.organization_id == organization_id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise ValueError(f"Rule not found: {rule_db_id}")

    now = datetime.now(timezone.utc)
    new_version = rule.version + 1

    # Store current version in history before overwriting
    version_record = RegoRuleVersionModel(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        organization_id=organization_id,
        version=new_version,
        rego_content=rego_content,
        created_by=updated_by,
        created_at=now,
    )
    db.add(version_record)

    # Update the active rule
    rule.rego_content = rego_content
    rule.version = new_version
    rule.updated_at = now

    # Audit log
    await record_audit_log(
        db,
        organization_id=organization_id,
        action="rule_updated",
        rule_id=rule.rule_id,
        actor=updated_by or "system",
        details={"new_version": new_version},
    )

    await db.flush()
    return rule


async def rollback_rule(
    db: AsyncSession,
    *,
    rule_db_id: str,
    organization_id: str,
    target_version: int | None = None,
    rolled_back_by: str | None = None,
) -> CustomRegoRuleModel:
    """Restore a previous version of a rule as the active version.

    If target_version is None, rolls back to the immediately previous version.

    Args:
        db: Async database session.
        rule_db_id: The database primary key of the rule.
        organization_id: The owning organization.
        target_version: Specific version to restore (defaults to previous).
        rolled_back_by: Actor performing the rollback.

    Returns:
        The updated CustomRegoRuleModel with restored content.

    Raises:
        ValueError: If rule or target version not found.
    """
    # Fetch existing rule
    result = await db.execute(
        select(CustomRegoRuleModel).where(
            CustomRegoRuleModel.id == rule_db_id,
            CustomRegoRuleModel.organization_id == organization_id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise ValueError(f"Rule not found: {rule_db_id}")

    # Determine target version
    if target_version is None:
        target_version = rule.version - 1

    if target_version < 1:
        raise ValueError("Cannot rollback: no previous version exists")

    # Fetch the target version from history
    version_result = await db.execute(
        select(RegoRuleVersionModel).where(
            RegoRuleVersionModel.rule_id == rule.id,
            RegoRuleVersionModel.version == target_version,
        )
    )
    version_record = version_result.scalar_one_or_none()
    if not version_record:
        raise ValueError(f"Version {target_version} not found for rule {rule_db_id}")

    now = datetime.now(timezone.utc)
    new_version = rule.version + 1

    # Store the rollback as a new version entry
    rollback_version = RegoRuleVersionModel(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        organization_id=organization_id,
        version=new_version,
        rego_content=version_record.rego_content,
        created_by=rolled_back_by,
        created_at=now,
    )
    db.add(rollback_version)

    # Restore the rule content
    rule.rego_content = version_record.rego_content
    rule.version = new_version
    rule.updated_at = now

    # Audit log
    await record_audit_log(
        db,
        organization_id=organization_id,
        action="rule_rolled_back",
        rule_id=rule.rule_id,
        actor=rolled_back_by or "system",
        details={"restored_version": target_version, "new_version": new_version},
    )

    await db.flush()
    return rule


async def list_rule_versions(
    db: AsyncSession,
    *,
    rule_db_id: str,
) -> list[RegoRuleVersionModel]:
    """Retrieve version history for a rule.

    Args:
        db: Async database session.
        rule_db_id: The database primary key of the rule.

    Returns:
        List of RegoRuleVersionModel ordered by version descending.
    """
    result = await db.execute(
        select(RegoRuleVersionModel)
        .where(RegoRuleVersionModel.rule_id == rule_db_id)
        .order_by(RegoRuleVersionModel.version.desc())
    )
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════════════
# Task 10.3 — Policy Hierarchy and Conflict Resolution
# ═══════════════════════════════════════════════════════════════════════════════

# Hierarchy levels ordered from least specific to most specific
HIERARCHY_LEVELS = ["organization", "team", "project"]


async def resolve_policy_hierarchy(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str | None = None,
    project_id: str | None = None,
) -> list[PolicyHierarchyModel]:
    """Merge policies from org → team → project levels.

    Lower (more specific) levels inherit from higher levels and can override.

    Args:
        db: Async database session.
        organization_id: The organization ID.
        team_id: Optional team ID for team-level policies.
        project_id: Optional project ID for project-level policies.

    Returns:
        Merged list of PolicyHierarchyModel representing effective policies.
    """
    # Fetch org-level policies
    org_q = select(PolicyHierarchyModel).where(
        PolicyHierarchyModel.organization_id == organization_id,
        PolicyHierarchyModel.level == "organization",
        PolicyHierarchyModel.is_active == True,  # noqa: E712
    )
    org_result = await db.execute(org_q)
    org_policies = list(org_result.scalars().all())

    # Fetch team-level policies
    team_policies: list[PolicyHierarchyModel] = []
    if team_id:
        team_q = select(PolicyHierarchyModel).where(
            PolicyHierarchyModel.organization_id == organization_id,
            PolicyHierarchyModel.level == "team",
            PolicyHierarchyModel.level_id == team_id,
            PolicyHierarchyModel.is_active == True,  # noqa: E712
        )
        team_result = await db.execute(team_q)
        team_policies = list(team_result.scalars().all())

    # Fetch project-level policies
    project_policies: list[PolicyHierarchyModel] = []
    if project_id:
        project_q = select(PolicyHierarchyModel).where(
            PolicyHierarchyModel.organization_id == organization_id,
            PolicyHierarchyModel.level == "project",
            PolicyHierarchyModel.level_id == project_id,
            PolicyHierarchyModel.is_active == True,  # noqa: E712
        )
        project_result = await db.execute(project_q)
        project_policies = list(project_result.scalars().all())

    return resolve_conflicts(org_policies, team_policies, project_policies)


def resolve_conflicts(
    org_policies: list[PolicyHierarchyModel],
    team_policies: list[PolicyHierarchyModel],
    project_policies: list[PolicyHierarchyModel],
) -> list[PolicyHierarchyModel]:
    """Resolve policy conflicts across hierarchy levels.

    Resolution rules:
    - Most specific (lowest-level) wins for the same rule_id.
    - At the same level, explicit deny (block) > allow (alert).

    Args:
        org_policies: Organization-level policies.
        team_policies: Team-level policies.
        project_policies: Project-level policies.

    Returns:
        Merged list with conflicts resolved.
    """
    # Build a dict keyed by rule_id, most specific wins
    merged: dict[str, PolicyHierarchyModel] = {}

    # Start with org-level (least specific)
    for policy in org_policies:
        merged[policy.rule_id] = policy

    # Team-level overrides org-level
    for policy in team_policies:
        merged[policy.rule_id] = policy

    # Project-level overrides team-level
    for policy in project_policies:
        merged[policy.rule_id] = policy

    # At same level, if there are duplicates, deny > allow
    # (This is already handled by the override logic above since we take the last one.
    #  But if multiple policies at the same level have the same rule_id, pick deny.)
    # Group by (level, rule_id) and resolve same-level conflicts
    level_groups: dict[tuple[str, str], list[PolicyHierarchyModel]] = {}
    for policy in list(merged.values()):
        key = (policy.level, policy.rule_id)
        level_groups.setdefault(key, []).append(policy)

    final: dict[str, PolicyHierarchyModel] = {}
    for (_level, rule_id), policies in level_groups.items():
        if len(policies) == 1:
            final[rule_id] = policies[0]
        else:
            # deny (block) > allow (alert) at same level
            blocking = [p for p in policies if p.enforcement_mode == "block"]
            if blocking:
                final[rule_id] = blocking[0]
            else:
                # auto_remediate > alert
                auto_rem = [p for p in policies if p.enforcement_mode == "auto_remediate"]
                if auto_rem:
                    final[rule_id] = auto_rem[0]
                else:
                    final[rule_id] = policies[0]

    return list(final.values())


async def apply_overrides(
    db: AsyncSession,
    *,
    organization_id: str,
    level: str,
    level_id: str,
    rule_id: str,
    enforcement_mode: str,
    overridden_by: str,
    justification: str,
) -> PolicyHierarchyModel:
    """Record a policy override with principal, timestamp, and justification.

    Args:
        db: Async database session.
        organization_id: The owning organization.
        level: Hierarchy level (organization, team, project).
        level_id: ID of the entity at that level.
        rule_id: The rule being overridden.
        enforcement_mode: New enforcement mode.
        overridden_by: Actor performing the override.
        justification: Reason for the override.

    Returns:
        The new or updated PolicyHierarchyModel.
    """
    if level not in HIERARCHY_LEVELS:
        raise ValueError(f"Invalid level: {level}. Must be one of {HIERARCHY_LEVELS}")

    now = datetime.now(timezone.utc)

    # Check if an existing policy at this level already exists for this rule
    existing_q = select(PolicyHierarchyModel).where(
        PolicyHierarchyModel.organization_id == organization_id,
        PolicyHierarchyModel.level == level,
        PolicyHierarchyModel.level_id == level_id,
        PolicyHierarchyModel.rule_id == rule_id,
        PolicyHierarchyModel.is_active == True,  # noqa: E712
    )
    existing_result = await db.execute(existing_q)
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Update existing policy with override info
        existing.enforcement_mode = enforcement_mode
        existing.is_override = True
        existing.override_justification = justification
        existing.overridden_by = overridden_by
        existing.overridden_at = now
        existing.updated_at = now
        policy = existing
    else:
        # Create new policy entry
        policy = PolicyHierarchyModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            level=level,
            level_id=level_id,
            rule_id=rule_id,
            enforcement_mode=enforcement_mode,
            is_override=True,
            override_justification=justification,
            overridden_by=overridden_by,
            overridden_at=now,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(policy)

    # Audit log
    await record_audit_log(
        db,
        organization_id=organization_id,
        action="mode_changed",
        rule_id=rule_id,
        actor=overridden_by,
        details={
            "level": level,
            "level_id": level_id,
            "enforcement_mode": enforcement_mode,
            "justification": justification,
        },
    )

    await db.flush()
    return policy


async def get_effective_policies(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str | None = None,
    project_id: str | None = None,
) -> list[PolicyHierarchyModel]:
    """Return the merged policy set for a resource context.

    This is the public-facing function that resolves the full hierarchy
    and returns the effective set of policies that apply.

    Args:
        db: Async database session.
        organization_id: The organization ID.
        team_id: Optional team context.
        project_id: Optional project context.

    Returns:
        List of resolved PolicyHierarchyModel entries.
    """
    return await resolve_policy_hierarchy(
        db,
        organization_id=organization_id,
        team_id=team_id,
        project_id=project_id,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Task 10.5 — Enforcement Modes and Exception Management
# ═══════════════════════════════════════════════════════════════════════════════


async def apply_enforcement_mode(
    *,
    enforcement_mode: str,
    organization_id: str,
    resource_id: str,
    rule_id: str,
    finding_producer: FindingProducer | None = None,
) -> dict[str, Any]:
    """Route action based on enforcement mode.

    Modes:
    - "alert": Generate a finding/alert only.
    - "block": Prevent the deployment/action.
    - "auto_remediate": Trigger automatic remediation via Kafka event.

    Args:
        enforcement_mode: One of alert, block, auto_remediate.
        organization_id: The owning organization.
        resource_id: The affected resource.
        rule_id: The rule that triggered enforcement.
        finding_producer: Optional FindingProducer for publishing events.

    Returns:
        Dict describing the action taken.
    """
    if enforcement_mode == "alert":
        logger.info(
            "Policy enforcement [alert]: rule=%s resource=%s org=%s",
            rule_id, resource_id, organization_id,
        )
        return {
            "action": "alert",
            "rule_id": rule_id,
            "resource_id": resource_id,
            "message": "Finding generated for policy violation",
        }

    elif enforcement_mode == "block":
        logger.info(
            "Policy enforcement [block]: rule=%s resource=%s org=%s",
            rule_id, resource_id, organization_id,
        )
        return {
            "action": "block",
            "rule_id": rule_id,
            "resource_id": resource_id,
            "message": "Deployment blocked due to policy violation",
        }

    elif enforcement_mode == "auto_remediate":
        logger.info(
            "Policy enforcement [auto_remediate]: rule=%s resource=%s org=%s",
            rule_id, resource_id, organization_id,
        )
        # Publish auto-remediation event via Kafka
        if finding_producer:
            await finding_producer.publish_policy_auto_remediate(
                organization_id=organization_id,
                resource_id=resource_id,
                rule_id=rule_id,
                remediation_action="auto_fix",
                enforcement_mode=enforcement_mode,
            )
        return {
            "action": "auto_remediate",
            "rule_id": rule_id,
            "resource_id": resource_id,
            "message": "Auto-remediation triggered for policy violation",
        }

    else:
        raise ValueError(
            f"Invalid enforcement mode: {enforcement_mode}. "
            "Must be one of: alert, block, auto_remediate"
        )


async def create_exception(
    db: AsyncSession,
    *,
    organization_id: str,
    rule_id: str,
    resource_id: str,
    justification: str,
    granted_by: str,
    expires_at: datetime,
) -> PolicyExceptionModel:
    """Create a policy exception with validation.

    Validates:
    - Expiry must be ≤ 365 days from now.
    - Justification must be non-empty.
    - granted_by must be provided.

    Args:
        db: Async database session.
        organization_id: The owning organization.
        rule_id: The rule to exempt.
        resource_id: The resource to exempt.
        justification: Reason for the exception.
        granted_by: Actor granting the exception.
        expires_at: When the exception expires.

    Returns:
        The persisted PolicyExceptionModel.

    Raises:
        ValueError: If validation fails.
    """
    now = datetime.now(timezone.utc)
    max_expiry = now + timedelta(days=settings.policy_exception_max_days)

    # Ensure expires_at is timezone-aware for comparison
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at > max_expiry:
        raise ValueError(
            f"Exception expiry cannot exceed {settings.policy_exception_max_days} days "
            f"from now. Maximum allowed: {max_expiry.isoformat()}"
        )

    if expires_at <= now:
        raise ValueError("Exception expiry must be in the future")

    if not justification or not justification.strip():
        raise ValueError("Justification is required and cannot be empty")

    if not granted_by or not granted_by.strip():
        raise ValueError("granted_by actor is required")

    exception = PolicyExceptionModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        rule_id=rule_id,
        resource_id=resource_id,
        justification=justification.strip(),
        granted_by=granted_by.strip(),
        expires_at=expires_at,
        is_active=True,
        created_at=now,
    )
    db.add(exception)

    # Audit log
    await record_audit_log(
        db,
        organization_id=organization_id,
        action="exception_granted",
        rule_id=rule_id,
        resource_id=resource_id,
        actor=granted_by,
        details={
            "justification": justification.strip(),
            "expires_at": expires_at.isoformat(),
        },
    )

    await db.flush()
    return exception


async def check_exception_active(
    db: AsyncSession,
    *,
    organization_id: str,
    rule_id: str,
    resource_id: str,
) -> bool:
    """Determine if an active exception applies to a resource+rule combination.

    Args:
        db: Async database session.
        organization_id: The owning organization.
        rule_id: The rule to check.
        resource_id: The resource to check.

    Returns:
        True if an active, non-expired exception exists.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PolicyExceptionModel).where(
            PolicyExceptionModel.organization_id == organization_id,
            PolicyExceptionModel.rule_id == rule_id,
            PolicyExceptionModel.resource_id == resource_id,
            PolicyExceptionModel.is_active == True,  # noqa: E712
            PolicyExceptionModel.expires_at > now,
        )
    )
    return result.scalar_one_or_none() is not None


async def expire_exceptions(db: AsyncSession) -> int:
    """Scheduled job to deactivate all expired exceptions.

    Args:
        db: Async database session.

    Returns:
        Number of exceptions deactivated.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        update(PolicyExceptionModel)
        .where(
            PolicyExceptionModel.is_active == True,  # noqa: E712
            PolicyExceptionModel.expires_at <= now,
        )
        .values(is_active=False)
    )
    result = await db.execute(stmt)
    count = result.rowcount
    if count > 0:
        logger.info("Expired %d policy exceptions", count)
    await db.flush()
    return count


async def record_audit_log(
    db: AsyncSession,
    *,
    organization_id: str,
    action: str,
    actor: str,
    rule_id: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> PolicyAuditLogModel:
    """Log a policy change with actor and timestamp.

    Args:
        db: Async database session.
        organization_id: The owning organization.
        action: The action type (rule_created, rule_updated, exception_granted, mode_changed).
        actor: Who performed the action.
        rule_id: Optional associated rule.
        resource_id: Optional associated resource.
        details: Optional additional context.

    Returns:
        The persisted PolicyAuditLogModel.
    """
    log_entry = PolicyAuditLogModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        action=action,
        rule_id=rule_id,
        resource_id=resource_id,
        actor=actor,
        details=details or {},
        timestamp=datetime.now(timezone.utc),
    )
    db.add(log_entry)
    await db.flush()
    return log_entry
