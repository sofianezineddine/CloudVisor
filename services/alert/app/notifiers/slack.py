import logging
from typing import Any

import httpx

from .base import BaseNotifier

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    "CRITICAL": "🔴",
    "HIGH": "🟠",
    "MEDIUM": "🟡",
    "LOW": "🔵",
    "INFO": "⚪",
}


class SlackNotifier(BaseNotifier):
    async def send(self, finding: dict[str, Any], channel: dict[str, Any]) -> bool:
        webhook_url = channel.get("config", {}).get("webhook_url")
        if not webhook_url:
            logger.error("Slack channel missing webhook_url")
            return False

        severity = finding.get("severity", "INFO")
        emoji = SEVERITY_EMOJI.get(severity, "⚪")
        title = finding.get("title", "Security Finding")
        resource = finding.get("resource_name") or finding.get("resource_id", "Unknown")
        account = finding.get("account_id", "Unknown")

        payload = {
            "text": f"{emoji} *{severity}* — {title}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{severity}* — {title}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Resource:*\n{resource}"},
                        {"type": "mrkdwn", "text": f"*Account:*\n{account}"},
                    ],
                },
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                if response.status_code == 200:
                    return True
                logger.warning(
                    f"Slack returned {response.status_code}: {response.text[:100]}"
                )
                return False
        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            return False
