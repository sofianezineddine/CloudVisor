"""PagerDuty notifier for CRITICAL severity findings."""

import logging
from typing import Any

import httpx

from .base import BaseNotifier

logger = logging.getLogger(__name__)


class PagerDutyNotifier(BaseNotifier):
    """
    PagerDuty notifier per spec:
    - CRITICAL severity triggers on-call escalation
    - Auto-resolves when finding is resolved
    """

    async def send(self, finding: dict[str, Any], channel: dict[str, Any]) -> bool:
        """Trigger PagerDuty incident for CRITICAL findings."""
        config = channel.get("config", {})
        integration_key = config.get("integration_key")

        if not integration_key:
            logger.error("PagerDuty channel missing integration_key")
            return False

        severity = finding.get("severity", "INFO")
        
        # Only trigger for CRITICAL per spec
        if severity != "CRITICAL":
            logger.debug(f"Skipping PagerDuty for {severity} finding (CRITICAL only)")
            return True

        try:
            # Build PagerDuty event
            event = {
                "routing_key": integration_key,
                "event_action": "trigger",
                "dedup_key": f"cloudvisor-{finding.get('id')}",
                "payload": {
                    "summary": finding.get("title", "Security Finding"),
                    "severity": "critical",
                    "source": "CloudVisor",
                    "component": finding.get("resource_name") or finding.get("resource_id"),
                    "group": finding.get("account_id"),
                    "class": finding.get("provider"),
                    "custom_details": {
                        "finding_id": finding.get("id"),
                        "resource": finding.get("resource_id"),
                        "account": finding.get("account_id"),
                        "region": finding.get("region"),
                        "rule_id": finding.get("rule_id"),
                        "description": finding.get("description", ""),
                        "remediation": finding.get("remediation", ""),
                        "link": f"https://app.cloudvisor.io/findings/{finding.get('id')}",
                    },
                },
                "links": [
                    {
                        "href": f"https://app.cloudvisor.io/findings/{finding.get('id')}",
                        "text": "View in CloudVisor",
                    }
                ],
            }

            # Send to PagerDuty Events API v2
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=event,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 202:
                    logger.info(f"PagerDuty incident triggered for finding {finding.get('id')}")
                    return True
                else:
                    logger.warning(
                        f"PagerDuty returned {response.status_code}: {response.text[:200]}"
                    )
                    return False

        except Exception as e:
            logger.error(f"PagerDuty trigger failed: {e}")
            return False

    async def resolve(self, finding_id: str, integration_key: str) -> bool:
        """Resolve PagerDuty incident when finding is resolved."""
        try:
            event = {
                "routing_key": integration_key,
                "event_action": "resolve",
                "dedup_key": f"cloudvisor-{finding_id}",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=event,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 202:
                    logger.info(f"PagerDuty incident resolved for finding {finding_id}")
                    return True
                else:
                    logger.warning(f"PagerDuty resolve failed: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"PagerDuty resolve failed: {e}")
            return False
