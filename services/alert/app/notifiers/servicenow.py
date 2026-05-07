"""ServiceNow notifier — creates incidents or change requests per spec §3.5."""

import logging
from typing import Any

import httpx

from .base import BaseNotifier

logger = logging.getLogger(__name__)

# Severity → ServiceNow priority mapping
PRIORITY_MAP = {
    "CRITICAL": "1",  # Critical
    "HIGH": "2",      # High
    "MEDIUM": "3",    # Moderate
    "LOW": "4",       # Low
    "INFO": "5",      # Planning
}


class ServiceNowNotifier(BaseNotifier):
    """
    ServiceNow notifier per spec §3.5:
    - Creates an incident or change request
    - Maps CloudVisor severity to ServiceNow priority
    """

    async def send(self, finding: dict[str, Any], channel: dict[str, Any]) -> bool:
        """Create a ServiceNow incident for the finding."""
        config = channel.get("config", {})
        instance_url = config.get("instance_url")  # e.g. https://company.service-now.com
        username = config.get("username")
        password = config.get("password")
        table = config.get("table", "incident")  # "incident" or "change_request"

        if not all([instance_url, username, password]):
            logger.error("ServiceNow channel missing required configuration (instance_url, username, password)")
            return False

        severity = finding.get("severity", "MEDIUM")
        priority = PRIORITY_MAP.get(severity, "3")

        payload = {
            "short_description": finding.get("title", "Security Finding"),
            "description": self._build_description(finding),
            "priority": priority,
            "category": "Security",
            "subcategory": "Cloud Security",
            "caller_id": "CloudVisor",
            "u_cloudvisor_finding_id": finding.get("id"),
            "u_cloudvisor_resource": finding.get("resource_name") or finding.get("resource_id"),
            "u_cloudvisor_account": finding.get("account_id"),
            "u_cloudvisor_provider": finding.get("provider"),
            "u_cloudvisor_severity": severity,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{instance_url}/api/now/table/{table}",
                    json=payload,
                    auth=(username, password),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )

                if response.status_code in [200, 201]:
                    result = response.json()
                    sys_id = result.get("result", {}).get("sys_id")
                    number = result.get("result", {}).get("number")
                    logger.info(
                        f"ServiceNow {table} created: {number} (sys_id={sys_id}) "
                        f"for finding {finding.get('id')}"
                    )
                    return True
                else:
                    logger.warning(
                        f"ServiceNow returned {response.status_code}: {response.text[:200]}"
                    )
                    return False

        except Exception as e:
            logger.error(f"ServiceNow notification failed: {e}")
            return False

    def _build_description(self, finding: dict[str, Any]) -> str:
        resource = finding.get("resource_name") or finding.get("resource_id", "Unknown")
        account = finding.get("account_id", "Unknown")
        region = finding.get("region", "Unknown")
        description = finding.get("description", "")
        remediation = finding.get("remediation", "")

        return (
            f"CloudVisor Security Finding\n\n"
            f"Severity: {finding.get('severity', 'UNKNOWN')}\n"
            f"Resource: {resource}\n"
            f"Account: {account}\n"
            f"Region: {region}\n"
            f"Provider: {finding.get('provider', 'Unknown')}\n\n"
            f"Description:\n{description}\n\n"
            f"Remediation:\n{remediation}\n\n"
            f"View in CloudVisor: https://app.cloudvisor.io/findings/{finding.get('id')}"
        )
