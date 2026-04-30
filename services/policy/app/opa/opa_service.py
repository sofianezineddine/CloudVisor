"""OPA/Rego integration for policy evaluation."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OPAService:
    """Open Policy Agent integration service."""

    def __init__(self, opa_url: str = "http://localhost:8181"):
        self._opa_url = opa_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def check_health(self) -> bool:
        """Check if OPA is healthy."""
        try:
            response = await self._client.get(f"{self._opa_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"OPA health check failed: {e}")
            return False

    async def load_policy(
        self,
        policy_name: str,
        rego_code: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Load a policy into OPA using PUT /v1/policies/{id}."""
        try:
            # OPA policy ID uses slashes: cloudvisor/cspm/aws_s3_public_access
            policy_id = policy_name.replace(".", "/")
            response = await self._client.put(
                f"{self._opa_url}/v1/policies/{policy_id}",
                content=rego_code.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
            if response.status_code in (200, 201):
                logger.debug(f"Loaded policy: {policy_name}")
                return True
            logger.debug(f"OPA policy load {policy_name}: {response.status_code} {response.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"Error loading policy {policy_name}: {e}")
            return False

    async def delete_policy(self, policy_name: str) -> bool:
        """Delete a policy from OPA."""
        try:
            policy_id = policy_name.replace(".", "/")
            response = await self._client.delete(f"{self._opa_url}/v1/policies/{policy_id}")
            return response.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Error deleting policy {policy_name}: {e}")
            return False

    async def evaluate(
        self,
        input_data: dict[str, Any],
        policy_path: str = "cloudvisor",
    ) -> list[dict[str, Any]]:
        """
        Evaluate input against a specific OPA policy path.

        policy_path uses slashes: cloudvisor/cspm/aws_s3_public_access
        OPA data API: POST /v1/data/{policy_path}
        """
        try:
            # Normalize path: replace dots with slashes for OPA data API
            opa_path = policy_path.replace(".", "/")
            data = {"input": input_data}

            response = await self._client.post(
                f"{self._opa_url}/v1/data/{opa_path}",
                json=data,
            )

            if response.status_code != 200:
                logger.debug(f"OPA evaluation {policy_path}: {response.status_code}")
                return []

            result = response.json()
            return self._parse_results(result)

        except Exception as e:
            logger.debug(f"OPA evaluate {policy_path}: {e}")
            return []

    def _parse_results(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse OPA result into findings.

        OPA represents Rego sets as dicts with true values:
          deny[msg] → {"deny": {"message text": true}}
        Or as lists:
          deny[msg] → {"deny": ["message text"]}
        """
        findings = []
        result_data = result.get("result", {})

        if not isinstance(result_data, dict):
            return findings

        for rule_key in ("deny", "warn", "violation", "findings"):
            rule_value = result_data.get(rule_key)
            if not rule_value:
                continue

            if isinstance(rule_value, dict):
                # OPA set: {"message text": true, ...}
                for msg, val in rule_value.items():
                    if val is True and isinstance(msg, str) and msg:
                        findings.append({"message": msg})
            elif isinstance(rule_value, list):
                for item in rule_value:
                    if isinstance(item, str) and item:
                        findings.append({"message": item})
                    elif isinstance(item, dict):
                        findings.append(item)

        return findings

    async def evaluate_batch(
        self,
        resources: list[dict[str, Any]],
        policy_path: str,
    ) -> list[list[dict[str, Any]]]:
        """Evaluate multiple resources against a policy in parallel."""
        tasks = [
            self.evaluate({"resource": r}, policy_path)
            for r in resources
        ]
        return await asyncio.gather(*tasks)

    async def validate_rego(self, rego_code: str) -> dict[str, Any]:
        """Validate Rego code syntax by trying to load it as a temp policy."""
        import uuid
        temp_id = f"temp/validation/{uuid.uuid4().hex[:8]}"
        try:
            # Try loading the policy — if OPA accepts it, it's valid
            response = await self._client.put(
                f"{self._opa_url}/v1/policies/{temp_id}",
                content=rego_code.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
            if response.status_code in (200, 201):
                # Clean up temp policy
                await self._client.delete(f"{self._opa_url}/v1/policies/{temp_id}")
                return {"valid": True}
            # Parse OPA error
            try:
                err = response.json()
                msg = err.get("message") or err.get("errors", [{}])[0].get("message", response.text[:300])
            except Exception:
                msg = response.text[:300]
            return {"valid": False, "error": msg}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def get_policies(self) -> list[dict[str, Any]]:
        """Get list of loaded policies from OPA."""
        try:
            response = await self._client.get(f"{self._opa_url}/v1/policies")
            if response.status_code == 200:
                return response.json().get("result", [])
            return []
        except Exception:
            return []


class RegoParser:
    """Parse and extract metadata from Rego code comments."""

    METADATA_PATTERNS = [
        "title:",
        "description:",
        "severity:",
        "category:",
        "provider:",
        "resource_type:",
        "remediation:",
        "version:",
        "tags:",
    ]

    @staticmethod
    def extract_metadata(rego_code: str) -> dict[str, Any]:
        """Extract metadata from Rego # METADATA comment block."""
        metadata: dict[str, Any] = {}
        lines = rego_code.split("\n")
        in_metadata = False

        for line in lines:
            stripped = line.strip()
            if stripped == "# METADATA":
                in_metadata = True
                continue
            if in_metadata:
                if stripped.startswith("# "):
                    content = stripped[2:].strip()
                    for pattern in RegoParser.METADATA_PATTERNS:
                        if content.startswith(pattern):
                            key = pattern.rstrip(":").replace("-", "_")
                            value = content[len(pattern):].strip().strip('"').strip("'")
                            metadata[key] = value
                            break
                elif stripped and not stripped.startswith("#"):
                    in_metadata = False

        return metadata

    @staticmethod
    def extract_package(rego_code: str) -> str:
        """Extract package name from rego code."""
        for line in rego_code.split("\n"):
            stripped = line.strip()
            if stripped.startswith("package "):
                return stripped.replace("package ", "").strip()
        return "unknown"

    @staticmethod
    def extract_rule_id(policy_path: str, rego_code: str) -> str:
        """Extract rule ID from policy path."""
        return policy_path.split(".")[-1].split("/")[-1]


class PolicyLoader:
    """Load and manage policies from file system with hot-reload support."""

    def __init__(self, opa_service: OPAService, rules_path: str = "./rules/rego"):
        self._opa = opa_service
        self._rules_path = rules_path
        # Track loaded file mtimes for hot-reload: {policy_name: mtime}
        self._loaded_mtimes: dict[str, float] = {}

    async def load_all_rules(self) -> int:
        """Load all .rego files from the rules directory recursively."""
        rules_path = Path(self._rules_path)
        if not rules_path.exists():
            logger.warning(f"Rules path does not exist: {self._rules_path}")
            return 0

        loaded = 0
        for rego_file in rules_path.rglob("*.rego"):
            try:
                content = rego_file.read_text(encoding="utf-8")
                rel = rego_file.relative_to(rules_path)
                # Convert path to OPA policy name: cspm/aws/s3.rego → cloudvisor/cspm/aws/s3
                parts = list(rel.parts)
                parts[-1] = parts[-1].removesuffix(".rego")
                policy_name = "cloudvisor/" + "/".join(parts)

                if await self._opa.load_policy(policy_name, content):
                    self._loaded_mtimes[policy_name] = rego_file.stat().st_mtime
                    loaded += 1
                else:
                    logger.warning(f"Failed to load rule: {rego_file}")
            except Exception as e:
                logger.error(f"Error loading rule {rego_file}: {e}")

        logger.info(f"Loaded {loaded} Rego rules from {self._rules_path}")
        return loaded

    async def start_polling(self) -> None:
        """Start the hot-reload polling loop (runs every 60 seconds)."""
        logger.info("Starting Rego hot-reload polling (60s interval)")
        while True:
            await asyncio.sleep(60)
            try:
                await self._check_and_reload()
            except Exception as e:
                logger.error(f"Hot-reload check failed: {e}")

    async def _check_and_reload(self) -> None:
        """Compare file mtimes and reload changed files."""
        rules_path = Path(self._rules_path)
        if not rules_path.exists():
            return

        current_files: dict[str, float] = {}
        for rego_file in rules_path.rglob("*.rego"):
            rel = rego_file.relative_to(rules_path)
            parts = list(rel.parts)
            parts[-1] = parts[-1].removesuffix(".rego")
            policy_name = "cloudvisor/" + "/".join(parts)
            current_files[policy_name] = rego_file.stat().st_mtime

        # Reload new or modified files
        for policy_name, mtime in current_files.items():
            if self._loaded_mtimes.get(policy_name) != mtime:
                # Reconstruct file path from policy name
                rel_path = policy_name.removeprefix("cloudvisor/") + ".rego"
                rego_file = rules_path / rel_path
                try:
                    content = rego_file.read_text(encoding="utf-8")
                    if await self._opa.load_policy(policy_name, content):
                        self._loaded_mtimes[policy_name] = mtime
                        logger.info(f"Hot-reloaded rule: {policy_name}")
                except Exception as e:
                    logger.error(f"Error hot-reloading {policy_name}: {e}")

        # Remove deleted files from OPA
        deleted = set(self._loaded_mtimes.keys()) - set(current_files.keys())
        for policy_name in deleted:
            await self._opa.delete_policy(policy_name)
            del self._loaded_mtimes[policy_name]
            logger.info(f"Removed deleted rule: {policy_name}")

    async def reload_rules(self) -> bool:
        """Hot-reload all rules."""
        logger.info("Reloading all rules...")
        self._loaded_mtimes.clear()
        return await self.load_all_rules() > 0
