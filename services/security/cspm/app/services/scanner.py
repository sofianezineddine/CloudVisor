import hashlib
import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FindingResult:
    rule_id: str
    title: str
    description: str
    severity: str
    remediation: str
    compliance_mapping: list[dict]


def compute_fingerprint(rule_id: str, resource_id: str, account_id: str, org_id: str) -> str:
    """Deterministic SHA-256 fingerprint for deduplication."""
    raw = f"{rule_id}{resource_id}{account_id}{org_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def evaluate_resource(
    resource: dict[str, Any],
    org_id: str,
    policy_service_url: str,
) -> list[FindingResult]:
    """Call Policy service and return violations."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{policy_service_url}/internal/policy/evaluate",
                json={"resources": [resource], "org_id": org_id},
                headers={"X-Org-ID": org_id},
            )
            if response.status_code != 200:
                logger.error(
                    f"Policy evaluate failed: {response.status_code} {response.text[:200]}"
                )
                return []
            data = response.json()
            findings = data.get("findings", [])
            return [
                FindingResult(
                    rule_id=f.get("rule_id", "unknown"),
                    title=f.get("title", ""),
                    description=f.get("description", ""),
                    severity=f.get("severity", "MEDIUM"),
                    remediation=f.get("remediation", ""),
                    compliance_mapping=f.get("compliance_mapping", []),
                )
                for f in findings
            ]
    except Exception as e:
        logger.error(f"Error evaluating resource {resource.get('id', '?')}: {e}")
        return []
