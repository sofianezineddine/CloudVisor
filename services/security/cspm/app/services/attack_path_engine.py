"""Attack Path Engine — graph-based attack path discovery and blast radius computation.

Provides functions for:
- Attack path discovery from internet-exposed entry points to sensitive resources
- Blast radius computation for any given resource
- Lateral movement opportunity detection
- MITRE ATT&CK Cloud technique mapping
- Path severity assignment based on hop count
- Toxic combination detection
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_cspm_settings
from app.core.graph_client import GraphClient, GraphClientError

logger = logging.getLogger(__name__)

# ─── Severity Constants ───────────────────────────────────────────────────────

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"

# ─── Neo4j Cypher Queries ─────────────────────────────────────────────────────

ATTACK_PATH_QUERY = """
MATCH (entry:Resource {org_id: $org_id, is_internet_exposed: true})
MATCH (sensitive:Resource {org_id: $org_id, contains_sensitive_data: true})
MATCH path = shortestPath((entry)-[:CONNECTS_TO|HAS_ACCESS|TRUSTS*..{max_hops}]->(sensitive))
RETURN path, length(path) as hops,
       [n IN nodes(path) | n.resource_type] as resource_types,
       [n IN nodes(path) | n.id] as node_ids,
       entry.id as entry_id,
       sensitive.id as sensitive_id,
       [r IN relationships(path) | type(r)] as relationship_types
ORDER BY hops ASC
"""

BLAST_RADIUS_QUERY = """
MATCH (source:Resource {id: $resource_id, org_id: $org_id})
MATCH (reachable:Resource)
WHERE (source)-[:CONNECTS_TO|HAS_ACCESS|TRUSTS*1..{max_depth}]->(reachable)
RETURN collect(DISTINCT reachable.id) as blast_radius_ids,
       collect(DISTINCT reachable.resource_type) as blast_radius_types
"""

LATERAL_MOVEMENT_SHARED_CREDS_QUERY = """
MATCH (r1:Resource {org_id: $org_id})-[:USES_CREDENTIAL]->(cred:Credential)<-[:USES_CREDENTIAL]-(r2:Resource {org_id: $org_id})
WHERE r1.id <> r2.id
RETURN r1.id as source_id, r2.id as target_id, cred.id as credential_id,
       'shared_credentials' as movement_type
"""

LATERAL_MOVEMENT_PERMISSIVE_SG_QUERY = """
MATCH (r1:Resource {org_id: $org_id})-[:MEMBER_OF]->(sg:SecurityGroup)<-[:MEMBER_OF]-(r2:Resource {org_id: $org_id})
WHERE r1.id <> r2.id AND sg.allows_all_traffic = true
RETURN r1.id as source_id, r2.id as target_id, sg.id as security_group_id,
       'permissive_security_group' as movement_type
"""

LATERAL_MOVEMENT_INSTANCE_PROFILE_QUERY = """
MATCH (instance:Resource {org_id: $org_id, resource_type: 'ec2_instance'})-[:HAS_PROFILE]->(profile:InstanceProfile)-[:HAS_ROLE]->(role:IAMIdentity)-[:HAS_ACCESS]->(target:Resource {org_id: $org_id})
WHERE instance.id <> target.id
RETURN instance.id as source_id, target.id as target_id, profile.id as profile_id,
       role.id as role_id, 'instance_profile_chain' as movement_type
"""

# ─── MITRE ATT&CK Cloud Mapping ──────────────────────────────────────────────

MITRE_ATTACK_MAPPING: dict[str, dict[str, str]] = {
    "T1078": {
        "id": "T1078",
        "name": "Valid Accounts",
        "description": "Credential-based access using valid accounts",
    },
    "T1098": {
        "id": "T1098",
        "name": "Account Manipulation",
        "description": "Manipulation of account settings to maintain access",
    },
    "T1530": {
        "id": "T1530",
        "name": "Data from Cloud Storage Object",
        "description": "Access to data stored in cloud storage objects",
    },
    "T1537": {
        "id": "T1537",
        "name": "Transfer Data to Cloud Account",
        "description": "Exfiltration of data to an attacker-controlled cloud account",
    },
    "T1552": {
        "id": "T1552",
        "name": "Unsecured Credentials",
        "description": "Access to credentials stored insecurely",
    },
    "T1580": {
        "id": "T1580",
        "name": "Cloud Infrastructure Discovery",
        "description": "Discovery of cloud infrastructure and services",
    },
    "T1190": {
        "id": "T1190",
        "name": "Exploit Public-Facing Application",
        "description": "Exploitation of a public-facing application as entry point",
    },
}

# Mapping from path patterns (relationship types and resource types) to MITRE techniques
_PATH_PATTERN_TO_MITRE: list[dict[str, Any]] = [
    {
        "technique_id": "T1537",
        "match": lambda resource_types, rel_types: (
            "TRUSTS" in rel_types
            and any(rt in ("s3_bucket", "storage_account", "rds_instance", "database") for rt in resource_types)
        ),
        "description": "Path enables data transfer via cross-account trust",
    },
    {
        "technique_id": "T1552",
        "match": lambda resource_types, rel_types: (
            any(rt in ("secrets_manager", "parameter_store", "key_vault") for rt in resource_types)
        ),
        "description": "Path reaches unsecured credential stores",
    },
    {
        "technique_id": "T1530",
        "match": lambda resource_types, rel_types: (
            any(rt in ("s3_bucket", "storage_account", "gcs_bucket") for rt in resource_types)
            and "TRUSTS" not in rel_types
        ),
        "description": "Path reaches cloud storage containing data",
    },
    {
        "technique_id": "T1190",
        "match": lambda resource_types, rel_types: (
            len(resource_types) > 0
            and resource_types[0] in ("load_balancer", "api_gateway", "web_server")
        ),
        "description": "Path starts from a public-facing application",
    },
    {
        "technique_id": "T1098",
        "match": lambda resource_types, rel_types: (
            any(rt in ("iam_role", "iam_user", "iam_policy") for rt in resource_types)
            and "HAS_ACCESS" in rel_types
        ),
        "description": "Path enables account manipulation via IAM access",
    },
    {
        "technique_id": "T1078",
        "match": lambda resource_types, rel_types: (
            "HAS_ACCESS" in rel_types or "TRUSTS" in rel_types
        ),
        "description": "Path uses valid account credentials or trust relationships",
    },
    {
        "technique_id": "T1580",
        "match": lambda resource_types, rel_types: (
            "CONNECTS_TO" in rel_types
            and len(resource_types) > 2
        ),
        "description": "Path involves cloud infrastructure discovery through network connectivity",
    },
]


# ─── Attack Path Discovery ────────────────────────────────────────────────────


async def discover_attack_paths(
    graph_client: GraphClient,
    organization_id: str,
    max_hops: int | None = None,
) -> list[dict[str, Any]]:
    """Discover attack paths from internet-exposed entry points to sensitive resources.

    Uses Neo4j graph traversal to find shortest paths from resources marked as
    internet-exposed to resources containing sensitive data. Paths traverse
    CONNECTS_TO, HAS_ACCESS, and TRUSTS relationships.

    Args:
        graph_client: An instance of GraphClient for Neo4j queries.
        organization_id: The tenant organization ID for multi-tenant isolation.
        max_hops: Maximum number of hops to traverse. Defaults to
            settings.attack_path_max_hops (6).

    Returns:
        List of attack path dicts, each containing:
            - id: Unique path identifier
            - organization_id: Tenant ID
            - entry_resource_id: The internet-exposed entry point resource ID
            - target_resource_id: The sensitive target resource ID
            - path_hops: Number of hops in the path
            - path_nodes: Ordered list of resource IDs in the path
            - path_edges: List of relationship dicts {from, to, relationship_type}
            - resource_types: List of resource types along the path
            - severity: Assigned severity based on hop count
            - mitre_technique_id: Mapped MITRE ATT&CK technique ID
            - mitre_technique_name: Mapped MITRE ATT&CK technique name
            - is_lateral_movement: Whether lateral movement was detected
            - discovered_at: Timestamp of discovery

    Raises:
        GraphClientError: If the Neo4j query fails.
    """
    settings = get_cspm_settings()
    effective_max_hops = max_hops if max_hops is not None else settings.attack_path_max_hops

    # Build the query with the max_hops parameter embedded (Neo4j doesn't support
    # parameterized relationship length in shortestPath)
    query = ATTACK_PATH_QUERY.replace("{max_hops}", str(effective_max_hops))

    logger.info(
        "Discovering attack paths for org=%s with max_hops=%d",
        organization_id,
        effective_max_hops,
    )

    try:
        records = await graph_client.query(
            cypher=query,
            parameters={"org_id": organization_id},
        )
    except GraphClientError:
        logger.error(
            "Failed to discover attack paths for org=%s", organization_id
        )
        raise

    attack_paths: list[dict[str, Any]] = []
    seen_path_keys: set[str] = set()

    for record in records:
        hops = record.get("hops", 0)
        node_ids = record.get("node_ids", [])
        resource_types = record.get("resource_types", [])
        relationship_types = record.get("relationship_types", [])
        entry_id = record.get("entry_id", node_ids[0] if node_ids else "")
        sensitive_id = record.get("sensitive_id", node_ids[-1] if node_ids else "")

        # Deduplicate paths by entry+target pair
        path_key = f"{entry_id}:{sensitive_id}"
        if path_key in seen_path_keys:
            continue
        seen_path_keys.add(path_key)

        # Build edge list from node IDs and relationship types
        path_edges = _build_path_edges(node_ids, relationship_types)

        # Assign severity based on hop count
        severity = assign_path_severity(hops)

        # Map to MITRE ATT&CK technique
        mitre_info = map_to_mitre_attack(resource_types, relationship_types)

        attack_path: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "organization_id": organization_id,
            "entry_resource_id": entry_id,
            "target_resource_id": sensitive_id,
            "path_hops": hops,
            "path_nodes": node_ids,
            "path_edges": path_edges,
            "resource_types": resource_types,
            "severity": severity,
            "mitre_technique_id": mitre_info.get("id") if mitre_info else None,
            "mitre_technique_name": mitre_info.get("name") if mitre_info else None,
            "is_lateral_movement": False,
            "blast_radius_count": 0,
            "discovered_at": datetime.now(timezone.utc),
        }
        attack_paths.append(attack_path)

    logger.info(
        "Discovered %d attack paths for org=%s",
        len(attack_paths),
        organization_id,
    )
    return attack_paths


# ─── Blast Radius Computation ─────────────────────────────────────────────────


async def compute_blast_radius(
    graph_client: GraphClient,
    resource_id: str,
    organization_id: str,
    max_depth: int | None = None,
) -> dict[str, Any]:
    """Compute the blast radius for a given resource.

    Traverses all reachable resources from the source through CONNECTS_TO,
    HAS_ACCESS, and TRUSTS relationships up to a configurable depth.

    Args:
        graph_client: An instance of GraphClient for Neo4j queries.
        resource_id: The ID of the resource to compute blast radius for.
        organization_id: The tenant organization ID for multi-tenant isolation.
        max_depth: Maximum traversal depth. Defaults to
            settings.blast_radius_max_depth (4).

    Returns:
        Dict containing:
            - resource_id: The source resource ID
            - organization_id: Tenant ID
            - blast_radius_count: Number of reachable resources
            - reachable_resources: List of reachable resource IDs
            - reachable_resource_types: List of distinct resource types reachable

    Raises:
        GraphClientError: If the Neo4j query fails.
    """
    settings = get_cspm_settings()
    effective_max_depth = max_depth if max_depth is not None else settings.blast_radius_max_depth

    query = BLAST_RADIUS_QUERY.replace("{max_depth}", str(effective_max_depth))

    logger.info(
        "Computing blast radius for resource=%s, org=%s, max_depth=%d",
        resource_id,
        organization_id,
        effective_max_depth,
    )

    try:
        records = await graph_client.query(
            cypher=query,
            parameters={
                "resource_id": resource_id,
                "org_id": organization_id,
            },
        )
    except GraphClientError:
        logger.error(
            "Failed to compute blast radius for resource=%s, org=%s",
            resource_id,
            organization_id,
        )
        raise

    # Extract results from the first record
    reachable_ids: list[str] = []
    reachable_types: list[str] = []

    if records:
        first_record = records[0]
        reachable_ids = first_record.get("blast_radius_ids", [])
        reachable_types = first_record.get("blast_radius_types", [])

    # Remove the source resource from blast radius if present
    reachable_ids = [rid for rid in reachable_ids if rid != resource_id]
    # Deduplicate types
    reachable_types = list(set(reachable_types))

    result = {
        "resource_id": resource_id,
        "organization_id": organization_id,
        "blast_radius_count": len(reachable_ids),
        "reachable_resources": reachable_ids,
        "reachable_resource_types": reachable_types,
    }

    logger.info(
        "Blast radius for resource=%s: %d reachable resources",
        resource_id,
        len(reachable_ids),
    )
    return result


# ─── Lateral Movement Detection ───────────────────────────────────────────────


async def detect_lateral_movement(
    graph_client: GraphClient,
    organization_id: str,
) -> list[dict[str, Any]]:
    """Detect lateral movement opportunities within an organization's infrastructure.

    Identifies three types of lateral movement vectors:
      1. Shared credentials — resources sharing the same credential
      2. Permissive security groups — resources in security groups allowing all traffic
      3. Instance profile chains — EC2 instances with profiles granting access to other resources

    Args:
        graph_client: An instance of GraphClient for Neo4j queries.
        organization_id: The tenant organization ID for multi-tenant isolation.

    Returns:
        List of lateral movement finding dicts, each containing:
            - id: Unique finding identifier
            - organization_id: Tenant ID
            - source_id: Source resource ID
            - target_id: Target resource ID
            - movement_type: Type of lateral movement (shared_credentials,
              permissive_security_group, instance_profile_chain)
            - details: Additional context about the movement vector
            - severity: Assigned severity (HIGH for all lateral movement)
            - mitre_technique_id: Mapped MITRE technique
            - mitre_technique_name: Mapped MITRE technique name
            - discovered_at: Timestamp of discovery

    Raises:
        GraphClientError: If any Neo4j query fails.
    """
    logger.info(
        "Detecting lateral movement opportunities for org=%s", organization_id
    )

    lateral_movements: list[dict[str, Any]] = []
    parameters = {"org_id": organization_id}

    # Query 1: Shared credentials
    try:
        shared_creds_records = await graph_client.query(
            cypher=LATERAL_MOVEMENT_SHARED_CREDS_QUERY,
            parameters=parameters,
        )
        for record in shared_creds_records:
            lateral_movements.append(
                _build_lateral_movement_finding(
                    record=record,
                    organization_id=organization_id,
                    movement_type="shared_credentials",
                    details={
                        "credential_id": record.get("credential_id", ""),
                        "description": (
                            "Resources share the same credential, allowing lateral "
                            "movement if the credential is compromised."
                        ),
                    },
                )
            )
    except GraphClientError as exc:
        logger.warning("Shared credentials query failed: %s", exc)

    # Query 2: Permissive security groups
    try:
        permissive_sg_records = await graph_client.query(
            cypher=LATERAL_MOVEMENT_PERMISSIVE_SG_QUERY,
            parameters=parameters,
        )
        for record in permissive_sg_records:
            lateral_movements.append(
                _build_lateral_movement_finding(
                    record=record,
                    organization_id=organization_id,
                    movement_type="permissive_security_group",
                    details={
                        "security_group_id": record.get("security_group_id", ""),
                        "description": (
                            "Resources are in a security group that allows all traffic, "
                            "enabling unrestricted lateral movement."
                        ),
                    },
                )
            )
    except GraphClientError as exc:
        logger.warning("Permissive security groups query failed: %s", exc)

    # Query 3: Instance profile chains
    try:
        instance_profile_records = await graph_client.query(
            cypher=LATERAL_MOVEMENT_INSTANCE_PROFILE_QUERY,
            parameters=parameters,
        )
        for record in instance_profile_records:
            lateral_movements.append(
                _build_lateral_movement_finding(
                    record=record,
                    organization_id=organization_id,
                    movement_type="instance_profile_chain",
                    details={
                        "profile_id": record.get("profile_id", ""),
                        "role_id": record.get("role_id", ""),
                        "description": (
                            "EC2 instance has an instance profile with a role that "
                            "grants access to other resources, enabling lateral movement."
                        ),
                    },
                )
            )
    except GraphClientError as exc:
        logger.warning("Instance profile chains query failed: %s", exc)

    logger.info(
        "Detected %d lateral movement opportunities for org=%s",
        len(lateral_movements),
        organization_id,
    )
    return lateral_movements


# ─── MITRE ATT&CK Mapping ────────────────────────────────────────────────────


def map_to_mitre_attack(
    resource_types: list[str],
    relationship_types: list[str],
) -> dict[str, str] | None:
    """Map an attack path pattern to a MITRE ATT&CK Cloud technique.

    Evaluates the resource types and relationship types along a path against
    known pattern-to-technique mappings. Returns the first matching technique.

    Args:
        resource_types: List of resource types along the attack path
            (e.g., ["load_balancer", "ec2_instance", "s3_bucket"]).
        relationship_types: List of relationship types along the path
            (e.g., ["CONNECTS_TO", "HAS_ACCESS"]).

    Returns:
        Dict with MITRE technique info (id, name, description) if a match is found,
        or None if no pattern matches.
    """
    for pattern in _PATH_PATTERN_TO_MITRE:
        try:
            if pattern["match"](resource_types, relationship_types):
                technique_id = pattern["technique_id"]
                technique_info = MITRE_ATTACK_MAPPING.get(technique_id)
                if technique_info:
                    logger.debug(
                        "Mapped path to MITRE technique %s: %s",
                        technique_id,
                        technique_info["name"],
                    )
                    return technique_info
        except (IndexError, TypeError, KeyError):
            # Skip patterns that fail to match due to data issues
            continue

    logger.debug(
        "No MITRE technique match for resource_types=%s, rel_types=%s",
        resource_types,
        relationship_types,
    )
    return None


# ─── Severity Assignment ──────────────────────────────────────────────────────


def assign_path_severity(hops: int) -> str:
    """Assign severity to an attack path based on the number of hops.

    Severity rules:
      - CRITICAL: path ≤ 3 hops from internet-exposed to sensitive resource
      - HIGH: path of exactly 4 hops
      - MEDIUM: path of 5-6 hops
      - LOW: path longer than 6 hops

    Args:
        hops: Number of hops (edges) in the attack path.

    Returns:
        Severity string: CRITICAL, HIGH, MEDIUM, or LOW.
    """
    settings = get_cspm_settings()
    critical_threshold = settings.attack_path_critical_hop_threshold

    if hops <= critical_threshold:
        return SEVERITY_CRITICAL
    elif hops == critical_threshold + 1:
        return SEVERITY_HIGH
    elif hops <= settings.attack_path_max_hops:
        return SEVERITY_MEDIUM
    else:
        return SEVERITY_LOW


# ─── Helper Functions ─────────────────────────────────────────────────────────


def _build_path_edges(
    node_ids: list[str],
    relationship_types: list[str],
) -> list[dict[str, str]]:
    """Build a list of edge dicts from node IDs and relationship types.

    Args:
        node_ids: Ordered list of node IDs in the path.
        relationship_types: List of relationship types between consecutive nodes.

    Returns:
        List of edge dicts with keys: from, to, relationship_type.
    """
    edges: list[dict[str, str]] = []
    for i in range(len(node_ids) - 1):
        rel_type = relationship_types[i] if i < len(relationship_types) else "UNKNOWN"
        edges.append({
            "from": node_ids[i],
            "to": node_ids[i + 1],
            "relationship_type": rel_type,
        })
    return edges


def _build_lateral_movement_finding(
    record: dict[str, Any],
    organization_id: str,
    movement_type: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    """Build a lateral movement finding dict from a query record.

    Args:
        record: A record from a lateral movement Neo4j query.
        organization_id: The tenant organization ID.
        movement_type: Type of lateral movement detected.
        details: Additional context about the movement vector.

    Returns:
        A lateral movement finding dict.
    """
    # Map movement types to MITRE techniques
    movement_mitre_map: dict[str, str] = {
        "shared_credentials": "T1078",
        "permissive_security_group": "T1580",
        "instance_profile_chain": "T1078",
    }

    technique_id = movement_mitre_map.get(movement_type)
    technique_info = MITRE_ATTACK_MAPPING.get(technique_id, {}) if technique_id else {}

    return {
        "id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "source_id": record.get("source_id", ""),
        "target_id": record.get("target_id", ""),
        "movement_type": movement_type,
        "details": details,
        "severity": SEVERITY_HIGH,
        "mitre_technique_id": technique_id,
        "mitre_technique_name": technique_info.get("name"),
        "discovered_at": datetime.now(timezone.utc),
    }


# ─── Toxic Combination Detection ──────────────────────────────────────────────

# Severity ordering for elevation logic
_SEVERITY_ORDER: dict[str, int] = {
    SEVERITY_LOW: 1,
    SEVERITY_MEDIUM: 2,
    SEVERITY_HIGH: 3,
    SEVERITY_CRITICAL: 4,
}

_SEVERITY_FROM_RANK: dict[int, str] = {v: k for k, v in _SEVERITY_ORDER.items()}

# Predefined toxic combination patterns
TOXIC_PATTERNS: list[dict[str, Any]] = [
    {
        "id": "public-sensitive-unencrypted",
        "components": ["public_access", "sensitive_data_tag", "no_encryption"],
        "elevated_severity": "CRITICAL",
        "description": "Public bucket with sensitive data and no encryption",
    },
    {
        "id": "admin-no-mfa-external-trust",
        "components": ["admin_privileges", "no_mfa", "external_trust"],
        "elevated_severity": "CRITICAL",
        "description": "Admin account without MFA trusted by external account",
    },
]


def detect_toxic_combinations(
    resource_configs: list[dict[str, Any]],
    patterns: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Detect toxic combinations of misconfigurations across resource configurations.

    Checks each resource's active misconfiguration tags against known toxic
    combination patterns. When all components of a pattern are present on a
    single resource, a consolidated finding is generated with elevated severity.

    Args:
        resource_configs: List of resource configuration dicts. Each must contain:
            - resource_id (str): The resource identifier.
            - organization_id (str): The tenant organization ID.
            - misconfigurations (list[dict]): List of misconfiguration dicts, each
              with at least 'rule_id' (str), 'severity' (str), and 'component_tag' (str).
        patterns: Optional list of toxic combination pattern dicts to check against.
            Defaults to TOXIC_PATTERNS if not provided. Each pattern must contain:
            - id (str): Pattern identifier.
            - components (list[str]): List of component_tag values that form the combination.
            - elevated_severity (str): The severity to assign to the consolidated finding.
            - description (str): Human-readable description of the toxic combination.

    Returns:
        List of toxic combination finding dicts, each containing:
            - id: Unique finding identifier
            - organization_id: Tenant ID
            - resource_id: The affected resource
            - pattern_id: The matched pattern ID
            - elevated_severity: The elevated severity (strictly greater than max component)
            - description: Pattern description
            - component_finding_ids: List of contributing misconfiguration rule_ids
            - component_details: List of contributing misconfiguration details
            - detected_at: Timestamp of detection
    """
    effective_patterns = patterns if patterns is not None else TOXIC_PATTERNS

    findings: list[dict[str, Any]] = []

    for resource in resource_configs:
        resource_id = resource.get("resource_id", "")
        organization_id = resource.get("organization_id", "")
        misconfigs = resource.get("misconfigurations", [])

        if not misconfigs:
            continue

        # Build a set of component tags present on this resource
        component_tags: set[str] = set()
        tag_to_misconfigs: dict[str, list[dict[str, Any]]] = {}

        for misconfig in misconfigs:
            tag = misconfig.get("component_tag", "")
            if tag:
                component_tags.add(tag)
                tag_to_misconfigs.setdefault(tag, []).append(misconfig)

        # Check each pattern
        for pattern in effective_patterns:
            pattern_components = set(pattern.get("components", []))

            if not pattern_components:
                continue

            # All components must be present
            if pattern_components.issubset(component_tags):
                # Gather contributing misconfigurations
                contributing: list[dict[str, Any]] = []
                for component in pattern["components"]:
                    contributing.extend(tag_to_misconfigs.get(component, []))

                # Compute elevated severity
                elevated = elevate_severity(
                    component_severities=[m.get("severity", SEVERITY_LOW) for m in contributing],
                    pattern_elevated_severity=pattern.get("elevated_severity", SEVERITY_CRITICAL),
                )

                finding = build_consolidated_finding(
                    resource_id=resource_id,
                    organization_id=organization_id,
                    pattern=pattern,
                    contributing_misconfigs=contributing,
                    elevated_severity=elevated,
                )
                findings.append(finding)

    logger.info("Detected %d toxic combinations across %d resources", len(findings), len(resource_configs))
    return findings


def elevate_severity(
    component_severities: list[str],
    pattern_elevated_severity: str,
) -> str:
    """Compute the elevated severity for a toxic combination.

    The consolidated severity must be STRICTLY GREATER than the maximum severity
    of the individual components. If the pattern's defined elevated severity is
    already strictly greater, it is used. Otherwise, the severity is bumped one
    level above the max component severity (capped at CRITICAL).

    Args:
        component_severities: List of severity strings from contributing misconfigs.
        pattern_elevated_severity: The severity defined by the toxic pattern.

    Returns:
        The elevated severity string, guaranteed to be strictly greater than
        the maximum component severity.
    """
    if not component_severities:
        return pattern_elevated_severity

    # Find the max severity rank among components
    max_component_rank = max(
        _SEVERITY_ORDER.get(s, 1) for s in component_severities
    )

    # Get the pattern's elevated severity rank
    pattern_rank = _SEVERITY_ORDER.get(pattern_elevated_severity, 4)

    # The elevated severity must be strictly greater than max component
    if pattern_rank > max_component_rank:
        return pattern_elevated_severity

    # Bump one level above max component, capped at CRITICAL
    elevated_rank = min(max_component_rank + 1, _SEVERITY_ORDER[SEVERITY_CRITICAL])
    return _SEVERITY_FROM_RANK.get(elevated_rank, SEVERITY_CRITICAL)


def build_consolidated_finding(
    resource_id: str,
    organization_id: str,
    pattern: dict[str, Any],
    contributing_misconfigs: list[dict[str, Any]],
    elevated_severity: str,
) -> dict[str, Any]:
    """Create a consolidated toxic combination finding with sub-findings.

    Builds a finding that includes all contributing misconfigurations as
    sub-findings, providing full context for remediation.

    Args:
        resource_id: The affected resource ID.
        organization_id: The tenant organization ID.
        pattern: The matched toxic combination pattern dict.
        contributing_misconfigs: List of misconfiguration dicts that form the combination.
        elevated_severity: The computed elevated severity for the consolidated finding.

    Returns:
        A consolidated finding dict containing:
            - id: Unique finding identifier
            - organization_id: Tenant ID
            - resource_id: The affected resource
            - pattern_id: The matched pattern ID
            - elevated_severity: The elevated severity
            - description: Pattern description
            - component_finding_ids: List of contributing rule_ids
            - component_details: List of dicts with rule_id, severity, description
            - detected_at: Timestamp of detection
    """
    component_finding_ids: list[str] = []
    component_details: list[dict[str, Any]] = []

    for misconfig in contributing_misconfigs:
        rule_id = misconfig.get("rule_id", "")
        if rule_id:
            component_finding_ids.append(rule_id)

        component_details.append({
            "rule_id": rule_id,
            "severity": misconfig.get("severity", SEVERITY_LOW),
            "description": misconfig.get("description", ""),
            "component_tag": misconfig.get("component_tag", ""),
        })

    return {
        "id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "resource_id": resource_id,
        "pattern_id": pattern.get("id", ""),
        "elevated_severity": elevated_severity,
        "description": pattern.get("description", ""),
        "component_finding_ids": component_finding_ids,
        "component_details": component_details,
        "detected_at": datetime.now(timezone.utc),
    }


def load_custom_toxic_rules(
    rules_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Load custom toxic combination rules from Rego files on disk.

    Scans the specified directory (or the default
    `rules/rego/cspm/toxic_combinations/`) for `.rego` files and parses
    metadata from structured comments to build toxic combination patterns.

    Each Rego file should contain metadata comments in the following format:
        # METADATA
        # pattern_id: <pattern-id>
        # components: <comma-separated component tags>
        # elevated_severity: <CRITICAL|HIGH|MEDIUM|LOW>
        # description: <human-readable description>

    Args:
        rules_dir: Path to the directory containing Rego rule files.
            Defaults to `rules/rego/cspm/toxic_combinations/` relative to
            the CSPM service root.

    Returns:
        List of toxic combination pattern dicts parsed from Rego files.
        Each dict contains: id, components, elevated_severity, description,
        and rego_file (the source filename).
    """
    if rules_dir is None:
        # Default path relative to the CSPM service root
        service_root = Path(__file__).resolve().parent.parent.parent
        rules_dir = service_root / "rules" / "rego" / "cspm" / "toxic_combinations"
    else:
        rules_dir = Path(rules_dir)

    custom_patterns: list[dict[str, Any]] = []

    if not rules_dir.exists() or not rules_dir.is_dir():
        logger.debug(
            "Toxic combination rules directory does not exist: %s", rules_dir
        )
        return custom_patterns

    rego_files = sorted(rules_dir.glob("*.rego"))

    if not rego_files:
        logger.debug("No .rego files found in %s", rules_dir)
        return custom_patterns

    for rego_file in rego_files:
        try:
            pattern = _parse_toxic_rule_metadata(rego_file)
            if pattern:
                custom_patterns.append(pattern)
                logger.debug("Loaded toxic rule from %s: %s", rego_file.name, pattern["id"])
        except Exception as exc:
            logger.warning(
                "Failed to parse toxic rule from %s: %s", rego_file.name, exc
            )

    logger.info(
        "Loaded %d custom toxic combination rules from %s",
        len(custom_patterns),
        rules_dir,
    )
    return custom_patterns


def _parse_toxic_rule_metadata(rego_file: Path) -> dict[str, Any] | None:
    """Parse metadata from a Rego file's structured comments.

    Looks for lines starting with '# ' that contain key: value pairs
    after a '# METADATA' marker.

    Args:
        rego_file: Path to the .rego file.

    Returns:
        A toxic combination pattern dict if valid metadata is found,
        or None if the file lacks required metadata.
    """
    content = rego_file.read_text(encoding="utf-8")
    lines = content.splitlines()

    metadata: dict[str, str] = {}
    in_metadata = False

    for line in lines:
        stripped = line.strip()

        if stripped.upper() == "# METADATA":
            in_metadata = True
            continue

        if in_metadata and stripped.startswith("#"):
            # Parse key: value from comment
            comment_content = stripped[1:].strip()
            if ":" in comment_content:
                key, _, value = comment_content.partition(":")
                metadata[key.strip().lower()] = value.strip()
        elif in_metadata and not stripped.startswith("#"):
            # End of metadata block
            break

    # Validate required fields
    pattern_id = metadata.get("pattern_id")
    components_str = metadata.get("components")
    elevated_severity = metadata.get("elevated_severity")
    description = metadata.get("description")

    if not all([pattern_id, components_str, elevated_severity, description]):
        return None

    components = [c.strip() for c in components_str.split(",") if c.strip()]

    if not components:
        return None

    return {
        "id": pattern_id,
        "components": components,
        "elevated_severity": elevated_severity.upper(),
        "description": description,
        "rego_file": rego_file.name,
    }
