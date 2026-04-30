import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ResourceEventConsumer:
    def __init__(self, bootstrap_servers: str, policy_service_url: str, finding_producer=None):
        self._bootstrap_servers = bootstrap_servers
        self._policy_service_url = policy_service_url
        self._producer = finding_producer
        self._consumer = None
        # Track open fingerprints per resource: {resource_id: set[fingerprint]}
        self._open_fingerprints: dict[str, set[str]] = {}

    async def start(self) -> None:
        try:
            from aiokafka import AIOKafkaConsumer

            self._consumer = AIOKafkaConsumer(
                "resource.discovered",
                "resource.updated",
                bootstrap_servers=self._bootstrap_servers,
                group_id="cspm-scanner",
                auto_offset_reset="earliest",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            )
            await self._consumer.start()
            logger.info("CSPM resource event consumer started")
        except Exception as e:
            logger.warning(f"Kafka consumer failed to start: {e}")
            self._consumer = None

    async def run(self) -> None:
        if not self._consumer:
            logger.warning("No Kafka consumer — CSPM scanner running in degraded mode")
            return

        from ..services.scanner import evaluate_resource, compute_fingerprint
        from ..producers.finding_producer import FindingProducer

        producer = FindingProducer(self._producer)

        async for msg in self._consumer:
            try:
                resource = msg.value
                org_id = resource.get("organization_id", "")
                resource_id = resource.get("cloud_resource_id", resource.get("id", ""))
                account_id = resource.get("account_id", "")

                findings = await evaluate_resource(resource, org_id, self._policy_service_url)
                current_fingerprints = set()

                for finding in findings:
                    fp = compute_fingerprint(finding.rule_id, resource_id, account_id, org_id)
                    current_fingerprints.add(fp)
                    event = {
                        "rule_id": finding.rule_id,
                        "resource_id": resource_id,
                        "resource_type": resource.get("resource_type", ""),
                        "resource_name": resource.get("name", ""),
                        "account_id": account_id,
                        "org_id": org_id,
                        "severity": finding.severity,
                        "title": finding.title,
                        "description": finding.description,
                        "remediation": finding.remediation,
                        "compliance_mapping": finding.compliance_mapping,
                        "fingerprint": fp,
                        "provider": resource.get("provider", ""),
                        "region": resource.get("region", ""),
                    }
                    await producer.publish_finding_raw(event)

                # Resolve findings that no longer fire
                prev_fps = self._open_fingerprints.get(resource_id, set())
                for resolved_fp in prev_fps - current_fingerprints:
                    await producer.publish_finding_resolved(resolved_fp, org_id)

                self._open_fingerprints[resource_id] = current_fingerprints

            except Exception as e:
                logger.error(f"Error processing resource event: {e}")

    async def stop(self) -> None:
        if self._consumer:
            await self._consumer.stop()
