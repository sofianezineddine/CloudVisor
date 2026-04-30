"""
Inline rule seeder — reads index.json files and upserts new rules into the policy DB.
Uses direct asyncpg connection to handle json[] column properly.
"""
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

RULES_BASE = Path(os.environ.get("POLICY_RULES_REPO_PATH", "/app/rules/rego"))


async def seed_from_index(session_factory, opa_service) -> None:
    """Read all index.json files and upsert new rules into the DB via direct asyncpg."""
    import asyncpg as _asyncpg

    db_url = os.environ.get("DB_URL", "")
    asyncpg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        conn = await _asyncpg.connect(asyncpg_url)
        logger.info("Index seeder: connected to DB via asyncpg")
    except Exception as e:
        logger.warning(f"Index seeder: failed to connect to DB via asyncpg: {e}")
        return

    total_new = 0
    total_updated = 0

    try:
        for provider in ("aws", "azure", "gcp", "oci"):
            index_path = RULES_BASE / "cspm" / provider / "index.json"
            if not index_path.exists():
                continue

            try:
                with open(index_path, "r") as f:
                    index_data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read {index_path}: {e}")
                continue

            rules = index_data.get("rules", [])
            logger.info(f"Index seeder: processing {len(rules)} {provider.upper()} rules")

            for rule_info in rules:
                rule_id = rule_info.get("id")
                if not rule_id:
                    continue

                # Read rego file
                rego_file = rule_info.get("file", "")
                rego_path = RULES_BASE / "cspm" / provider / rego_file
                rego_code = ""
                if rego_path.exists():
                    try:
                        rego_code = rego_path.read_text(encoding="utf-8")
                    except Exception:
                        pass
                if not rego_code:
                    rego_code = f"package cloudvisor.cspm.{provider}.{rule_id.replace('-', '_')}\n"

                # compliance as list of JSON strings for json[] column
                compliance = rule_info.get("compliance", [])
                compliance_pg = [json.dumps(c) for c in compliance]

                try:
                    existing = await conn.fetchrow(
                        "SELECT id FROM rules WHERE rule_id = $1 AND organization_id IS NULL",
                        rule_id
                    )

                    now = datetime.utcnow()

                    if existing:
                        await conn.execute(
                            "UPDATE rules SET compliance_mapping = $1, rego_code = $2, updated_at = $3 "
                            "WHERE rule_id = $4 AND organization_id IS NULL",
                            compliance_pg, rego_code, now, rule_id
                        )
                        total_updated += 1
                    else:
                        new_id = str(uuid.uuid4())
                        await conn.execute(
                            "INSERT INTO rules "
                            "(id, organization_id, rule_id, title, description, severity, category, "
                            "provider, resource_type, remediation, rego_code, version, "
                            "compliance_mapping, tags, is_builtin, is_custom, is_enabled, "
                            "created_at, updated_at) "
                            "VALUES ($1, NULL, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, "
                            "$12, $13, true, false, true, $14, $14)",
                            new_id,
                            rule_id,
                            rule_info.get("title", rule_id),
                            rule_info.get("description", ""),
                            rule_info.get("severity", "MEDIUM"),
                            rule_info.get("category", "cspm"),
                            provider,
                            rule_info.get("resource_type", ""),
                            rule_info.get("remediation", ""),
                            rego_code,
                            rule_info.get("version", "1.0.0"),
                            compliance_pg,
                            [],
                            now,
                        )
                        total_new += 1

                    # Load into OPA
                    policy_name = f"cloudvisor.cspm.{provider}.{rule_id.replace('-', '_')}"
                    await opa_service.load_policy(policy_name, rego_code)

                except Exception as e:
                    logger.warning(f"Failed to seed rule {rule_id}: {type(e).__name__}: {str(e)[:200]}")

    finally:
        await conn.close()

    logger.info(f"Index seeder complete: {total_new} new, {total_updated} updated")
