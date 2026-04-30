import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


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
