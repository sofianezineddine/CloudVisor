"""Rule loader service for loading CSPM rules into OPA."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from ..opa import OPAService

logger = logging.getLogger(__name__)


class RuleLoaderService:
    """Service for loading CSPM rules from filesystem into OPA."""

    def __init__(self, opa_service: OPAService):
        self.opa_service = opa_service
        self.rules_base_path = Path(__file__).parent.parent / "rules" / "rego"

    async def load_all_rules(self) -> Dict[str, Any]:
        """Load all CSPM rules into OPA."""
        results = {
            "loaded": 0,
            "failed": 0,
            "rules": [],
            "errors": []
        }

        for provider in ("aws", "azure", "gcp", "oci"):
            provider_results = await self._load_provider_rules(provider)
            results["loaded"] += provider_results["loaded"]
            results["failed"] += provider_results["failed"]
            results["rules"].extend(provider_results["rules"])
            results["errors"].extend(provider_results["errors"])

        logger.info(f"Rule loading complete: {results['loaded']} loaded, {results['failed']} failed")
        return results

    async def _load_provider_rules(self, provider: str) -> Dict[str, Any]:
        """Load CSPM rules for a specific cloud provider."""
        results = {"loaded": 0, "failed": 0, "rules": [], "errors": []}

        rules_path = self.rules_base_path / "cspm" / provider
        if not rules_path.exists():
            return results

        index_path = rules_path / "index.json"
        if not index_path.exists():
            logger.warning(f"No index.json for {provider} CSPM rules")
            return results

        try:
            with open(index_path, 'r') as f:
                index_data = json.load(f)

            rules = index_data.get("rules", [])
            logger.info(f"Loading {len(rules)} {provider.upper()} CSPM rules")

            for rule_info in rules:
                rule_file = rule_info.get("file")
                rule_id = rule_info.get("id")

                if not rule_file or not rule_id:
                    results["failed"] += 1
                    continue

                rule_path = rules_path / rule_file
                if not rule_path.exists():
                    results["failed"] += 1
                    results["errors"].append(f"Rule file not found: {rule_file}")
                    continue

                try:
                    with open(rule_path, 'r') as f:
                        rego_content = f.read()

                    policy_name = f"cloudvisor.cspm.{provider}.{rule_id.replace('-', '_')}"
                    success = await self.opa_service.load_policy(
                        policy_name=policy_name,
                        rego_code=rego_content,
                        metadata=rule_info
                    )

                    if success:
                        results["loaded"] += 1
                        results["rules"].append({
                            "id": rule_id,
                            "policy_name": policy_name,
                            "file": rule_file,
                            "title": rule_info.get("title"),
                            "severity": rule_info.get("severity"),
                            "provider": provider,
                        })
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"Failed to load rule: {rule_id}")

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Error loading rule {rule_id}: {str(e)}")
                    logger.error(f"Error loading rule {rule_id}: {e}")

        except Exception as e:
            logger.error(f"Error loading {provider} CSPM rules index: {e}")
            results["errors"].append(f"Error loading {provider} rules index: {str(e)}")

        return results

    async def reload_rules(self) -> Dict[str, Any]:
        """Reload all rules (useful for development/testing)."""
        logger.info("Reloading all CSPM rules...")
        return await self.load_all_rules()

    async def get_loaded_rules(self) -> List[Dict[str, Any]]:
        """Get list of currently loaded rules from OPA."""
        # This would query OPA for loaded policies
        # For now, return empty list as OPA doesn't have a direct API for this
        return []

    async def validate_rule(self, rego_content: str) -> Dict[str, Any]:
        """Validate a Rego rule without loading it permanently."""
        try:
            # Create a temporary policy name for validation
            temp_policy_name = "temp.validation.rule"
            
            # Try to load the rule temporarily
            success = await self.opa_service.load_policy(
                policy_name=temp_policy_name,
                rego_code=rego_content
            )

            if success:
                # Clean up the temporary policy
                await self.opa_service.delete_policy(temp_policy_name)
                return {"valid": True, "error": None}
            else:
                return {"valid": False, "error": "Failed to compile Rego rule"}

        except Exception as e:
            return {"valid": False, "error": str(e)}