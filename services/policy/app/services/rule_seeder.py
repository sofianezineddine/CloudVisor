"""
Rule Seeder — seeds built-in rules from index.json files into the policy DB.
Covers CSPM (all providers), KSPM, CDR, and CICD categories.
Runs on startup. Uses upsert logic so it's safe to run multiple times.
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.policy import RuleModel

import os

logger = logging.getLogger(__name__)

# Rules are at /app/rules/rego/ inside the container (copied by Dockerfile)
_THIS_FILE = Path(__file__).resolve()
_RULES_ENV = os.environ.get("POLICY_RULES_REPO_PATH", "")
if _RULES_ENV:
    RULES_BASE = Path(_RULES_ENV)
elif Path("/app/rules/rego").exists():
    RULES_BASE = Path("/app/rules/rego")
else:
    # Local dev: go up from services/policy/app/services/ to repo root
    RULES_BASE = _THIS_FILE.parent.parent.parent.parent.parent / "rules" / "rego"


# All index.json locations to seed from
_INDEX_LOCATIONS = [
    # CSPM per provider
    ("cspm", "aws",   RULES_BASE / "cspm" / "aws"   / "index.json"),
    ("cspm", "azure", RULES_BASE / "cspm" / "azure" / "index.json"),
    ("cspm", "gcp",   RULES_BASE / "cspm" / "gcp"   / "index.json"),
    ("cspm", "oci",   RULES_BASE / "cspm" / "oci"   / "index.json"),
    # Non-CSPM categories
    ("kspm", None,    RULES_BASE / "kspm"  / "index.json"),
    ("cdr",  None,    RULES_BASE / "cdr"   / "index.json"),
    ("cicd", None,    RULES_BASE / "cicd"  / "index.json"),
]


async def seed_builtin_rules(session_factory) -> None:
    """
    Read all index.json files and upsert them into the rules table.
    Covers CSPM (AWS/Azure/GCP/OCI), KSPM, CDR, and CICD.
    """
    total_seeded = 0
    total_skipped = 0

    for category, provider, index_path in _INDEX_LOCATIONS:
        if not index_path.exists():
            logger.debug(f"No index.json at {index_path}, skipping")
            continue

        try:
            with open(index_path, "r") as f:
                index_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read {index_path}: {e}")
            continue

        rules = index_data.get("rules", [])
        label = f"{provider.upper()} " if provider else ""
        logger.info(f"Seeding {len(rules)} {label}{category.upper()} rules into policy DB")

        # Determine the rego files base directory
        if provider:
            rego_dir = RULES_BASE / category / provider
        else:
            rego_dir = RULES_BASE / category

        for rule_info in rules:
            rule_id = rule_info.get("id")
            if not rule_id:
                continue

            # Read the rego file content
            rego_file = rule_info.get("file", "")
            rego_path = rego_dir / rego_file
            rego_code = ""
            if rego_path.exists():
                try:
                    rego_code = rego_path.read_text(encoding="utf-8")
                except Exception:
                    pass
            if not rego_code:
                pkg_suffix = rule_id.replace("-", "_")
                rego_code = f"# Rule: {rule_id}\npackage cloudvisor.{category}.{pkg_suffix}\n"

            compliance = rule_info.get("compliance", [])

            async with session_factory() as db:
                try:
                    existing = (await db.execute(
                        select(RuleModel).where(
                            RuleModel.rule_id == rule_id,
                            RuleModel.organization_id == None,  # noqa: E711
                        )
                    )).scalar_one_or_none()

                    now = datetime.utcnow()

                    if existing:
                        existing.title = rule_info.get("title", existing.title)
                        existing.severity = rule_info.get("severity", existing.severity)
                        existing.compliance_mapping = compliance
                        existing.resource_type = rule_info.get("resource_type", existing.resource_type)
                        existing.rego_code = rego_code
                        existing.updated_at = now
                        total_skipped += 1
                    else:
                        db.add(RuleModel(
                            id=str(uuid.uuid4()),
                            organization_id=None,
                            rule_id=rule_id,
                            title=rule_info.get("title", rule_id),
                            description=rule_info.get("description", ""),
                            severity=rule_info.get("severity", "MEDIUM"),
                            category=category,
                            provider=provider or rule_info.get("provider"),
                            resource_type=rule_info.get("resource_type", ""),
                            remediation=rule_info.get("remediation", ""),
                            rego_code=rego_code,
                            version=rule_info.get("version", "1.0.0"),
                            compliance_mapping=compliance,
                            tags=[],
                            is_builtin=True,
                            is_custom=False,
                            is_enabled=True,
                            created_at=now,
                            updated_at=now,
                        ))
                        total_seeded += 1

                    await db.commit()
                except Exception as e:
                    logger.error(f"Failed to seed rule {rule_id}: {e}")
                    await db.rollback()

    logger.info(f"Rule seeding complete: {total_seeded} new, {total_skipped} updated")
