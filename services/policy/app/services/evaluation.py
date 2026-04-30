"""Policy evaluation service."""

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import RuleModel, RuleDisableModel
from ..opa import OPAService, RegoParser

logger = logging.getLogger(__name__)


class PolicyEvaluationService:
    """Service for evaluating rules against resources."""

    def __init__(
        self,
        db: AsyncSession,
        opa_service: OPAService,
        redis_client: Any = None,
    ):
        self._db = db
        self._opa = opa_service
        self._redis = redis_client
        self._parser = RegoParser()

    async def evaluate_resources(
        self,
        resources: list[dict[str, Any]],
        organization_id: str,
        category: str | None = None,
        rule_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Evaluate one or many resources against rules."""
        enabled_rules = await self._get_enabled_rules(organization_id, category, rule_ids)
        findings = []
        for resource in resources:
            resource_findings = await self._evaluate_single_resource(resource, enabled_rules)
            findings.extend(resource_findings)
        return findings

    async def evaluate_single(
        self,
        resource: dict[str, Any],
        organization_id: str,
    ) -> list[dict[str, Any]]:
        """Evaluate a single resource."""
        return await self._evaluate_single_resource(
            resource,
            await self._get_enabled_rules(organization_id),
        )

    async def _evaluate_single_resource(
        self,
        resource: dict[str, Any],
        rules: list[RuleModel],
    ) -> list[dict[str, Any]]:
        """Evaluate a single resource against enabled rules."""
        findings = []

        for rule in rules:
            if not self._is_rule_applicable(rule, resource):
                continue

            cache_key = f"eval:{rule.rule_id}:{resource.get('cloud_resource_id', resource.get('id', ''))}"

            # Check Redis cache — use json.loads, NOT eval()
            if self._redis:
                cached = await self._redis.get(cache_key)
                if cached:
                    try:
                        cached_findings = json.loads(cached)
                        findings.extend(cached_findings)
                        continue
                    except (json.JSONDecodeError, TypeError):
                        pass  # Cache miss — re-evaluate

            input_data = {
                "resource": resource,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # OPA path: cloudvisor/cspm/aws_s3_public_access
            rule_id_normalized = rule.rule_id.replace("-", "_")
            policy_path = f"cloudvisor/{rule.category}/{rule_id_normalized}"
            results = await self._opa.evaluate(input_data, policy_path)

            rule_findings = []
            for result in results:
                finding = self._create_finding(rule, resource, result)
                rule_findings.append(finding)

            findings.extend(rule_findings)

            # Cache with json.dumps — safe serialization
            if self._redis and rule_findings:
                await self._redis.setex(cache_key, 300, json.dumps(rule_findings))

        return findings

    def _is_rule_applicable(self, rule: RuleModel, resource: dict[str, Any]) -> bool:
        """Check if rule is applicable to resource type and provider."""
        if rule.resource_type:
            resource_type = resource.get("resource_type", "")
            rule_suffix = rule.resource_type.split("::")[-1].lower()
            resource_suffix = resource_type.split("::")[-1].lower()
            if (rule_suffix != resource_suffix
                    and rule.resource_type not in resource_type
                    and resource_type not in rule.resource_type):
                return False

        if rule.provider:
            provider = resource.get("provider", "")
            if rule.provider.lower() not in provider.lower():
                return False

        return True

    def _create_finding(
        self,
        rule: RuleModel,
        resource: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a finding from rule evaluation result."""
        return {
            "rule_id": rule.rule_id,
            "title": rule.title,
            "description": result.get("message", rule.description or rule.title),
            "severity": rule.severity,
            "category": rule.category,
            "provider": rule.provider,
            "resource_type": rule.resource_type,
            "resource_id": resource.get("cloud_resource_id", resource.get("id", "")),
            "resource_name": resource.get("name", ""),
            "remediation": rule.remediation,
            "compliance_mapping": rule.compliance_mapping or [],
            "tags": rule.tags or [],
        }

    async def _get_enabled_rules(
        self,
        organization_id: str | None = None,
        category: str | None = None,
        rule_ids: list[str] | None = None,
    ) -> list[RuleModel]:
        """Get enabled rules, excluding those disabled for this org."""
        # Get disabled rule_ids for this org
        disabled_ids: set[str] = set()
        if organization_id:
            disabled_result = await self._db.execute(
                select(RuleDisableModel.rule_id).where(
                    RuleDisableModel.organization_id == organization_id
                )
            )
            disabled_ids = {row[0] for row in disabled_result}

        query = select(RuleModel).where(RuleModel.is_enabled == True)

        if category:
            query = query.where(RuleModel.category == category)
        if rule_ids:
            query = query.where(RuleModel.rule_id.in_(rule_ids))

        result = await self._db.execute(query)
        all_rules = result.scalars().all()

        # Filter out disabled rules for this org
        return [r for r in all_rules if r.rule_id not in disabled_ids]

    async def dry_run(
        self,
        rego_code: str,
        resources: list[dict[str, Any]],
        organization_id: str,
    ) -> dict[str, Any]:
        """Test a custom rule without persisting findings."""
        validation = await self._opa.validate_rego(rego_code)
        if not validation.get("valid"):
            return {"success": False, "error": validation.get("error")}

        rule_id = f"dry-run-{int(datetime.utcnow().timestamp())}"
        metadata = self._parser.extract_metadata(rego_code)
        policy_name = f"cloudvisor/custom/{organization_id}/{rule_id}"

        loaded = await self._opa.load_policy(policy_name, rego_code, metadata)
        if not loaded:
            return {"success": False, "error": "Failed to load policy into OPA"}

        findings = []
        for resource in resources:
            results = await self._opa.evaluate(
                {"resource": resource},
                f"cloudvisor/custom/{organization_id}/{rule_id}",
            )
            findings.extend(results)

        # Clean up temp policy
        await self._opa.delete_policy(policy_name)

        return {
            "success": True,
            "findings": findings,
            "metadata": metadata,
        }


class ComplianceService:
    """Service for compliance framework mapping and posture calculation."""

    # Supported frameworks with their display names
    FRAMEWORKS = {
        "CIS-AWS": "CIS AWS Foundations Benchmark v3.0",
        "CIS-Azure": "CIS Microsoft Azure Foundations Benchmark",
        "CIS-GCP": "CIS Google Cloud Platform Foundation Benchmark",
        "CIS-OCI": "CIS Oracle Cloud Infrastructure Foundations Benchmark",
        "SOC2": "SOC 2 Type II",
        "PCI-DSS": "PCI Data Security Standard v4.0",
        "HIPAA": "Health Insurance Portability and Accountability Act",
        "ISO27001": "ISO/IEC 27001:2022",
        "NIST-800-53": "NIST SP 800-53 Rev 5",
        "GDPR": "General Data Protection Regulation",
        "FedRAMP": "Federal Risk and Authorization Management Program",
        "CCPA": "California Consumer Privacy Act",
    }

    def __init__(self, db: AsyncSession, redis_client: Any = None):
        self._db = db
        self._redis = redis_client
        self._cache_ttl = 300  # 5 minutes

    async def get_compliance_posture(
        self,
        organization_id: str,
        framework: str,
    ) -> dict[str, Any]:
        """
        Calculate compliance posture for a framework.

        Posture is derived from:
        - Rules mapped to this framework's controls
        - Whether those rules are enabled (passing) or disabled (failing/not_applicable)
        """
        cache_key = f"compliance:{organization_id}:{framework}"

        # Check Redis cache — use json.loads, NOT eval()
        if self._redis:
            cached = await self._redis.get(cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except (json.JSONDecodeError, TypeError):
                    pass

        # Get all rules mapped to this framework
        rules = await self._get_framework_rules(framework)

        # Get disabled rules for this org
        disabled_result = await self._db.execute(
            select(RuleDisableModel.rule_id).where(
                RuleDisableModel.organization_id == organization_id
            )
        )
        disabled_ids = {row[0] for row in disabled_result}

        # Build control status map
        controls = []
        seen_controls: set[str] = set()
        passing = 0
        failing = 0
        not_applicable = 0

        for rule in rules:
            mapping = rule.compliance_mapping or []
            for m in mapping:
                if not isinstance(m, dict):
                    continue
                if m.get("framework", "").upper() != framework.upper():
                    continue

                control_id = m.get("control", "")
                if not control_id or control_id in seen_controls:
                    continue
                seen_controls.add(control_id)

                is_disabled = rule.rule_id in disabled_ids
                if is_disabled:
                    status = "not_applicable"
                    not_applicable += 1
                elif rule.is_enabled:
                    status = "pass"
                    passing += 1
                else:
                    status = "fail"
                    failing += 1

                controls.append({
                    "id": control_id,
                    "rule_id": rule.rule_id,
                    "title": rule.title,
                    "severity": rule.severity,
                    "status": status,
                })

        total = len(controls)
        percentage = round((passing / total * 100), 1) if total > 0 else 0.0

        # If no controls found for this framework, return 100% (no rules = no violations)
        if total == 0:
            percentage = 100.0

        result = {
            "framework": framework,
            "display_name": self.FRAMEWORKS.get(framework, framework),
            "total_controls": total,
            "passing": passing,
            "failing": failing,
            "not_applicable": not_applicable,
            "percentage": percentage,
            "controls": controls,
        }

        # Cache with json.dumps
        if self._redis:
            await self._redis.setex(cache_key, self._cache_ttl, json.dumps(result))

        return result

    async def _get_framework_rules(self, framework: str) -> list[RuleModel]:
        """Get all rules that have compliance mappings for this framework."""
        result = await self._db.execute(
            select(RuleModel).where(RuleModel.is_enabled == True)
        )
        all_rules = result.scalars().all()

        # Filter rules that have mappings for this framework
        framework_rules = []
        for rule in all_rules:
            mapping = rule.compliance_mapping or []
            for m in mapping:
                if isinstance(m, dict) and m.get("framework", "").upper() == framework.upper():
                    framework_rules.append(rule)
                    break

        return framework_rules

    async def get_all_frameworks(self, organization_id: str) -> list[dict[str, Any]]:
        """Get compliance posture for all supported frameworks."""
        results = []
        for framework in self.FRAMEWORKS:
            posture = await self.get_compliance_posture(organization_id, framework)
            results.append(posture)
        return results

    async def get_evidence(
        self,
        organization_id: str,
        framework: str,
        control_id: str,
    ) -> dict[str, Any]:
        """
        Generate compliance evidence for a specific control.
        Returns rule details, resource counts, and finding summary.
        """
        rules = await self._get_framework_rules(framework)
        control_rules = [
            r for r in rules
            if any(
                isinstance(m, dict) and m.get("control") == control_id
                for m in (r.compliance_mapping or [])
            )
        ]

        return {
            "framework": framework,
            "control_id": control_id,
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "title": r.title,
                    "severity": r.severity,
                    "is_enabled": r.is_enabled,
                }
                for r in control_rules
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }
