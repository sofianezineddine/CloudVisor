"""
Rule Seeder — seeds built-in CSPM rules from index.json files into the policy DB.
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
# Fall back to relative path for local development
_THIS_FILE = Path(__file__).resolve()
# Try env var first, then container path, then relative
_RULES_ENV = os.environ.get("POLICY_RULES_REPO_PATH", "")
if _RULES_ENV:
    RULES_BASE = Path(_RULES_ENV)
elif Path("/app/rules/rego").exists():
    RULES_BASE = Path("/app/rules/rego")
else:
    # Local dev: go up from services/policy/app/services/ to repo root
    RULES_BASE = _THIS_FILE.parent.parent.parent.parent.parent / "rules" / "rego"


async def seed_builtin_rules(session_factory) -> None:
    """
    Read all index.json files from rules/rego/cspm/{provider}/
    and upsert them into the rules table.
    """
    total_seeded = 0
    total_skipped = 0

    for provider in ("aws", "azure", "gcp", "oci"):
        index_path = RULES_BASE / "cspm" / provider / "index.json"
        if not index_path.exists():
            logger.debug(f"No index.json for {provider}, skipping")
            continue

        try:
            with open(index_path, "r") as f:
                index_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read {index_path}: {e}")
            continue

        rules = index_data.get("rules", [])
        logger.info(f"Seeding {len(rules)} {provider.upper()} rules into policy DB")

        for rule_info in rules:
            rule_id = rule_info.get("id")
            if not rule_id:
                continue

            # Read the rego file content
            rego_file = rule_info.get("file", "")
            rego_path = RULES_BASE / "cspm" / provider / rego_file
            rego_code = ""
            if rego_path.exists():
                try:
                    rego_code = rego_path.read_text(encoding="utf-8")
                except Exception:
                    rego_code = f"# Rule: {rule_id}\npackage cloudvisor.cspm.{provider}.{rule_id.replace('-', '_')}\n"
            else:
                rego_code = f"# Rule: {rule_id}\npackage cloudvisor.cspm.{provider}.{rule_id.replace('-', '_')}\n"

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
                        # Update title/severity/compliance if changed
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
                            category=rule_info.get("category", "cspm"),
                            provider=provider,
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
