"""
Policy Kafka consumer — evaluates all applicable rules against every
resource.discovered and resource.updated event, then publishes finding.raw
events to the Alert service.

This is the core of the CSPM engine: cloud resource → OPA evaluation → findings.
"""

import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)


class ResourceEventConsumer:
    """
    Consumes resource.discovered and resource.updated events.
    For each resource, evaluates all enabled rules via OPA and
    publishes finding.raw events for any violations found.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str = "cloudvisor-policy",
        session_factory: Any = None,
        opa_service: Any = None,
        kafka_producer: Any = None,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._session_factory = session_factory
        self._opa = opa_service
        self._producer = kafka_producer
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            "resource.discovered",
            "resource.updated",
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        logger.info("Policy resource event consumer started")

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
        logger.info("Policy resource event consumer stopped")

    async def run(self) -> None:
        if not self._consumer:
            return
        try:
            async for message in self._consumer:
                if not self._running:
                    break
                try:
                    await self._process_message(message)
                except Exception as e:
                    logger.error(f"Error processing resource event: {e}")
        except Exception as e:
            logger.error(f"Policy consumer error: {e}")

    async def _process_message(self, message: Any) -> None:
        """Evaluate a resource against all applicable rules."""
        event = message.value
        event_type = event.get("event_type", "")

        if event_type not in ("resource.discovered", "resource.updated"):
            return

        resource = self._event_to_resource(event)
        if not resource:
            return

        organization_id = resource.get("organization_id", "")
        if not organization_id:
            return

        # Get enabled rules for this org from DB
        rules = await self._get_enabled_rules(organization_id, resource.get("resource_type", ""))
        if not rules:
            return

        # Evaluate each rule against the resource
        violations = 0
        for rule in rules:
            try:
                findings = await self._evaluate_rule(rule, resource)
                for finding in findings:
                    await self._emit_finding(finding, resource, organization_id)
                    violations += 1
            except Exception as e:
                logger.debug(f"Rule {rule.get('rule_id')} evaluation error: {e}")

        if violations > 0:
            logger.info(
                f"Resource {resource.get('name')} ({resource.get('resource_type')}): "
                f"{violations} violations found"
            )

    def _event_to_resource(self, event: dict) -> dict | None:
        """Convert a Kafka event to a resource dict for OPA evaluation."""
        cloud_resource_id = event.get("cloud_resource_id", "")
        if not cloud_resource_id:
            return None

        return {
            "id": cloud_resource_id,
            "cloud_resource_id": cloud_resource_id,
            "provider": event.get("provider", ""),
            "account_id": event.get("account_id", ""),
            "organization_id": event.get("organization_id", ""),
            "region": event.get("region", "global"),
            "resource_type": event.get("resource_type", ""),
            "name": event.get("name", ""),
            "tags": event.get("tags", {}),
            "is_public": event.get("is_public", False),
            "environment": event.get("environment", "unknown"),
            "raw": event.get("raw", {}),
        }

    async def _get_enabled_rules(self, organization_id: str, resource_type: str) -> list[dict]:
        """Get enabled rules applicable to this resource type."""
        if not self._session_factory:
            return []

        from sqlalchemy import select
        from app.models import RuleModel, RuleDisableModel
        from app.core.database import create_db_session

        try:
            async with create_db_session(self._session_factory) as session:
                # Get all enabled built-in rules
                stmt = select(RuleModel).where(
                    RuleModel.is_enabled == True,
                    RuleModel.is_builtin == True,
                )
                result = await session.execute(stmt)
                all_rules = result.scalars().all()

                # Get disabled rules for this org
                disabled_stmt = select(RuleDisableModel.rule_id).where(
                    RuleDisableModel.organization_id == organization_id
                )
                disabled_result = await session.execute(disabled_stmt)
                disabled_ids = {row[0] for row in disabled_result}

                # Filter: applicable to this resource type + not disabled for this org
                applicable = []
                for rule in all_rules:
                    if rule.rule_id in disabled_ids:
                        continue
                    # Check if rule applies to this resource type
                    # Match on suffix: "aws::ec2::securitygroup" matches "aws::securitygroup"
                    if rule.resource_type and resource_type:
                        rule_suffix = rule.resource_type.split("::")[-1].lower()
                        resource_suffix = resource_type.split("::")[-1].lower()
                        if (rule_suffix != resource_suffix and
                                rule.resource_type not in resource_type and
                                resource_type not in rule.resource_type):
                            continue
                    applicable.append({
                        "rule_id": rule.rule_id,
                        "title": rule.title,
                        "severity": rule.severity,
                        "category": rule.category,
                        "provider": rule.provider,
                        "resource_type": rule.resource_type,
                        "remediation": rule.remediation,
                        "compliance_mapping": rule.compliance_mapping or [],
                        "rego_code": rule.rego_code,
                    })

                return applicable
        except Exception as e:
            logger.error(f"Failed to get rules: {e}")
            return []

    async def _evaluate_rule(self, rule: dict, resource: dict) -> list[dict]:
        """Evaluate a single rule against a resource via OPA.
        
        Returns a list of finding dicts, each with rule metadata merged in.
        """
        if not self._opa:
            return []

        input_data = {"resource": resource}
        # OPA path: cloudvisor.cspm.aws_s3_public_access → cloudvisor/cspm/aws_s3_public_access
        rule_id_normalized = rule['rule_id'].replace('-', '_')
        policy_path = f"cloudvisor/{rule['category']}/{rule_id_normalized}"

        try:
            results = await self._opa.evaluate(input_data, policy_path)
            # Enrich each raw OPA result with rule metadata
            enriched = []
            for r in results:
                enriched.append({
                    "rule_id": rule["rule_id"],
                    "title": rule["title"],
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "provider": rule.get("provider"),
                    "resource_type": rule.get("resource_type"),
                    "remediation": rule.get("remediation"),
                    "compliance_mapping": rule.get("compliance_mapping", []),
                    "description": r.get("message", rule["title"]),
                })
            return enriched
        except Exception as e:
            logger.debug(f"OPA evaluation for {rule['rule_id']}: {e}")
            return []

    async def _emit_finding(
        self, finding: dict, resource: dict, organization_id: str
    ) -> None:
        """Publish a finding.raw event to Kafka for the Alert service."""
        if not self._producer:
            return

        event = {
            "event_type": "finding.raw",
            "organization_id": organization_id,
            "rule_id": finding.get("rule_id", ""),
            "resource_id": resource.get("cloud_resource_id", ""),
            "resource_name": resource.get("name", ""),
            "severity": finding.get("severity", "MEDIUM"),
            "title": finding.get("title", ""),
            "description": finding.get("description", finding.get("message", "")),
            "remediation": finding.get("remediation", ""),
            "provider": resource.get("provider", ""),
            "account_id": resource.get("account_id", ""),
            "region": resource.get("region", ""),
            "resource_type": resource.get("resource_type", ""),
            "tags": resource.get("tags", {}),
            "compliance_mapping": finding.get("compliance_mapping", []),
            "context": {"resource": resource},
        }

        try:
            await self._producer.send_and_wait(
                "finding.raw",
                key=resource.get("cloud_resource_id", "").encode("utf-8"),
                value=json.dumps(event, default=str).encode("utf-8"),
            )
            logger.debug(f"Emitted finding.raw: {finding.get('rule_id')} on {resource.get('name')}")
        except Exception as e:
            logger.error(f"Failed to emit finding.raw: {e}")
