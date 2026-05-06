"""Microsoft Teams notifier with Adaptive Card format."""

import logging
from typing import Any

import httpx

from .base import BaseNotifier

logger = logging.getLogger(__name__)


class TeamsNotifier(BaseNotifier):
    """Microsoft Teams notifier using Adaptive Card format per spec."""

    async def send(self, finding: dict[str, Any], channel: dict[str, Any]) -> bool:
        """Send Teams notification using Adaptive Card."""
        config = channel.get("config", {})
        webhook_url = config.get("webhook_url")

        if not webhook_url:
            logger.error("Teams channel missing webhook_url")
            return False

        try:
            severity = finding.get("severity", "INFO")
            
            # Severity color mapping
            severity_colors = {
                "CRITICAL": "Attention",  # Red
                "HIGH": "Warning",  # Orange
                "MEDIUM": "Good",  # Yellow/Green
                "LOW": "Accent",  # Blue
                "INFO": "Default",  # Gray
            }
            theme_color = severity_colors.get(severity, "Default")

            # Build Adaptive Card
            card = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                            "type": "AdaptiveCard",
                            "version": "1.4",
                            "body": [
                                {
                                    "type": "Container",
                                    "style": theme_color,
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": f"🔒 CloudVisor Security Alert",
                                            "weight": "Bolder",
                                            "size": "Medium",
                                            "color": "Light",
                                        },
                                        {
                                            "type": "TextBlock",
                                            "text": f"{severity}: {finding.get('title', 'Security Finding')}",
                                            "weight": "Bolder",
                                            "size": "Large",
                                            "wrap": True,
                                            "color": "Light",
                                        },
                                    ],
                                },
                                {
                                    "type": "FactSet",
                                    "facts": [
                                        {
                                            "title": "Severity",
                                            "value": severity,
                                        },
                                        {
                                            "title": "Resource",
                                            "value": finding.get("resource_name")
                                            or finding.get("resource_id", "Unknown"),
                                        },
                                        {
                                            "title": "Account",
                                            "value": finding.get("account_id", "Unknown"),
                                        },
                                        {
                                            "title": "Region",
                                            "value": finding.get("region", "Unknown"),
                                        },
                                        {
                                            "title": "Provider",
                                            "value": finding.get("provider", "Unknown"),
                                        },
                                    ],
                                },
                                {
                                    "type": "TextBlock",
                                    "text": "**Description**",
                                    "weight": "Bolder",
                                    "spacing": "Medium",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": finding.get("description", "No description available"),
                                    "wrap": True,
                                },
                                {
                                    "type": "TextBlock",
                                    "text": "**Remediation**",
                                    "weight": "Bolder",
                                    "spacing": "Medium",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": finding.get("remediation", "No remediation steps available"),
                                    "wrap": True,
                                },
                            ],
                            "actions": [
                                {
                                    "type": "Action.OpenUrl",
                                    "title": "View in CloudVisor",
                                    "url": f"https://app.cloudvisor.io/findings/{finding.get('id')}",
                                }
                            ],
                        },
                    }
                ],
            }

            # Send to Teams webhook
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook_url,
                    json=card,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    logger.info(f"Teams notification sent for finding {finding.get('id')}")
                    return True
                else:
                    logger.warning(
                        f"Teams returned {response.status_code}: {response.text[:200]}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Teams notification failed: {e}")
            return False
