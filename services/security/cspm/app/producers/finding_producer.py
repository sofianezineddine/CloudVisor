import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_cspm_settings

logger = logging.getLogger(__name__)
settings = get_cspm_settings()


class FindingProducer:
    def __init__(self, kafka_producer=None):
        self._producer = kafka_producer

    async def publish_finding_raw(self, finding_event: dict[str, Any]) -> None:
        if not self._producer:
            logger.debug(
                f"Kafka not available, skipping finding.raw: {finding_event.get('rule_id')}"
            )
            return
        try:
            await self._producer.send_and_wait(
                "finding.raw",
                json.dumps(finding_event).encode("utf-8"),
            )
        except Exception as e:
            logger.error(f"Failed to publish finding.raw: {e}")

    async def publish_finding_resolved(self, fingerprint: str, org_id: str) -> None:
        if not self._producer:
            return
        try:
            event = {"fingerprint": fingerprint, "org_id": org_id, "status": "resolved"}
            await self._producer.send_and_wait(
                "finding.resolved",
                json.dumps(event).encode("utf-8"),
            )
        except Exception as e:
            logger.error(f"Failed to publish finding.resolved: {e}")

    async def publish_iam_analysis_complete(
        self,
        *,
        organization_id: str,
        account_id: str,
        identities_analyzed: int,
        escalation_paths_found: int,
        correlation_id: str | None = None,
    ) -> None:
        """Publish an iam.analysis_complete event after IAM analysis finishes."""
        if not self._producer:
            logger.warning(
                "Kafka producer not available, skipping iam.analysis_complete "
                f"for account {account_id}"
            )
            return

        event = {
            "organization_id": organization_id,
            "account_id": account_id,
            "identities_analyzed": identities_analyzed,
            "escalation_paths_found": escalation_paths_found,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self._producer.send_and_wait(
                settings.kafka_topic_iam_analysis_complete,
                json.dumps(event).encode("utf-8"),
            )
            logger.info(
                f"Published iam.analysis_complete for account={account_id} "
                f"identities={identities_analyzed} escalation_paths={escalation_paths_found}"
            )
        except Exception as e:
            logger.error(f"Failed to publish iam.analysis_complete: {e}")

    async def publish_policy_auto_remediate(
        self,
        *,
        organization_id: str,
        resource_id: str,
        rule_id: str,
        remediation_action: str,
        enforcement_mode: str,
        correlation_id: str | None = None,
    ) -> None:
        """Publish a policy.auto_remediate event when auto-remediation is triggered."""
        if not self._producer:
            logger.warning(
                "Kafka producer not available, skipping policy.auto_remediate "
                f"for resource {resource_id}"
            )
            return

        event = {
            "organization_id": organization_id,
            "resource_id": resource_id,
            "rule_id": rule_id,
            "remediation_action": remediation_action,
            "enforcement_mode": enforcement_mode,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self._producer.send_and_wait(
                settings.kafka_topic_policy_auto_remediate,
                json.dumps(event).encode("utf-8"),
            )
            logger.info(
                f"Published policy.auto_remediate for resource={resource_id} "
                f"rule={rule_id} action={remediation_action}"
            )
        except Exception as e:
            logger.error(f"Failed to publish policy.auto_remediate: {e}")
