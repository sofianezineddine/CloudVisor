"""Graph service — manages nodes, edges, relationships, risk scoring, and snapshots."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ─── Relationship rules (spec §3.2) ──────────────────────────────────────────
# Maps resource_type suffix → list of (target_type_suffix, relationship_type)
# Used by _resolve_and_create_relationships to auto-wire edges after node upsert.
RELATIONSHIP_RULES: dict[str, list[tuple[str, str]]] = {
    # AWS Compute
    "ec2":                  [("subnet", "RUNS_IN"), ("securitygroup", "BELONGS_TO"), ("iamrole", "HAS_ROLE")],
    "instance":             [("subnet", "RUNS_IN"), ("securitygroup", "BELONGS_TO"), ("iamrole", "HAS_ROLE")],
    # Networking
    "subnet":               [("vpc", "BELONGS_TO")],
    "subnetwork":           [("network", "BELONGS_TO")],
    # Azure Compute
    "virtualmachine":       [("virtualnetwork", "RUNS_IN"), ("networksecuritygroup", "BELONGS_TO")],
    # IAM — spec: IAMUser -[:HAS_ACCESS_TO]-> IAMRole (via group membership + policy)
    "iamuser":              [("iamrole", "HAS_ACCESS_TO")],
    # IAM Role — spec: IAMRole -[:ASSUMES]-> IAMRole (cross-account trust)
    "iamrole":              [("iamrole", "ASSUMES")],
    # Serverless
    "lambdafunction":       [("iamrole", "HAS_ROLE"), ("rdsinstance", "CONNECTS_TO")],
    "cloudfunction":        [("serviceaccount", "HAS_ROLE")],
    # Kubernetes — spec: EKSCluster -[:RUNS_IN]-> VPC, EKSCluster -[:CONTAINS]-> NodeGroup
    "ekscluster":           [("vpc", "RUNS_IN"), ("nodegroup", "CONTAINS")],
    "akskubernetesservice": [("virtualnetwork", "RUNS_IN")],
    "kubernetesservice":    [("virtualnetwork", "RUNS_IN")],
    "gkecluster":           [("network", "RUNS_IN")],
    "okecluster":           [("vcn", "RUNS_IN")],
    # spec: NodeGroup -[:RUNS_ON]-> EC2Instance
    "nodegroup":            [("ec2", "RUNS_ON"), ("instance", "RUNS_ON")],
    # Storage — IAM roles reference S3 via policy analysis (handled separately)
    "s3bucket":             [],
    "bucket":               [],
}

# Flat lookup used by tests: resource_type → list of relationship type strings
RELATIONSHIP_TYPES: dict[str, list[str]] = {
    "EC2":           ["RUNS_IN", "BELONGS_TO", "HAS_ROLE"],
    "S3Bucket":      ["CONTAINS"],
    "IAMRole":       ["HAS_ACCESS_TO", "ASSUMES"],
    "IAMUser":       ["HAS_ACCESS_TO"],
    "Lambda":        ["HAS_ROLE", "CONNECTS_TO"],
    "EKSCluster":    ["RUNS_IN", "CONTAINS"],
    "NodeGroup":     ["RUNS_ON"],
    "Subnet":        ["BELONGS_TO"],
    "SecurityGroup": ["ALLOWS_INBOUND_FROM"],
}


@dataclass
class AssetNode:
    """Represents an asset node in the graph."""

    id: str
    cloud_resource_id: str
    provider: str
    account_id: str
    region: str
    resource_type: str
    name: str
    tags: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    organization_id: str = ""
    is_public: bool = False
    environment: str = "unknown"
    risk_score: int = 0
    open_findings_count: int = 0
    contains_pii: bool = False
    is_production: bool = False
    is_admin: bool = False          # admin IAM access (+10pts per spec)
    first_seen_at: datetime = field(default_factory=datetime.utcnow)
    last_seen_at: datetime = field(default_factory=datetime.utcnow)

    def to_properties(self) -> dict[str, Any]:
        """Convert to Neo4j-safe property dict (no nested dicts)."""
        return {
            "id": self.id,
            "cloud_resource_id": self.cloud_resource_id,
            "provider": self.provider,
            "account_id": self.account_id,
            "region": self.region,
            "resource_type": self.resource_type,
            "name": self.name,
            "tags": json.dumps(self.tags) if self.tags else "{}",
            "organization_id": self.organization_id,
            "is_public": self.is_public,
            "is_internet_exposed": self.is_public,          # spec alias
            "has_public_access": self.is_public,             # spec alias
            "environment": self.environment,
            "risk_score": self.risk_score,
            "open_findings_count": self.open_findings_count,
            "contains_pii": self.contains_pii,
            "contains_sensitive_data": self.contains_pii,   # spec alias
            "is_admin": self.is_admin,
            "is_production": self.environment == "prod",
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
        }

    def get_type_suffix(self) -> str:
        """Get the last part of resource_type: 'aws::ec2::instance' → 'instance'."""
        return self.resource_type.split("::")[-1].lower().replace("_", "").replace(" ", "")


class GraphService:
    """Service for managing the asset graph in Neo4j."""

    # Redis TTL for cached queries (spec: 60 seconds)
    _CACHE_TTL = 60

    def __init__(
        self,
        neo4j_client: Any,
        elasticsearch_client: Any = None,
        event_producer: Any = None,
        db_session_factory: Any = None,
        redis_client: Any = None,
    ):
        self._neo4j = neo4j_client
        self._es = elasticsearch_client
        self._producer = event_producer
        self._db_session_factory = db_session_factory
        self._redis = redis_client  # for query result caching (spec §3.2)

    # ─── Redis cache helpers ──────────────────────────────────────────────────

    # Type-label mapping: resource_type suffix → Neo4j label
    _TYPE_LABEL_MAP: dict[str, str] = {
        "ec2": "EC2Instance",
        "instance": "EC2Instance",
        "virtualmachine": "VirtualMachine",
        "s3bucket": "S3Bucket",
        "bucket": "StorageBucket",
        "iamuser": "IAMUser",
        "iamrole": "IAMRole",
        "iampolicy": "IAMPolicy",
        "serviceaccount": "ServiceAccount",
        "rdsinstance": "RDSInstance",
        "lambdafunction": "LambdaFunction",
        "cloudfunction": "CloudFunction",
        "ekscluster": "EKSCluster",
        "gkecluster": "GKECluster",
        "akskubernetesservice": "AKSCluster",
        "okecluster": "OKECluster",
        "vpc": "VPC",
        "virtualnetwork": "VirtualNetwork",
        "vcn": "VCN",
        "subnet": "Subnet",
        "subnetwork": "Subnetwork",
        "securitygroup": "SecurityGroup",
        "networksecuritygroup": "NetworkSecurityGroup",
        "securitylist": "SecurityList",
        "loadbalancer": "LoadBalancer",
        "kmskey": "KMSKey",
        "cloudtrailtrail": "CloudTrailTrail",
        "ecrrepository": "ECRRepository",
        "efsfilesystem": "EFSFileSystem",
        "dynamodbtable": "DynamoDBTable",
        "sqsqueue": "SQSQueue",
        "snstopic": "SNSTopic",
        "route53hostedzone": "Route53HostedZone",
        "cloudfrontdistribution": "CloudFrontDistribution",
        "apigateway": "APIGateway",
        "secretsmanagersecret": "SecretsManagerSecret",
    }

    def _derive_type_label(self, resource_type: str) -> str:
        """Derive a Neo4j-safe type-specific label from a resource_type string.

        Examples:
          'aws::ec2::instance' → 'EC2Instance'
          'azure::compute::virtualmachine' → 'VirtualMachine'
          'EC2' → 'EC2Instance'

        Returns empty string if no mapping found (node keeps only :Asset label).
        """
        suffix = resource_type.split("::")[-1].lower().replace("_", "").replace(" ", "")
        return self._TYPE_LABEL_MAP.get(suffix, "")

    async def _cache_get(self, key: str) -> Any | None:
        """Get a cached value from Redis. Returns None if unavailable."""
        if not self._redis:
            return None
        try:
            import json as _json
            raw = await self._redis.get(key)
            return _json.loads(raw) if raw else None
        except Exception:
            return None

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in Redis with TTL. Silently ignores errors."""
        if not self._redis:
            return
        try:
            import json as _json
            await self._redis.setex(key, ttl or self._CACHE_TTL, _json.dumps(value, default=str))
        except Exception:
            pass

    async def _cache_invalidate(self, pattern: str) -> None:
        """Delete all Redis keys matching a pattern."""
        if not self._redis:
            return
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                await self._redis.delete(*keys)
        except Exception:
            pass

    # ─── Node CRUD ────────────────────────────────────────────────────────────

    async def create_asset_node(self, asset: AssetNode) -> dict[str, Any]:
        """Create or update an asset node, resolve relationships, index in ES.

        Uses both the generic :Asset label AND a type-specific label (e.g.
        :EC2Instance, :S3Bucket) so Cypher queries can use either.
        """
        properties = asset.to_properties()
        properties["last_seen_at"] = datetime.utcnow().isoformat()

        # Derive a type-specific label from the resource_type
        type_label = self._derive_type_label(asset.resource_type)

        query = f"""
        MERGE (a:Asset {{id: $id}})
        ON CREATE SET a += $props, a.created_at = $now
        ON MATCH  SET a += $props
        {"SET a:" + type_label if type_label else ""}
        RETURN a
        """
        result = await self._neo4j.execute_query(
            query,
            {"id": asset.id, "props": properties, "now": datetime.utcnow().isoformat()},
        )

        await self._resolve_and_create_relationships(asset)

        if self._es:
            await self._index_asset(asset)

        # Invalidate cached list/stats queries for this org
        await self._cache_invalidate(f"graph:assets:{asset.organization_id}:*")
        await self._cache_invalidate(f"graph:stats:{asset.organization_id}:*")

        if self._producer:
            await self._producer.emit_asset_created(
                asset_id=asset.id,
                organization_id=asset.organization_id,
                resource_type=asset.resource_type,
                provider=asset.provider,
                name=asset.name,
            )

        logger.debug(f"Created/merged asset node: {asset.id} ({asset.resource_type})")
        return result[0]["a"] if result else {}

    async def update_asset_node(self, asset: AssetNode) -> dict[str, Any]:
        """Update an existing asset node, recompute risk score, create snapshot."""
        # Fetch previous state for snapshot diff
        previous_node = await self._neo4j.get_node(asset.id)

        properties = asset.to_properties()
        properties["last_seen_at"] = datetime.utcnow().isoformat()

        query = """
        MATCH (a:Asset {id: $id})
        SET a += $props
        RETURN a
        """
        result = await self._neo4j.execute_query(query, {"id": asset.id, "props": properties})

        await self._resolve_and_create_relationships(asset)

        new_score = await self.compute_and_update_risk_score(asset.id)

        if self._es:
            await self._index_asset(asset)

        if self._producer:
            await self._producer.emit_asset_updated(
                asset_id=asset.id,
                organization_id=asset.organization_id,
                resource_type=asset.resource_type,
                risk_score=new_score,
            )

        # Create historical snapshot
        if self._db_session_factory:
            await self._create_snapshot(asset, previous_node)

        # Invalidate cached queries for this org
        await self._cache_invalidate(f"graph:assets:{asset.organization_id}:*")
        await self._cache_invalidate(f"graph:stats:{asset.organization_id}:*")
        # Invalidate single-asset cache
        await self._cache_invalidate(f"graph:asset:{asset.id}")

        logger.debug(f"Updated asset node: {asset.id}")
        return result[0]["a"] if result else {}

    async def delete_asset_node(self, asset_id: str) -> bool:
        """Delete an asset node and all its relationships."""
        node = await self._neo4j.get_node(asset_id)
        org_id = node.get("organization_id", "") if node else ""

        await self._neo4j.delete_node(asset_id)

        if self._es:
            await self._es.delete_document("assets", asset_id)

        # Invalidate all caches for this asset and org
        await self._cache_invalidate(f"graph:asset:{asset_id}")
        if org_id:
            await self._cache_invalidate(f"graph:assets:{org_id}:*")
            await self._cache_invalidate(f"graph:stats:{org_id}:*")

        if self._producer and org_id:
            await self._producer.emit_asset_deleted(
                asset_id=asset_id,
                organization_id=org_id,
            )

        logger.info(f"Deleted asset node: {asset_id}")
        return True

    # ─── Snapshot ─────────────────────────────────────────────────────────────

    async def _create_snapshot(
        self, asset: AssetNode, previous_node: dict[str, Any] | None
    ) -> None:
        """Persist a versioned snapshot of the asset to PostgreSQL."""
        try:
            from .snapshots import SnapshotService

            asset_data = {
                "id": asset.id,
                "cloud_resource_id": asset.cloud_resource_id,
                "organization_id": asset.organization_id,
                "provider": asset.provider,
                "account_id": asset.account_id,
                "region": asset.region,
                "resource_type": asset.resource_type,
                "name": asset.name,
                "tags": asset.tags,
                "environment": asset.environment,
                "is_public": asset.is_public,
                "risk_score": asset.risk_score,
                "open_findings_count": asset.open_findings_count,
                "raw": asset.raw,
            }

            # Convert previous Neo4j node to comparable dict
            prev_data: dict[str, Any] | None = None
            if previous_node:
                prev_data = {
                    "name": previous_node.get("name"),
                    "environment": previous_node.get("environment"),
                    "is_public": previous_node.get("is_public"),
                    "risk_score": previous_node.get("risk_score"),
                    "open_findings_count": previous_node.get("open_findings_count"),
                    "tags": previous_node.get("tags"),
                }

            async with self._db_session_factory() as db_session:
                snapshot_svc = SnapshotService(db_session)
                await snapshot_svc.create_snapshot(
                    asset_data=asset_data,
                    previous_snapshot=prev_data,
                )
        except Exception as e:
            logger.debug(f"Snapshot creation failed (non-fatal): {e}")

    # ─── Risk scoring ─────────────────────────────────────────────────────────

    async def compute_and_update_risk_score(self, asset_id: str) -> int:
        """Compute risk score for an asset and update the node.

        Emits asset.risk_score_changed when score changes by more than 5 points.
        """
        query = """
        MATCH (a:Asset {id: $asset_id})
        RETURN
            a.open_findings_count   AS findings_count,
            a.critical_count        AS critical_count,
            a.high_count            AS high_count,
            a.medium_count          AS medium_count,
            a.is_public             AS is_public,
            a.contains_pii          AS contains_pii,
            a.is_admin              AS is_admin,
            a.environment           AS env,
            a.risk_score            AS current_score,
            a.organization_id       AS org_id
        """
        result = await self._neo4j.execute_query(query, {"asset_id": asset_id})
        if not result:
            return 0

        row = result[0]
        critical = int(row.get("critical_count") or row.get("findings_count") or 0)
        high = int(row.get("high_count") or 0)
        medium = int(row.get("medium_count") or 0)
        is_public = bool(row.get("is_public") or False)
        contains_pii = bool(row.get("contains_pii") or False)
        is_admin = bool(row.get("is_admin") or False)
        environment = row.get("env") or "unknown"
        old_score = int(row.get("current_score") or 0)
        org_id = row.get("org_id") or ""

        new_score = self._calculate_risk_score(
            critical=critical,
            high=high,
            medium=medium,
            is_public=is_public,
            contains_pii=contains_pii,
            environment=environment,
            is_admin=is_admin,
        )

        update_query = """
        MATCH (a:Asset {id: $asset_id})
        SET a.risk_score = $risk_score
        RETURN a
        """
        await self._neo4j.execute_query(
            update_query, {"asset_id": asset_id, "risk_score": new_score}
        )

        # Emit event if score changed by more than 5 points (spec requirement)
        if self._producer and abs(new_score - old_score) > 5:
            await self._producer.emit_risk_score_changed(
                asset_id=asset_id,
                organization_id=org_id,
                old_score=old_score,
                new_score=new_score,
            )

        return new_score

    def _calculate_risk_score(
        self,
        critical: int,
        high: int,
        medium: int,
        is_public: bool,
        contains_pii: bool,
        environment: str,
        is_admin: bool = False,
    ) -> int:
        """Calculate risk score per spec formula.

        Formula:
          findings_score = min(critical*40 + high*20 + medium*5, 60)
          public_score   = 20 if is_public else 0
          pii_score      = 15 if contains_pii else 0
          admin_score    = 10 if is_admin else 0
          base           = findings_score + public_score + pii_score + admin_score
          if prod: base  = int(base * 1.5)
          return min(base, 100)
        """
        findings_score = min(critical * 40 + high * 20 + medium * 5, 60)
        public_score = 20 if is_public else 0
        pii_score = 15 if contains_pii else 0
        admin_score = 10 if is_admin else 0
        base_score = findings_score + public_score + pii_score + admin_score

        if environment == "prod":
            base_score = int(base_score * 1.5)

        return min(base_score, 100)

    # ─── Relationship resolution ──────────────────────────────────────────────

    async def _resolve_and_create_relationships(self, asset: AssetNode) -> None:
        """Auto-wire edges between this asset and related nodes in the same account."""
        type_suffix = asset.get_type_suffix()
        rules = RELATIONSHIP_RULES.get(type_suffix, [])

        for target_suffix, rel_type in rules:
            # Find nodes of the target type in the same account/org
            query = """
            MATCH (target:Asset)
            WHERE target.account_id = $account_id
              AND target.organization_id = $org_id
              AND target.id <> $self_id
              AND (
                toLower(target.resource_type) ENDS WITH $target_suffix
                OR toLower(target.resource_type) CONTAINS $target_suffix
              )
            RETURN target.id AS target_id
            LIMIT 20
            """
            results = await self._neo4j.execute_query(query, {
                "account_id": asset.account_id,
                "org_id": asset.organization_id,
                "target_suffix": target_suffix,
                "self_id": asset.id,
            })

            for row in results:
                target_id = row.get("target_id")
                if not target_id:
                    continue

                merge_query = f"""
                MATCH (a:Asset {{id: $source_id}})
                MATCH (b:Asset {{id: $target_id}})
                MERGE (a)-[r:{rel_type}]->(b)
                RETURN r
                """
                try:
                    await self._neo4j.execute_write(merge_query, {
                        "source_id": asset.id,
                        "target_id": target_id,
                    })
                    logger.debug(f"Edge: {asset.id} -[{rel_type}]-> {target_id}")

                    if self._producer:
                        await self._producer.emit_relationship_changed(
                            source_id=asset.id,
                            target_id=target_id,
                            relationship_type=rel_type,
                            organization_id=asset.organization_id,
                            action="created",
                        )
                except Exception as e:
                    logger.debug(f"Relationship skipped: {e}")

        # IAM policy analysis: link IAMRole → S3Bucket / RDSInstance via raw policy
        if type_suffix in ("iamrole",):
            await self._resolve_iam_access_edges(asset)

        # SecurityGroup with open inbound → virtual CIDR node
        if type_suffix == "securitygroup" and asset.is_public:
            await self._create_internet_exposure_edge(asset)

    async def _resolve_iam_access_edges(self, role_asset: AssetNode) -> None:
        """Parse IAM policy from raw data and create HAS_ACCESS_TO edges."""
        raw = role_asset.raw or {}
        # AWS IAM role: AssumeRolePolicyDocument or inline policies
        policies = raw.get("AttachedPolicies", []) or raw.get("policies", [])
        if not policies:
            return

        # Find S3 and RDS assets in the same account
        for target_type_suffix, rel_type in [("s3bucket", "HAS_ACCESS_TO"), ("rdsinstance", "HAS_ACCESS_TO")]:
            query = """
            MATCH (target:Asset)
            WHERE target.account_id = $account_id
              AND target.organization_id = $org_id
              AND toLower(target.resource_type) CONTAINS $target_suffix
            RETURN target.id AS target_id
            LIMIT 10
            """
            results = await self._neo4j.execute_query(query, {
                "account_id": role_asset.account_id,
                "org_id": role_asset.organization_id,
                "target_suffix": target_type_suffix,
            })
            for row in results:
                target_id = row.get("target_id")
                if not target_id:
                    continue
                merge_query = f"""
                MATCH (a:Asset {{id: $source_id}})
                MATCH (b:Asset {{id: $target_id}})
                MERGE (a)-[r:{rel_type}]->(b)
                RETURN r
                """
                try:
                    await self._neo4j.execute_write(merge_query, {
                        "source_id": role_asset.id,
                        "target_id": target_id,
                    })
                except Exception:
                    pass

    async def _create_internet_exposure_edge(self, asset: AssetNode) -> None:
        """Create a virtual CIDR node for 0.0.0.0/0 and link the security group."""
        cidr_id = f"cidr-internet-{asset.organization_id}"
        merge_cidr = """
        MERGE (c:CIDR {id: $cidr_id})
        ON CREATE SET c.value = "0.0.0.0/0", c.organization_id = $org_id
        RETURN c
        """
        await self._neo4j.execute_write(merge_cidr, {
            "cidr_id": cidr_id,
            "org_id": asset.organization_id,
        })

        merge_edge = """
        MATCH (sg:Asset {id: $sg_id})
        MATCH (c:CIDR {id: $cidr_id})
        MERGE (sg)-[r:ALLOWS_INBOUND_FROM]->(c)
        RETURN r
        """
        await self._neo4j.execute_write(merge_edge, {
            "sg_id": asset.id,
            "cidr_id": cidr_id,
        })

    # ─── Elasticsearch indexing ───────────────────────────────────────────────

    async def _index_asset(self, asset: AssetNode) -> None:
        """Index asset in Elasticsearch for full-text search (excludes raw field)."""
        if not self._es:
            return
        try:
            doc = {
                "id": asset.id,
                "cloud_resource_id": asset.cloud_resource_id,
                "provider": asset.provider,
                "account_id": asset.account_id,
                "region": asset.region,
                "resource_type": asset.resource_type,
                "name": asset.name,
                "tags": asset.tags,
                "environment": asset.environment,
                "is_public": asset.is_public,
                "risk_score": asset.risk_score,
                "open_findings_count": asset.open_findings_count,
                "organization_id": asset.organization_id,
                "last_seen_at": asset.last_seen_at.isoformat(),
            }
            await self._es.index_document("assets", asset.id, doc)
        except Exception as e:
            logger.debug(f"ES indexing failed for {asset.id}: {e}")

    # ─── Attack paths ─────────────────────────────────────────────────────────

    async def find_attack_paths(
        self,
        start_id: str | None = None,
        end_id: str | None = None,
        max_hops: int = 6,
    ) -> list[list[dict[str, Any]]]:
        """Find attack paths between assets (up to max_hops)."""
        if start_id and end_id:
            return await self._neo4j.find_paths(start_id, end_id, max_hops)

        # Default: internet-exposed → high-risk targets (spec query 2 variant)
        query = f"""
        MATCH path = (entry:Asset)-[*1..{max_hops}]->(target:Asset)
        WHERE entry.is_public = true
          AND target.risk_score > 50
          AND entry.id <> target.id
        WITH path, entry, target, length(path) AS pathLength
        RETURN [n IN nodes(path) | {{
            id: n.id,
            name: n.name,
            resource_type: n.resource_type,
            risk_score: n.risk_score
        }}] AS path_nodes,
        pathLength
        ORDER BY pathLength ASC
        LIMIT 10
        """
        result = await self._neo4j.execute_query(query)
        return [r.get("path_nodes", []) for r in result]

    async def find_pii_attack_paths(
        self, organization_id: str, max_hops: int = 6
    ) -> list[dict[str, Any]]:
        """Spec query 2: internet → sensitive database (up to max_hops hops).

        MATCH path = (i:InternetGateway)-[:CONNECTS_TO*1..6]->(db:RDSInstance)
        WHERE db.contains_pii = true
        RETURN path, length(path) ORDER BY length(path) ASC LIMIT 10
        """
        query = f"""
        MATCH path = (entry:Asset)-[*1..{max_hops}]->(db:Asset)
        WHERE entry.organization_id = $org_id
          AND entry.is_public = true
          AND (
            toLower(db.resource_type) CONTAINS 'rds'
            OR toLower(db.resource_type) CONTAINS 'database'
            OR toLower(db.resource_type) CONTAINS 'sql'
          )
          AND (db.contains_pii = true OR db.contains_sensitive_data = true)
        WITH path, entry, db, length(path) AS pathLength
        RETURN [n IN nodes(path) | {{
            id: n.id,
            name: n.name,
            resource_type: n.resource_type,
            risk_score: n.risk_score,
            contains_pii: n.contains_pii
        }}] AS path_nodes,
        pathLength
        ORDER BY pathLength ASC
        LIMIT 10
        """
        result = await self._neo4j.execute_query(query, {"org_id": organization_id})
        return [{"path": r.get("path_nodes", []), "length": r.get("pathLength", 0)} for r in result]

    # ─── Spec Cypher queries ──────────────────────────────────────────────────

    async def get_internet_exposed_with_findings(
        self, organization_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """All internet-exposed resources with open findings (spec query 1)."""
        query = """
        MATCH (r:Asset {organization_id: $org_id})-[:ALLOWS_INBOUND_FROM]->(c:CIDR {value: "0.0.0.0/0"})
        WHERE r.open_findings_count > 0
        RETURN r ORDER BY r.risk_score DESC LIMIT $limit
        """
        result = await self._neo4j.execute_query(
            query, {"org_id": organization_id, "limit": limit}
        )
        return [r["r"] for r in result]

    async def get_overprivileged_iam_roles(
        self, organization_id: str, unused_threshold: int = 20
    ) -> list[dict[str, Any]]:
        """Over-privileged IAM roles with access to production resources (spec query 3)."""
        query = """
        MATCH (role:Asset {organization_id: $org_id})-[:HAS_ACCESS_TO]->(res:Asset)
        WHERE role.resource_type CONTAINS 'iamrole'
          AND coalesce(role.unused_permissions_count, 0) > $threshold
          AND res.environment = 'prod'
        RETURN role, collect(res) AS prod_resources
        """
        result = await self._neo4j.execute_query(
            query, {"org_id": organization_id, "threshold": unused_threshold}
        )
        return result

    async def get_blast_radius(
        self, role_id: str, max_hops: int = 3
    ) -> list[dict[str, Any]]:
        """All resources a compromised IAM role could reach (spec query 4)."""
        query = f"""
        MATCH (role:Asset {{id: $role_id}})-[:HAS_ACCESS_TO*1..{max_hops}]->(target:Asset)
        RETURN target, labels(target) AS type
        """
        result = await self._neo4j.execute_query(query, {"role_id": role_id})
        return result

    # ─── Stats ────────────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        return await self._neo4j.get_stats()

    async def get_asset_counts_by_type(self, organization_id: str) -> dict[str, int]:
        cache_key = f"graph:stats:{organization_id}:by_type"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        query = """
        MATCH (a:Asset {organization_id: $org_id})
        RETURN a.resource_type AS resource_type, count(a) AS count
        ORDER BY count DESC
        """
        result = await self._neo4j.execute_query(query, {"org_id": organization_id})
        data = {r["resource_type"]: r["count"] for r in result}
        await self._cache_set(cache_key, data)
        return data

    async def get_asset_counts_by_provider(self, organization_id: str) -> dict[str, int]:
        cache_key = f"graph:stats:{organization_id}:by_provider"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        query = """
        MATCH (a:Asset {organization_id: $org_id})
        RETURN a.provider AS provider, count(a) AS count
        """
        result = await self._neo4j.execute_query(query, {"org_id": organization_id})
        data = {r["provider"]: r["count"] for r in result}
        await self._cache_set(cache_key, data)
        return data

    async def get_public_assets(self, organization_id: str) -> list[dict[str, Any]]:
        """Get all internet-exposed assets."""
        cache_key = f"graph:assets:{organization_id}:public"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        query = """
        MATCH (a:Asset {organization_id: $org_id, is_public: true})
        RETURN a ORDER BY a.risk_score DESC LIMIT 100
        """
        result = await self._neo4j.execute_query(query, {"org_id": organization_id})
        data = [r["a"] for r in result]
        await self._cache_set(cache_key, data)
        return data


class RiskScoreService:
    """Standalone risk score service — delegates to GraphService."""

    def __init__(self, graph_service: "GraphService"):
        self._graph = graph_service

    async def compute_risk_score(
        self,
        open_findings: dict[str, int],
        is_public: bool,
        contains_pii: bool,
        environment: str,
        is_admin: bool = False,
    ) -> int:
        critical = open_findings.get("CRITICAL", 0)
        high = open_findings.get("HIGH", 0)
        medium = open_findings.get("MEDIUM", 0)
        return self._graph._calculate_risk_score(
            critical, high, medium, is_public, contains_pii, environment, is_admin
        )

    async def update_asset_risk_score(self, asset_id: str) -> int:
        return await self._graph.compute_and_update_risk_score(asset_id)

    async def batch_update_risk_scores(self, asset_ids: list[str]) -> dict[str, int]:
        results = {}
        for asset_id in asset_ids:
            try:
                results[asset_id] = await self.update_asset_risk_score(asset_id)
            except Exception as e:
                logger.error(f"Failed to update risk score for {asset_id}: {e}")
                results[asset_id] = 0
        return results
