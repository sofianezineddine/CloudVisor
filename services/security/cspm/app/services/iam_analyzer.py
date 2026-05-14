"""IAM Analyzer — business logic for identity risk analysis.

Provides functions for:
- Effective permission computation (flatten policies, SCPs, boundaries)
- Excess privilege detection and severity assignment
- Least-privilege policy generation
- Dormant identity detection
- Admin/root MFA issue detection
- Service account risk scoring
- Cross-account trust analysis and permissiveness detection
- Privilege escalation path discovery and severity assignment
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_cspm_settings

logger = logging.getLogger(__name__)

# ─── Severity Constants ───────────────────────────────────────────────────────

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"
SEVERITY_INFO = "INFO"


# ─── Effective Permission Computation ─────────────────────────────────────────


def compute_effective_permissions(
    attached_policies: list[dict[str, Any]],
    scp_policies: list[dict[str, Any]] | None = None,
    permission_boundaries: list[dict[str, Any]] | None = None,
) -> set[str]:
    """Compute effective permissions for an IAM identity.

    Algorithm:
      1. Collect all attached policies (inline + managed)
      2. Expand policy statements into individual permissions (Allow)
      3. Apply SCP restrictions (intersection with SCP allows)
      4. Apply permission boundaries (intersection with boundary allows)
      5. Remove explicitly denied permissions

    Result = (Union of all Allow statements) ∩ SCP_allows ∩ Boundary_allows - Explicit_denies

    Args:
        attached_policies: List of policy documents with Statement lists.
            Each statement has Effect ("Allow"/"Deny") and Action (list of permission strings).
        scp_policies: Optional list of Service Control Policy documents.
            If provided, effective permissions are intersected with SCP allows.
        permission_boundaries: Optional list of permission boundary policy documents.
            If provided, effective permissions are intersected with boundary allows.

    Returns:
        Set of effective permission strings after all restrictions are applied.
    """
    # Step 1-2: Expand all Allow and Deny statements
    all_allows: set[str] = set()
    explicit_denies: set[str] = set()

    for policy in attached_policies:
        statements = policy.get("Statement", [])
        for statement in statements:
            effect = statement.get("Effect", "")
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]

            if effect == "Allow":
                all_allows.update(actions)
            elif effect == "Deny":
                explicit_denies.update(actions)

    effective = all_allows.copy()

    # Step 3: Apply SCP restrictions (intersection)
    if scp_policies:
        scp_allows = _extract_allows_from_policies(scp_policies)
        if scp_allows:
            effective = effective.intersection(scp_allows)

    # Step 4: Apply permission boundaries (intersection)
    if permission_boundaries:
        boundary_allows = _extract_allows_from_policies(permission_boundaries)
        if boundary_allows:
            effective = effective.intersection(boundary_allows)

    # Step 5: Remove explicit denies
    effective -= explicit_denies

    logger.debug(
        "Computed effective permissions: %d allows, %d denies, %d effective",
        len(all_allows),
        len(explicit_denies),
        len(effective),
    )
    return effective


def _extract_allows_from_policies(policies: list[dict[str, Any]]) -> set[str]:
    """Extract all Allow actions from a list of policy documents."""
    allows: set[str] = set()
    for policy in policies:
        statements = policy.get("Statement", [])
        for statement in statements:
            if statement.get("Effect") == "Allow":
                actions = statement.get("Action", [])
                if isinstance(actions, str):
                    actions = [actions]
                allows.update(actions)
    return allows


# ─── Excess Permission Analysis ──────────────────────────────────────────────


def compute_excess_permissions(
    granted_permissions: set[str],
    used_permissions: set[str],
) -> set[str]:
    """Compute excess permissions as the set difference of granted vs used.

    Args:
        granted_permissions: Set of all effective permissions granted to the identity.
        used_permissions: Set of permissions actually used during the lookback period.

    Returns:
        Set of permissions that are granted but never used.
    """
    excess = granted_permissions - used_permissions
    logger.debug(
        "Excess permissions: %d granted, %d used, %d excess",
        len(granted_permissions),
        len(used_permissions),
        len(excess),
    )
    return excess


def compute_excess_ratio(
    granted_permissions: set[str],
    excess_permissions: set[str],
) -> float:
    """Compute the ratio of excess permissions to total granted permissions.

    Args:
        granted_permissions: Set of all effective permissions granted.
        excess_permissions: Set of permissions that are granted but unused.

    Returns:
        Ratio between 0.0 and 1.0. Returns 0.0 if no permissions are granted.
    """
    if not granted_permissions:
        return 0.0
    ratio = len(excess_permissions) / len(granted_permissions)
    return min(ratio, 1.0)


def assign_severity_from_ratio(excess_ratio: float) -> str:
    """Assign severity proportional to the excess privilege ratio.

    Severity thresholds:
      - >= 0.9: CRITICAL (90%+ unused permissions)
      - >= 0.7: HIGH (70%+ unused permissions)
      - >= 0.3: MEDIUM (30%+ unused permissions, matches default threshold)
      - < 0.3: LOW

    Args:
        excess_ratio: The ratio of excess permissions (0.0 to 1.0).

    Returns:
        Severity string: CRITICAL, HIGH, MEDIUM, or LOW.
    """
    if excess_ratio >= 0.9:
        return SEVERITY_CRITICAL
    elif excess_ratio >= 0.7:
        return SEVERITY_HIGH
    elif excess_ratio >= 0.3:
        return SEVERITY_MEDIUM
    else:
        return SEVERITY_LOW


# ─── Least-Privilege Policy Generation ───────────────────────────────────────


def generate_least_privilege_policy(
    used_permissions: set[str],
    identity_arn: str | None = None,
) -> dict[str, Any]:
    """Generate a least-privilege policy containing only used permissions.

    Creates an IAM policy document that grants only the permissions the identity
    actually used during the lookback period.

    Args:
        used_permissions: Set of permissions actually used by the identity.
        identity_arn: Optional ARN of the identity for policy naming.

    Returns:
        A policy document dict with Version, Statement, and metadata.
    """
    if not used_permissions:
        return {
            "Version": "2012-10-17",
            "Statement": [],
            "metadata": {
                "description": "No permissions used during lookback period",
                "identity_arn": identity_arn,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    # Group permissions by service prefix for cleaner policy
    service_groups: dict[str, list[str]] = {}
    for perm in sorted(used_permissions):
        parts = perm.split(":", 1)
        service = parts[0] if len(parts) > 1 else "unknown"
        service_groups.setdefault(service, []).append(perm)

    statements: list[dict[str, Any]] = []
    for service, actions in sorted(service_groups.items()):
        statements.append({
            "Sid": f"LeastPrivilege{service.replace('-', '').title()}",
            "Effect": "Allow",
            "Action": sorted(actions),
            "Resource": "*",
        })

    policy = {
        "Version": "2012-10-17",
        "Statement": statements,
        "metadata": {
            "description": "Least-privilege policy based on actual usage",
            "identity_arn": identity_arn,
            "permission_count": len(used_permissions),
            "service_count": len(service_groups),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    logger.info(
        "Generated least-privilege policy for %s: %d permissions across %d services",
        identity_arn or "unknown",
        len(used_permissions),
        len(service_groups),
    )
    return policy


# ─── Dormant Identity Detection ──────────────────────────────────────────────


def detect_dormant_identity(
    last_activity_at: datetime | None,
    lookback_days: int | None = None,
) -> bool:
    """Detect whether an identity is dormant based on last activity.

    An identity is considered dormant if it has not been used for more than
    the configured threshold (default 90 days).

    Args:
        last_activity_at: Timestamp of the identity's last activity.
            If None, the identity is considered dormant.
        lookback_days: Optional override for the dormant threshold in days.
            Defaults to settings.iam_dormant_threshold_days.

    Returns:
        True if the identity is dormant, False otherwise.
    """
    settings = get_cspm_settings()
    threshold_days = lookback_days if lookback_days is not None else settings.iam_dormant_threshold_days

    if last_activity_at is None:
        logger.debug("Identity has no recorded activity — marking as dormant")
        return True

    # Ensure timezone-aware comparison
    now = datetime.now(timezone.utc)
    if last_activity_at.tzinfo is None:
        last_activity_at = last_activity_at.replace(tzinfo=timezone.utc)

    days_inactive = (now - last_activity_at).days
    is_dormant = days_inactive >= threshold_days

    logger.debug(
        "Dormant check: last_activity=%s, days_inactive=%d, threshold=%d, dormant=%s",
        last_activity_at.isoformat(),
        days_inactive,
        threshold_days,
        is_dormant,
    )
    return is_dormant


# ─── Admin MFA Issue Detection ───────────────────────────────────────────────


def detect_admin_mfa_issues(
    is_admin: bool,
    has_mfa: bool,
    is_root: bool = False,
    last_activity_at: datetime | None = None,
    daily_usage_threshold_days: int = 7,
) -> list[dict[str, Any]]:
    """Detect MFA and usage issues for admin/root accounts.

    Checks:
      1. Admin or root without MFA → CRITICAL
      2. Admin or root used for daily operations → HIGH

    Args:
        is_admin: Whether the identity has admin-level privileges.
        has_mfa: Whether MFA is enabled for the identity.
        is_root: Whether this is the root account.
        last_activity_at: Timestamp of last activity for usage check.
        daily_usage_threshold_days: Number of recent days to consider as
            "daily operations" usage (default 7 days).

    Returns:
        List of finding dicts, each with severity, issue_type, and description.
    """
    findings: list[dict[str, Any]] = []

    if not is_admin and not is_root:
        return findings

    identity_type = "root account" if is_root else "admin account"

    # Check 1: Admin/root without MFA → CRITICAL
    if not has_mfa:
        findings.append({
            "severity": SEVERITY_CRITICAL,
            "issue_type": "admin_no_mfa",
            "description": (
                f"The {identity_type} does not have MFA enabled. "
                "This poses a critical security risk as compromised credentials "
                "would grant full access without a second factor."
            ),
        })
        logger.warning("CRITICAL: %s without MFA detected", identity_type)

    # Check 2: Admin/root used for daily operations → HIGH
    if last_activity_at is not None:
        now = datetime.now(timezone.utc)
        if last_activity_at.tzinfo is None:
            last_activity_at = last_activity_at.replace(tzinfo=timezone.utc)

        days_since_activity = (now - last_activity_at).days
        if days_since_activity <= daily_usage_threshold_days:
            findings.append({
                "severity": SEVERITY_HIGH,
                "issue_type": "admin_daily_usage",
                "description": (
                    f"The {identity_type} has been used within the last "
                    f"{daily_usage_threshold_days} days for operations. "
                    "Admin/root accounts should be reserved for emergency use. "
                    "Delegate day-to-day operations to a less-privileged role."
                ),
            })
            logger.info(
                "HIGH: %s used for daily operations (last active %d days ago)",
                identity_type,
                days_since_activity,
            )

    return findings


# ─── Service Account Risk Score ──────────────────────────────────────────────


def compute_service_account_risk_score(
    permission_breadth: int,
    resource_scope: list[str],
    key_age_days: int,
) -> int:
    """Compute a risk score (0-100) for a service account.

    The score increases with:
      - permission_breadth: Number of distinct permissions (more = riskier)
      - resource_scope: Number of resource ARN patterns accessible (more = riskier)
      - key_age_days: Days since last key rotation (older = riskier)

    Scoring formula:
      - Breadth component (0-40): scaled by permission count
      - Scope component (0-30): scaled by resource scope size
      - Rotation component (0-30): scaled by key age

    Args:
        permission_breadth: Number of distinct permissions granted.
        resource_scope: List of resource ARN patterns the account can access.
        key_age_days: Number of days since the last key rotation.

    Returns:
        Risk score between 0 and 100.
    """
    settings = get_cspm_settings()

    # Breadth component: 0-40 points
    # Scale: 0 perms = 0, 50+ perms = 40
    breadth_score = min(permission_breadth / 50.0, 1.0) * 40.0

    # Scope component: 0-30 points
    # Scale: 0 resources = 0, 20+ resource patterns = 30
    scope_size = len(resource_scope)
    scope_score = min(scope_size / 20.0, 1.0) * 30.0

    # Rotation component: 0-30 points
    # Scale: 0 days = 0, threshold days (90) or more = 30
    rotation_threshold = settings.iam_key_rotation_threshold_days
    rotation_score = min(key_age_days / float(rotation_threshold), 1.0) * 30.0

    total_score = int(breadth_score + scope_score + rotation_score)
    total_score = max(0, min(total_score, 100))

    logger.debug(
        "Service account risk score: breadth=%d(%.1f), scope=%d(%.1f), "
        "key_age=%d(%.1f), total=%d",
        permission_breadth,
        breadth_score,
        scope_size,
        scope_score,
        key_age_days,
        rotation_score,
        total_score,
    )
    return total_score


# ─── Cross-Account Trust Analysis ────────────────────────────────────────────


def analyze_cross_account_trusts(
    trust_policies: list[dict[str, Any]],
    source_account_id: str,
) -> list[dict[str, Any]]:
    """Discover and classify cross-account trust relationships from IAM role trust policies.

    Parses trust policy documents to extract cross-account trust relationships,
    determines the trusted principal and conditions, and classifies each trust
    for permissiveness.

    Args:
        trust_policies: List of IAM role trust policy documents. Each document
            should contain a "Statement" list with Principal and Condition fields.
            Expected structure:
            {
                "RoleName": "...",
                "RoleArn": "...",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                        "Action": "sts:AssumeRole",
                        "Condition": {"StringEquals": {"sts:ExternalId": "..."}}
                    }
                ]
            }
        source_account_id: The AWS account ID that owns the roles being analyzed.

    Returns:
        List of trust relationship dicts, each containing:
            - source_account_id: The account that owns the role
            - target_account_id: The account being trusted (extracted from principal ARN)
            - trusted_principal: The full principal ARN or identifier
            - conditions: Dict of conditions from the trust policy statement
            - has_external_id: Whether an external ID condition is present
            - has_wildcard_principal: Whether the principal is a wildcard ("*")
            - is_overly_permissive: Whether the trust is overly permissive
            - risk_score: Computed risk score (0-100)
            - role_name: The name of the role with this trust
            - role_arn: The ARN of the role with this trust
    """
    trust_relationships: list[dict[str, Any]] = []

    for policy_doc in trust_policies:
        role_name = policy_doc.get("RoleName", "unknown")
        role_arn = policy_doc.get("RoleArn", "")
        statements = policy_doc.get("Statement", [])

        for statement in statements:
            effect = statement.get("Effect", "")
            if effect != "Allow":
                continue

            principals = _extract_principals(statement)
            conditions = statement.get("Condition", {})
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]

            for principal in principals:
                target_account_id = _extract_account_id_from_principal(principal)

                # Skip same-account trusts — we only care about cross-account
                if target_account_id == source_account_id:
                    continue

                has_wildcard = principal == "*"
                has_external_id = _check_external_id_condition(conditions)
                is_permissive = detect_overly_permissive_trust(
                    trusted_principal=principal,
                    conditions=conditions,
                )
                risk_score = _compute_trust_risk_score(
                    has_wildcard_principal=has_wildcard,
                    has_external_id=has_external_id,
                    actions=actions,
                    conditions=conditions,
                )

                trust_rel = {
                    "source_account_id": source_account_id,
                    "target_account_id": target_account_id,
                    "trusted_principal": principal,
                    "conditions": conditions,
                    "has_external_id": has_external_id,
                    "has_wildcard_principal": has_wildcard,
                    "is_overly_permissive": is_permissive,
                    "risk_score": risk_score,
                    "role_name": role_name,
                    "role_arn": role_arn,
                }
                trust_relationships.append(trust_rel)

    logger.info(
        "Analyzed cross-account trusts for account %s: found %d relationships",
        source_account_id,
        len(trust_relationships),
    )
    return trust_relationships


def detect_overly_permissive_trust(
    trusted_principal: str,
    conditions: dict[str, Any],
) -> bool:
    """Determine whether a cross-account trust relationship is overly permissive.

    A trust is considered overly permissive if ANY of the following are true:
      1. The trusted principal is a wildcard ("*"), allowing any AWS account to assume the role
      2. The trust policy is missing an external ID condition, which is a best practice
         for cross-account role assumption to prevent confused deputy attacks

    Args:
        trusted_principal: The principal ARN or identifier in the trust policy.
            A value of "*" indicates any principal can assume the role.
        conditions: The Condition block from the trust policy statement.
            Should contain {"StringEquals": {"sts:ExternalId": "..."}} for safe trusts.

    Returns:
        True if the trust is overly permissive, False otherwise.
    """
    # Check 1: Wildcard principal
    if trusted_principal == "*":
        logger.warning(
            "Overly permissive trust detected: wildcard principal '*'"
        )
        return True

    # Check 2: Missing external ID condition
    has_external_id = _check_external_id_condition(conditions)
    if not has_external_id:
        logger.warning(
            "Overly permissive trust detected: missing external ID for principal %s",
            trusted_principal,
        )
        return True

    return False


async def store_trust_in_graph(
    graph_client: Any,
    trust_relationship: dict[str, Any],
    organization_id: str,
) -> dict[str, Any]:
    """Persist a cross-account trust relationship as an edge in Neo4j via the graph client.

    Creates or updates a TRUSTS relationship between two account nodes in the
    asset graph. The edge contains metadata about the trust conditions, risk score,
    and permissiveness classification.

    Args:
        graph_client: An instance of GraphClient from app.core.graph_client.
        trust_relationship: A trust relationship dict as returned by
            analyze_cross_account_trusts(). Must contain source_account_id,
            target_account_id, trusted_principal, conditions, risk_score, etc.
        organization_id: The tenant organization ID for multi-tenant isolation.

    Returns:
        The result dict from the graph service containing the created/updated
        relationship data.

    Raises:
        GraphClientError: If the graph service request fails.
    """
    source_account = trust_relationship["source_account_id"]
    target_account = trust_relationship["target_account_id"]
    trusted_principal = trust_relationship["trusted_principal"]
    conditions = trust_relationship.get("conditions", {})
    risk_score = trust_relationship.get("risk_score", 0)
    is_overly_permissive = trust_relationship.get("is_overly_permissive", False)
    has_external_id = trust_relationship.get("has_external_id", False)
    has_wildcard_principal = trust_relationship.get("has_wildcard_principal", False)
    role_arn = trust_relationship.get("role_arn", "")

    # Use a MERGE Cypher query to create or update the trust edge
    cypher = """
    MERGE (source:AWSAccount {account_id: $source_account, org_id: $org_id})
    MERGE (target:AWSAccount {account_id: $target_account, org_id: $org_id})
    MERGE (source)-[r:TRUSTS {trusted_principal: $trusted_principal}]->(target)
    SET r.conditions = $conditions,
        r.risk_score = $risk_score,
        r.is_overly_permissive = $is_overly_permissive,
        r.has_external_id = $has_external_id,
        r.has_wildcard_principal = $has_wildcard_principal,
        r.role_arn = $role_arn,
        r.org_id = $org_id,
        r.updated_at = datetime()
    RETURN r
    """

    parameters = {
        "source_account": source_account,
        "target_account": target_account,
        "trusted_principal": trusted_principal,
        "conditions": str(conditions),  # Neo4j stores as string for complex dicts
        "risk_score": risk_score,
        "is_overly_permissive": is_overly_permissive,
        "has_external_id": has_external_id,
        "has_wildcard_principal": has_wildcard_principal,
        "role_arn": role_arn,
        "org_id": organization_id,
    }

    logger.info(
        "Storing trust edge in graph: %s -> %s (principal=%s, risk=%d)",
        source_account,
        target_account,
        trusted_principal,
        risk_score,
    )

    result = await graph_client.query(cypher=cypher, parameters=parameters)
    return result


# ─── Cross-Account Trust Helpers ─────────────────────────────────────────────


def _extract_principals(statement: dict[str, Any]) -> list[str]:
    """Extract all principal identifiers from a trust policy statement.

    Handles the various formats AWS uses for Principal:
      - {"AWS": "arn:..."}
      - {"AWS": ["arn:...", "arn:..."]}
      - {"Service": "..."}
      - "*"

    Args:
        statement: A single trust policy statement dict.

    Returns:
        List of principal strings (ARNs, account IDs, or "*").
    """
    principal = statement.get("Principal", {})

    if isinstance(principal, str):
        return [principal]

    principals: list[str] = []
    if isinstance(principal, dict):
        for key in ("AWS", "Service", "Federated"):
            value = principal.get(key)
            if value is None:
                continue
            if isinstance(value, str):
                principals.append(value)
            elif isinstance(value, list):
                principals.extend(value)

    return principals if principals else []


def _extract_account_id_from_principal(principal: str) -> str:
    """Extract the AWS account ID from a principal ARN or identifier.

    Handles formats:
      - "arn:aws:iam::123456789012:root" → "123456789012"
      - "arn:aws:iam::123456789012:role/RoleName" → "123456789012"
      - "123456789012" → "123456789012"
      - "*" → "*"

    Args:
        principal: The principal ARN or identifier string.

    Returns:
        The extracted account ID, or the original string if extraction fails.
    """
    if principal == "*":
        return "*"

    # Try to extract from ARN format: arn:partition:service::account-id:resource
    if principal.startswith("arn:"):
        parts = principal.split(":")
        if len(parts) >= 5:
            return parts[4]

    # If it looks like a bare account ID (12 digits)
    if principal.isdigit() and len(principal) == 12:
        return principal

    return principal


def _check_external_id_condition(conditions: dict[str, Any]) -> bool:
    """Check whether a trust policy condition block contains an external ID requirement.

    Looks for sts:ExternalId in StringEquals or StringLike condition operators.

    Args:
        conditions: The Condition block from a trust policy statement.

    Returns:
        True if an external ID condition is present, False otherwise.
    """
    if not conditions:
        return False

    # Check common condition operators that could contain ExternalId
    for operator in ("StringEquals", "StringLike", "ForAnyValue:StringEquals"):
        operator_conditions = conditions.get(operator, {})
        if isinstance(operator_conditions, dict):
            if "sts:ExternalId" in operator_conditions:
                return True

    return False


def _compute_trust_risk_score(
    has_wildcard_principal: bool,
    has_external_id: bool,
    actions: list[str],
    conditions: dict[str, Any],
) -> int:
    """Compute a risk score (0-100) for a cross-account trust relationship.

    Scoring factors:
      - Wildcard principal ("*"): +50 points (highest risk factor)
      - Missing external ID: +25 points
      - Broad actions (sts:* or multiple actions): +15 points
      - No IP/source restrictions in conditions: +10 points

    Args:
        has_wildcard_principal: Whether the principal is "*".
        has_external_id: Whether an external ID condition is present.
        actions: List of allowed actions in the trust statement.
        conditions: The Condition block from the trust policy.

    Returns:
        Risk score between 0 and 100.
    """
    score = 0

    # Wildcard principal is the highest risk factor
    if has_wildcard_principal:
        score += 50

    # Missing external ID allows confused deputy attacks
    if not has_external_id:
        score += 25

    # Broad actions increase risk
    has_broad_actions = any(
        action in ("sts:*", "*") for action in actions
    ) or len(actions) > 2
    if has_broad_actions:
        score += 15

    # No IP/source restrictions
    has_ip_restriction = False
    if conditions:
        for operator in ("IpAddress", "StringEquals", "StringLike"):
            op_conditions = conditions.get(operator, {})
            if isinstance(op_conditions, dict):
                if any(
                    key in op_conditions
                    for key in ("aws:SourceIp", "aws:SourceVpc", "aws:SourceVpce")
                ):
                    has_ip_restriction = True
                    break

    if not has_ip_restriction:
        score += 10

    return max(0, min(score, 100))


# ─── Privilege Escalation Path Discovery ─────────────────────────────────────

# Neo4j Cypher query for escalation paths
ESCALATION_QUERY = """
MATCH path = (source:IAMIdentity {org_id: $org_id})-[:HAS_PERMISSION|CAN_ASSUME*1..5]->(target:IAMIdentity)
WHERE target.privilege_level > source.privilege_level
  AND any(r IN relationships(path) WHERE r.type IN $escalation_patterns)
RETURN path, length(path) as hops, target.privilege_level as target_level
ORDER BY hops ASC, target_level DESC
"""

# Known privilege escalation patterns — each tuple represents a combination of
# permissions that can be chained to escalate privileges.
KNOWN_ESCALATION_PATTERNS: list[tuple[str, ...]] = [
    ("iam:CreateRole", "iam:AttachRolePolicy"),
    ("iam:PassRole", "lambda:CreateFunction"),
    ("sts:AssumeRole",),  # chains
    ("ec2:RunInstances",),  # with instance profiles
    ("iam:CreateAccessKey",),
    ("iam:UpdateLoginProfile",),
    ("lambda:UpdateFunctionCode", "iam:PassRole"),
]

# Flattened set of all escalation-related permissions for quick lookup
_ESCALATION_PERMISSIONS_FLAT: set[str] = set()
for _pattern in KNOWN_ESCALATION_PATTERNS:
    _ESCALATION_PERMISSIONS_FLAT.update(_pattern)


async def discover_escalation_paths(
    graph_client: Any,
    organization_id: str,
) -> list[dict[str, Any]]:
    """Discover privilege escalation paths via Neo4j graph traversal.

    Traverses the IAM identity graph to find sequences of permissions that allow
    a lower-privileged identity to escalate to a higher privilege level. Uses the
    ESCALATION_QUERY Cypher query to find paths up to 5 hops where the target
    has a higher privilege level than the source.

    Args:
        graph_client: An instance of GraphClient from app.core.graph_client.
        organization_id: The tenant organization ID for multi-tenant isolation.

    Returns:
        List of escalation path dicts, each containing:
            - source_identity: The starting identity ARN/ID
            - target_identity: The destination identity ARN/ID
            - path_hops: Number of hops in the escalation path
            - path_details: List of intermediate steps with identity, permission, action
            - target_privilege_level: The privilege level of the target (e.g., "admin")
            - severity: Assigned severity based on hops and target level
            - pattern_ids: List of matched known escalation pattern indices

    Raises:
        GraphClientError: If the graph service request fails.
    """
    logger.info(
        "Discovering privilege escalation paths for org_id=%s",
        organization_id,
    )

    # Flatten all known patterns into a list of permission strings for the query
    escalation_pattern_permissions = list(_ESCALATION_PERMISSIONS_FLAT)

    try:
        records = await graph_client.query(
            cypher=ESCALATION_QUERY,
            parameters={
                "org_id": organization_id,
                "escalation_patterns": escalation_pattern_permissions,
            },
        )
    except Exception as exc:
        logger.error(
            "Failed to query escalation paths for org_id=%s: %s",
            organization_id,
            exc,
        )
        raise

    escalation_paths: list[dict[str, Any]] = []

    for record in records:
        path_data = record.get("path", {})
        hops = record.get("hops", 0)
        target_level = record.get("target_level", 0)

        # Extract nodes and relationships from the path
        nodes = path_data.get("nodes", [])
        relationships = path_data.get("relationships", [])

        if len(nodes) < 2:
            continue

        source_identity = nodes[0].get("identity_arn", nodes[0].get("id", "unknown"))
        target_identity = nodes[-1].get("identity_arn", nodes[-1].get("id", "unknown"))

        # Build path details from intermediate steps
        path_details = _build_path_details(nodes, relationships)

        # Match against known escalation patterns
        matched_patterns = match_known_patterns(path_details)

        # Determine target privilege level label
        target_privilege_label = _privilege_level_to_label(target_level)

        # Assign severity based on path length and target level
        severity = assign_escalation_severity(
            path_hops=hops,
            target_privilege_level=target_level,
        )

        escalation_path = {
            "source_identity": source_identity,
            "target_identity": target_identity,
            "path_hops": hops,
            "path_details": path_details,
            "target_privilege_level": target_privilege_label,
            "severity": severity,
            "pattern_ids": matched_patterns,
        }
        escalation_paths.append(escalation_path)

    logger.info(
        "Discovered %d escalation paths for org_id=%s",
        len(escalation_paths),
        organization_id,
    )
    return escalation_paths


def match_known_patterns(
    path_details: list[dict[str, Any]],
) -> list[int]:
    """Check a path's permissions against KNOWN_ESCALATION_PATTERNS.

    Examines the permissions used in each step of an escalation path and
    determines which known escalation patterns are matched. A pattern is
    considered matched if all permissions in the pattern tuple appear in
    the path's permission set.

    Args:
        path_details: List of path step dicts, each containing at minimum
            a "permission" key with the IAM permission string used in that step.

    Returns:
        List of pattern indices (0-based) from KNOWN_ESCALATION_PATTERNS that
        are matched by the path's permissions.
    """
    # Collect all permissions used in this path
    path_permissions: set[str] = set()
    for step in path_details:
        permission = step.get("permission", "")
        if permission:
            path_permissions.add(permission)

    matched_pattern_ids: list[int] = []

    for idx, pattern in enumerate(KNOWN_ESCALATION_PATTERNS):
        # A pattern matches if ALL permissions in the pattern tuple are present
        if all(perm in path_permissions for perm in pattern):
            matched_pattern_ids.append(idx)

    if matched_pattern_ids:
        logger.debug(
            "Matched escalation patterns %s for permissions %s",
            matched_pattern_ids,
            path_permissions,
        )

    return matched_pattern_ids


def assign_escalation_severity(
    path_hops: int,
    target_privilege_level: int | str,
) -> str:
    """Assign severity to an escalation path based on hop count and target level.

    Severity rules:
      - CRITICAL: path has fewer than 3 hops to admin-level access (level >= 9)
      - HIGH: 3-4 hops to admin-level access
      - MEDIUM: 5-6 hops to admin-level access
      - LOW: longer paths or non-admin targets (level < 9)

    Admin-level access is defined as a target_privilege_level >= 9 (on a 0-10 scale)
    or a string label of "admin".

    Args:
        path_hops: Number of hops in the escalation path.
        target_privilege_level: Numeric privilege level (0-10) or string label
            ("admin", "power_user", "read_only").

    Returns:
        Severity string: CRITICAL, HIGH, MEDIUM, or LOW.
    """
    # Normalize target_privilege_level to numeric
    if isinstance(target_privilege_level, str):
        level_numeric = _label_to_privilege_level(target_privilege_level)
    else:
        level_numeric = target_privilege_level

    is_admin_target = level_numeric >= 9

    if not is_admin_target:
        # Non-admin targets are always LOW severity regardless of hops
        return SEVERITY_LOW

    # Admin-level target — severity depends on hop count
    if path_hops < 3:
        return SEVERITY_CRITICAL
    elif path_hops <= 4:
        return SEVERITY_HIGH
    elif path_hops <= 6:
        return SEVERITY_MEDIUM
    else:
        return SEVERITY_LOW


async def store_escalation_path_in_graph(
    graph_client: Any,
    escalation_path: dict[str, Any],
    organization_id: str,
) -> dict[str, Any]:
    """Persist a discovered escalation path as a directed graph in Neo4j.

    Creates nodes for each identity in the path and edges representing
    permission transitions. The path is stored as a series of
    ESCALATES_TO relationships connecting the source to the target
    through intermediate identities.

    Args:
        graph_client: An instance of GraphClient from app.core.graph_client.
        escalation_path: An escalation path dict as returned by
            discover_escalation_paths(). Must contain source_identity,
            target_identity, path_hops, path_details, severity, and pattern_ids.
        organization_id: The tenant organization ID for multi-tenant isolation.

    Returns:
        The result dict from the graph service containing the created/updated
        path data.

    Raises:
        GraphClientError: If the graph service request fails.
    """
    source_identity = escalation_path["source_identity"]
    target_identity = escalation_path["target_identity"]
    path_hops = escalation_path["path_hops"]
    path_details = escalation_path.get("path_details", [])
    severity = escalation_path["severity"]
    pattern_ids = escalation_path.get("pattern_ids", [])
    target_privilege_level = escalation_path.get("target_privilege_level", "unknown")

    # Use a MERGE Cypher query to create or update the escalation path edge
    cypher = """
    MERGE (source:IAMIdentity {identity_arn: $source_identity, org_id: $org_id})
    MERGE (target:IAMIdentity {identity_arn: $target_identity, org_id: $org_id})
    MERGE (source)-[r:ESCALATES_TO {org_id: $org_id}]->(target)
    SET r.path_hops = $path_hops,
        r.path_details = $path_details,
        r.severity = $severity,
        r.pattern_ids = $pattern_ids,
        r.target_privilege_level = $target_privilege_level,
        r.discovered_at = datetime()
    RETURN r
    """

    parameters = {
        "source_identity": source_identity,
        "target_identity": target_identity,
        "path_hops": path_hops,
        "path_details": str(path_details),  # Neo4j stores complex structures as string
        "severity": severity,
        "pattern_ids": pattern_ids,
        "target_privilege_level": target_privilege_level,
        "org_id": organization_id,
    }

    logger.info(
        "Storing escalation path in graph: %s -> %s (hops=%d, severity=%s)",
        source_identity,
        target_identity,
        path_hops,
        severity,
    )

    try:
        result = await graph_client.query(cypher=cypher, parameters=parameters)
    except Exception as exc:
        logger.error(
            "Failed to store escalation path %s -> %s: %s",
            source_identity,
            target_identity,
            exc,
        )
        raise

    return result


# ─── Privilege Escalation Helpers ─────────────────────────────────────────────


def _build_path_details(
    nodes: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a structured list of path steps from graph nodes and relationships.

    Args:
        nodes: List of node dicts from the graph path.
        relationships: List of relationship dicts from the graph path.

    Returns:
        List of step dicts with identity, permission, and action fields.
    """
    path_details: list[dict[str, Any]] = []

    for i, rel in enumerate(relationships):
        source_node = nodes[i] if i < len(nodes) else {}
        target_node = nodes[i + 1] if (i + 1) < len(nodes) else {}

        step = {
            "identity": source_node.get("identity_arn", source_node.get("id", "unknown")),
            "permission": rel.get("permission", rel.get("type", "")),
            "action": rel.get("action", rel.get("type", "")),
            "target": target_node.get("identity_arn", target_node.get("id", "unknown")),
        }
        path_details.append(step)

    return path_details


def _privilege_level_to_label(level: int) -> str:
    """Convert a numeric privilege level to a human-readable label.

    Args:
        level: Numeric privilege level (0-10).

    Returns:
        String label: "admin", "power_user", or "read_only".
    """
    if level >= 9:
        return "admin"
    elif level >= 5:
        return "power_user"
    else:
        return "read_only"


def _label_to_privilege_level(label: str) -> int:
    """Convert a privilege level label to a numeric value.

    Args:
        label: String label ("admin", "power_user", "read_only").

    Returns:
        Numeric privilege level (0-10).
    """
    label_lower = label.lower().strip()
    if label_lower == "admin":
        return 10
    elif label_lower == "power_user":
        return 7
    elif label_lower == "read_only":
        return 3
    else:
        return 0
