"""FastAPI dependency injection for the Policy service."""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from functools import lru_cache

import redis.asyncio as redis
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from cloudvisor_utils.config import CloudvisorSettings

from .config import PolicySettings, get_policy_settings
from .database import create_engine, create_session, create_db_session

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None
_redis_client = None
_opa_service = None


async def init_dependencies(settings: CloudvisorSettings, policy_settings: PolicySettings) -> None:
    """Initialize all dependencies at app startup."""
    global _engine, _session_factory, _redis_client, _opa_service

    from ..models import Base, FrameworkModel, RuleModel
    from ..opa import OPAService

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    _engine = create_engine(settings.db.url)
    _session_factory = create_session(_engine)

    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Policy tables created")

    # ── Redis ─────────────────────────────────────────────────────────────────
    _redis_client = redis.from_url(
        settings.redis.url,
        decode_responses=True,
    )

    # ── OPA ───────────────────────────────────────────────────────────────────
    _opa_service = OPAService(policy_settings.opa_url)
    healthy = await _opa_service.check_health()
    if healthy:
        logger.info(f"OPA connected at {policy_settings.opa_url}")
    else:
        logger.warning(f"OPA not reachable at {policy_settings.opa_url} — evaluation will fail")

    # ── Seed built-in rules from Rego files ──────────────────────────────────
    await _seed_builtin_rules(_session_factory, _opa_service)

    # ── Start PolicyLoader hot-reload polling ─────────────────────────────────
    from ..opa import PolicyLoader
    import asyncio as _asyncio
    rules_path = os.environ.get("POLICY_RULES_REPO_PATH", "/app/rules/rego")
    _policy_loader = PolicyLoader(_opa_service, rules_path)
    # Load all rules into OPA on startup, then start hot-reload polling
    loaded_count = await _policy_loader.load_all_rules()
    logger.info(f"PolicyLoader: loaded {loaded_count} rules into OPA from {rules_path}")
    _asyncio.create_task(_policy_loader.start_polling())
    logger.info("PolicyLoader hot-reload polling started")

    # ── Kafka producer + consumer ─────────────────────────────────────────────
    kafka_servers = settings.kafka.bootstrap_servers

    # Producer: publishes finding.raw events
    from aiokafka import AIOKafkaProducer
    _kafka_producer = AIOKafkaProducer(
        bootstrap_servers=kafka_servers,
        acks="all",
        retry_backoff_ms=500,
    )
    try:
        await _kafka_producer.start()
        logger.info("Policy Kafka producer started")
    except Exception as e:
        logger.warning(f"Policy Kafka producer failed: {e}")
        _kafka_producer = None

    # Consumer: evaluates resources on discovery
    from ..consumers.resource_events import ResourceEventConsumer
    import asyncio as _asyncio

    resource_consumer = ResourceEventConsumer(
        bootstrap_servers=kafka_servers,
        session_factory=_session_factory,
        opa_service=_opa_service,
        kafka_producer=_kafka_producer,
    )
    try:
        await resource_consumer.start()
        _asyncio.create_task(resource_consumer.run())
        logger.info("Policy resource event consumer started")
    except Exception as e:
        logger.warning(f"Policy resource consumer failed to start: {e}")

    logger.info("Policy service dependencies initialized")


async def _seed_builtin_rules(session_factory, opa_service) -> None:
    """
    Seed the database with built-in rules.
    Priority: load from /app/rules/rego/ files first, fall back to hardcoded.
    Also loads all Rego files into OPA.
    """
    from datetime import datetime
    from sqlalchemy import select, func
    from ..models import RuleModel
    import os, glob

    async with session_factory() as session:
        count_result = await session.execute(
            select(func.count()).select_from(RuleModel).where(RuleModel.is_builtin == True)
        )
        count = count_result.scalar() or 0
        if count > 0:
            logger.info(f"Policy DB already has {count} built-in rules — loading into OPA only")
            # Still load into OPA (it loses state on restart)
            await _load_rules_into_opa(session_factory, opa_service)
            # Add any new rules from index.json that aren't in the DB yet
            await _seed_new_rules_from_index(session_factory, opa_service)
            return

    # Load from Rego files if available
    rules_path = os.environ.get("POLICY_RULES_REPO_PATH", "/app/rules/rego")
    rego_files = glob.glob(f"{rules_path}/**/*.rego", recursive=True)

    if rego_files:
        logger.info(f"Loading {len(rego_files)} Rego files from {rules_path}")
        await _load_rego_files(session_factory, opa_service, rego_files, rules_path)
    else:
        logger.info("No Rego files found — seeding hardcoded built-in rules")
        await _seed_hardcoded_rules(session_factory, opa_service)


async def _load_rego_files(session_factory, opa_service, rego_files: list, rules_path: str) -> None:
    """Parse Rego files, extract metadata, store in DB, load into OPA."""
    import os
    from datetime import datetime
    from pathlib import Path
    from ..models import RuleModel
    from ..opa import RegoParser

    parser = RegoParser()
    loaded = 0

    async with session_factory() as session:
        for rego_file in rego_files:
            try:
                with open(rego_file, "r") as f:
                    rego_code = f.read()

                metadata = parser.extract_metadata(rego_code)
                if not metadata.get("title"):
                    continue  # Skip files without metadata

                relative_path = os.path.relpath(rego_file, rules_path)
                rule_id = relative_path.replace("\\", "/").replace(".rego", "").replace("/", "_")
                import uuid as _uuid
                rule = RuleModel(
                    id=str(_uuid.uuid5(_uuid.NAMESPACE_DNS, relative_path.replace("\\", "/").replace(".rego", ""))),
                    rule_id=rule_id,
                    title=metadata.get("title", rule_id),
                    description=metadata.get("description"),
                    severity=metadata.get("severity", "MEDIUM"),
                    category=metadata.get("category", "cspm"),
                    provider=metadata.get("provider"),
                    resource_type=metadata.get("resource_type"),
                    remediation=metadata.get("remediation"),
                    rego_code=rego_code,
                    version=metadata.get("version", "1.0.0"),
                    compliance_mapping=[],
                    tags=metadata.get("tags", "").split(",") if metadata.get("tags") else [],
                    is_builtin=True,
                    is_custom=False,
                    is_enabled=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(rule)

                # Load into OPA using the rego package name as the path
                package_name = parser.extract_package(rego_code)
                policy_name = package_name.replace(".", "/") if package_name else f"cloudvisor/{metadata.get('category', 'cspm')}/{rule_id}"
                await opa_service.load_policy(policy_name, rego_code)
                loaded += 1

            except Exception as e:
                logger.warning(f"Failed to load {rego_file}: {e}")

        await session.commit()

    logger.info(f"Loaded {loaded} rules from Rego files")


async def _load_rules_into_opa(session_factory, opa_service) -> None:
    """Load all existing DB rules into OPA (called on restart)."""
    from sqlalchemy import select
    from ..models import RuleModel
    from ..opa import RegoParser

    parser = RegoParser()

    async with session_factory() as session:
        result = await session.execute(
            select(RuleModel).where(RuleModel.is_enabled == True)
        )
        rules = result.scalars().all()
        for rule in rules:
            try:
                package_name = parser.extract_package(rule.rego_code or "")
                policy_name = package_name.replace(".", "/") if package_name else f"cloudvisor/{rule.category}/{rule.rule_id}"
                await opa_service.load_policy(policy_name, rule.rego_code)
            except Exception as e:
                logger.debug(f"OPA load for {rule.rule_id}: {e}")

    logger.info(f"Reloaded rules into OPA")


def _get_builtin_rules() -> list[dict]:
    """Return the built-in rule library."""
    import uuid
    return [
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "aws-s3-public-access")),
            "rule_id": "aws-s3-public-access",
            "title": "S3 Bucket has public access enabled",
            "description": "S3 bucket allows public read or write access, exposing data to the internet.",
            "severity": "CRITICAL",
            "category": "cspm",
            "provider": "aws",
            "resource_type": "aws::s3::bucket",
            "remediation": "Enable S3 Block Public Access settings on the bucket and bucket policy.",
            "compliance_mapping": [
                {"framework": "CIS-AWS", "control": "2.1.5"},
                {"framework": "SOC2", "control": "CC6.1"},
                {"framework": "PCI-DSS", "control": "1.3"},
            ],
            "tags": ["s3", "public-access", "data-exposure"],
            "rego_code": '''package cloudvisor.cspm.aws_s3_public_access

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::s3::bucket"
    input.resource.is_public == true
    msg := sprintf("S3 bucket '%v' has public access enabled", [input.resource.name])
}
''',
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "aws-iam-root-mfa")),
            "rule_id": "aws-iam-root-mfa",
            "title": "IAM root account MFA not enabled",
            "description": "The root AWS account does not have MFA enabled, creating a critical security risk.",
            "severity": "CRITICAL",
            "category": "cspm",
            "provider": "aws",
            "resource_type": "aws::iam::user",
            "remediation": "Enable MFA on the root account immediately. Use a hardware MFA device for root.",
            "compliance_mapping": [
                {"framework": "CIS-AWS", "control": "1.5"},
                {"framework": "SOC2", "control": "CC6.1"},
            ],
            "tags": ["iam", "mfa", "root"],
            "rego_code": '''package cloudvisor.cspm.aws_iam_root_mfa

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::iam::user"
    input.resource.name == "root"
    not input.resource.raw.MFAActive
    msg := "IAM root account does not have MFA enabled"
}
''',
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "aws-rds-public")),
            "rule_id": "aws-rds-public",
            "title": "RDS instance is publicly accessible",
            "description": "RDS database instance is configured to be publicly accessible from the internet.",
            "severity": "HIGH",
            "category": "cspm",
            "provider": "aws",
            "resource_type": "aws::rds::dbinstance",
            "remediation": "Set PubliclyAccessible to false on the RDS instance and restrict security group access.",
            "compliance_mapping": [
                {"framework": "CIS-AWS", "control": "2.3.2"},
                {"framework": "PCI-DSS", "control": "1.3"},
                {"framework": "HIPAA", "control": "164.312"},
            ],
            "tags": ["rds", "database", "public-access"],
            "rego_code": '''package cloudvisor.cspm.aws_rds_public

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::rds::dbinstance"
    input.resource.raw.PubliclyAccessible == true
    msg := sprintf("RDS instance '%v' is publicly accessible", [input.resource.name])
}
''',
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "aws-sg-unrestricted-ssh")),
            "rule_id": "aws-sg-unrestricted-ssh",
            "title": "Security group allows unrestricted SSH access",
            "description": "Security group has an inbound rule allowing SSH (port 22) from 0.0.0.0/0.",
            "severity": "HIGH",
            "category": "cspm",
            "provider": "aws",
            "resource_type": "aws::ec2::securitygroup",
            "remediation": "Restrict SSH access to specific IP ranges. Use AWS Systems Manager Session Manager instead.",
            "compliance_mapping": [
                {"framework": "CIS-AWS", "control": "5.2"},
                {"framework": "SOC2", "control": "CC6.6"},
            ],
            "tags": ["security-group", "ssh", "network"],
            "rego_code": '''package cloudvisor.cspm.aws_sg_unrestricted_ssh

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::ec2::securitygroup"
    rule := input.resource.raw.IpPermissions[_]
    rule.FromPort <= 22
    rule.ToPort >= 22
    range := rule.IpRanges[_]
    range.CidrIp == "0.0.0.0/0"
    msg := sprintf("Security group '%v' allows unrestricted SSH from 0.0.0.0/0", [input.resource.name])
}
''',
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "aws-cloudtrail-disabled")),
            "rule_id": "aws-cloudtrail-disabled",
            "title": "CloudTrail logging not enabled",
            "description": "AWS CloudTrail is not enabled, meaning API activity is not being logged.",
            "severity": "HIGH",
            "category": "cspm",
            "provider": "aws",
            "resource_type": "aws::cloudtrail::trail",
            "remediation": "Enable CloudTrail in all regions with log file validation and S3 encryption.",
            "compliance_mapping": [
                {"framework": "CIS-AWS", "control": "3.1"},
                {"framework": "SOC2", "control": "CC7.2"},
                {"framework": "PCI-DSS", "control": "10.1"},
            ],
            "tags": ["cloudtrail", "logging", "audit"],
            "rego_code": '''package cloudvisor.cspm.aws_cloudtrail_disabled

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::cloudtrail::trail"
    not input.resource.raw.IsLogging
    msg := sprintf("CloudTrail trail '%v' is not logging", [input.resource.name])
}
''',
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "aws-ec2-imdsv2")),
            "rule_id": "aws-ec2-imdsv2",
            "title": "EC2 instance does not enforce IMDSv2",
            "description": "EC2 instance allows IMDSv1 which is vulnerable to SSRF attacks.",
            "severity": "MEDIUM",
            "category": "cspm",
            "provider": "aws",
            "resource_type": "aws::ec2::instance",
            "remediation": "Set HttpTokens to 'required' in the instance metadata options to enforce IMDSv2.",
            "compliance_mapping": [
                {"framework": "CIS-AWS", "control": "5.6"},
            ],
            "tags": ["ec2", "imds", "ssrf"],
            "rego_code": '''package cloudvisor.cspm.aws_ec2_imdsv2

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::ec2::instance"
    input.resource.raw.MetadataOptions.HttpTokens != "required"
    msg := sprintf("EC2 instance '%v' does not enforce IMDSv2", [input.resource.name])
}
''',
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "aws-kms-rotation")),
            "rule_id": "aws-kms-rotation",
            "title": "KMS key rotation not enabled",
            "description": "AWS KMS customer-managed key does not have automatic rotation enabled.",
            "severity": "MEDIUM",
            "category": "cspm",
            "provider": "aws",
            "resource_type": "aws::kms::key",
            "remediation": "Enable automatic key rotation for all customer-managed KMS keys.",
            "compliance_mapping": [
                {"framework": "CIS-AWS", "control": "3.8"},
                {"framework": "PCI-DSS", "control": "3.6"},
            ],
            "tags": ["kms", "encryption", "rotation"],
            "rego_code": '''package cloudvisor.cspm.aws_kms_rotation

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::kms::key"
    not input.resource.raw.KeyRotationEnabled
    msg := sprintf("KMS key '%v' does not have automatic rotation enabled", [input.resource.name])
}
''',
        },
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "aws-vpc-flow-logs")),
            "rule_id": "aws-vpc-flow-logs",
            "title": "VPC flow logs not enabled",
            "description": "VPC does not have flow logs enabled, limiting network traffic visibility.",
            "severity": "MEDIUM",
            "category": "cspm",
            "provider": "aws",
            "resource_type": "aws::ec2::vpc",
            "remediation": "Enable VPC flow logs and send them to CloudWatch Logs or S3.",
            "compliance_mapping": [
                {"framework": "CIS-AWS", "control": "3.9"},
                {"framework": "SOC2", "control": "CC7.2"},
            ],
            "tags": ["vpc", "flow-logs", "network"],
            "rego_code": '''package cloudvisor.cspm.aws_vpc_flow_logs

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::ec2::vpc"
    not input.resource.raw.FlowLogsEnabled
    msg := sprintf("VPC '%v' does not have flow logs enabled", [input.resource.name])
}
''',
        },
    ]


async def _seed_new_rules_from_index(session_factory, opa_service) -> None:
    """Add new rules from index.json files that aren't already in the DB."""
    import json as _json
    import os as _os
    import uuid as _uuid
    from datetime import datetime as _dt
    from pathlib import Path as _Path
    from sqlalchemy import select as _select
    from ..models import RuleModel

    rules_path = _os.environ.get("POLICY_RULES_REPO_PATH", "/app/rules/rego")
    total_new = 0

    for provider in ("aws", "azure", "gcp", "oci"):
        index_path = _Path(rules_path) / "cspm" / provider / "index.json"
        if not index_path.exists():
            continue

        try:
            with open(index_path, "r") as f:
                index_data = _json.load(f)
        except Exception:
            continue

        for rule_info in index_data.get("rules", []):
            rule_id = rule_info.get("id")
            if not rule_id:
                continue

            # Check if rule already exists
            async with session_factory() as session:
                existing = (await session.execute(
                    _select(RuleModel).where(
                        RuleModel.rule_id == rule_id,
                        RuleModel.organization_id == None,  # noqa: E711
                    )
                )).scalar_one_or_none()

                if existing:
                    continue

                # Read rego file
                rego_file = rule_info.get("file", "")
                rego_path = _Path(rules_path) / "cspm" / provider / rego_file
                rego_code = ""
                if rego_path.exists():
                    try:
                        rego_code = rego_path.read_text(encoding="utf-8")
                    except Exception:
                        pass
                if not rego_code:
                    rego_code = f"package cloudvisor.cspm.{provider}.{rule_id.replace('-', '_')}\n"

                now = _dt.utcnow()
                try:
                    from sqlalchemy import text as _text
                    new_id = str(_uuid.uuid4())
                    await session.execute(_text("""
                        INSERT INTO rules (
                            id, organization_id, rule_id, title, description,
                            severity, category, provider, resource_type, remediation,
                            rego_code, version, compliance_mapping, tags,
                            is_builtin, is_custom, is_enabled, created_at, updated_at
                        ) VALUES (
                            :id, NULL, :rule_id, :title, :description,
                            :severity, :category, :provider, :resource_type, :remediation,
                            :rego_code, :version, ARRAY[]::json[], ARRAY[]::json[],
                            true, false, true, :now, :now
                        )
                    """), {
                        "id": new_id,
                        "rule_id": rule_id,
                        "title": rule_info.get("title", rule_id),
                        "description": rule_info.get("description", ""),
                        "severity": rule_info.get("severity", "MEDIUM"),
                        "category": rule_info.get("category", "cspm"),
                        "provider": provider,
                        "resource_type": rule_info.get("resource_type", ""),
                        "remediation": rule_info.get("remediation", ""),
                        "rego_code": rego_code,
                        "version": rule_info.get("version", "1.0.0"),
                        "now": now,
                    })
                    await session.commit()
                    total_new += 1

                    # Load into OPA
                    policy_name = f"cloudvisor.cspm.{provider}.{rule_id.replace('-', '_')}"
                    await opa_service.load_policy(policy_name, rego_code)

                except Exception as e:
                    logger.warning(f"Failed to add rule {rule_id}: {e}")
                    await session.rollback()

    if total_new > 0:
        logger.info(f"Added {total_new} new rules from index.json files")


async def _seed_hardcoded_rules(session_factory, opa_service) -> None:
    """Seed the database with hardcoded built-in rules and load them into OPA."""
    from datetime import datetime
    from ..models import RuleModel

    rules_data = _get_builtin_rules()
    loaded = 0

    async with session_factory() as session:
        for rule_data in rules_data:
            rule = RuleModel(
                id=rule_data["id"],
                rule_id=rule_data["rule_id"],
                title=rule_data["title"],
                description=rule_data["description"],
                severity=rule_data["severity"],
                category=rule_data["category"],
                provider=rule_data.get("provider"),
                resource_type=rule_data.get("resource_type"),
                remediation=rule_data.get("remediation"),
                rego_code=rule_data["rego_code"],
                version="1.0.0",
                compliance_mapping=rule_data.get("compliance_mapping", []),
                tags=rule_data.get("tags", []),
                is_builtin=True,
                is_custom=False,
                is_enabled=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(rule)

            # Load into OPA
            rule_id_normalized = rule_data["rule_id"].replace("-", "_")
            policy_name = f"cloudvisor/{rule_data['category']}/{rule_id_normalized}"
            if await opa_service.load_policy(policy_name, rule_data["rego_code"]):
                loaded += 1

        await session.commit()

    logger.info(f"Seeded {loaded} hardcoded built-in rules into DB and OPA")


async def shutdown_dependencies() -> None:
    global _redis_client, _engine, _opa_service

    if _opa_service:
        await _opa_service.close()
        _opa_service = None

    if _redis_client:
        await _redis_client.close()
        _redis_client = None

    if _engine:
        await _engine.dispose()
        _engine = None

    logger.info("Policy service dependencies shut down")


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database sessions with RLS — org_id from JWT."""
    org_id = _extract_org_id(request)
    session_factory = request.app.state.session_factory
    async with create_db_session(session_factory, org_id) as session:
        yield session


def _extract_org_id(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import base64, json
            token = auth[7:]
            parts = token.split(".")
            if len(parts) == 3:
                payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                return payload.get("org_id")
        except Exception:
            pass
    return request.headers.get("X-Org-ID")


async def get_redis(request: Request):
    yield request.app.state.redis


@lru_cache
def get_policy_settings_cached() -> PolicySettings:
    return get_policy_settings()
