"""Jira notifier with bi-directional sync."""

import logging
from typing import Any

import httpx

from .base import BaseNotifier

logger = logging.getLogger(__name__)


class JiraNotifier(BaseNotifier):
    """
    Jira notifier per spec:
    - Auto-create issues with finding details
    - Map severity to Jira priority
    - Bi-directional status sync (TODO: webhook handler)
    """

    async def send(self, finding: dict[str, Any], channel: dict[str, Any]) -> bool:
        """Create Jira issue for finding."""
        config = channel.get("config", {})
        jira_url = config.get("url")  # e.g., https://company.atlassian.net
        email = config.get("email")
        api_token = config.get("api_token")
        project_key = config.get("project_key")
        issue_type = config.get("issue_type", "Bug")

        if not all([jira_url, email, api_token, project_key]):
            logger.error("Jira channel missing required configuration")
            return False

        try:
            # Map severity to Jira priority
            priority_map = {
                "CRITICAL": "Highest",
                "HIGH": "High",
                "MEDIUM": "Medium",
                "LOW": "Low",
                "INFO": "Lowest",
            }
            priority = priority_map.get(finding.get("severity", "MEDIUM"), "Medium")

            # Build issue payload
            issue_data = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": finding.get("title", "Security Finding"),
                    "description": self._build_description(finding),
                    "issuetype": {"name": issue_type},
                    "priority": {"name": priority},
                    "labels": [
                        "cloudvisor",
                        f"severity-{finding.get('severity', 'medium').lower()}",
                        f"provider-{finding.get('provider', 'unknown').lower()}",
                    ],
                }
            }

            # Create issue
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{jira_url}/rest/api/3/issue",
                    json=issue_data,
                    auth=(email, api_token),
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code in [200, 201]:
                    issue_key = response.json().get("key")
                    logger.info(f"Created Jira issue {issue_key} for finding {finding.get('id')}")
                    
                    # Store Jira issue key in finding context for bi-directional sync
                    # TODO: Update finding context with jira_issue_key
                    
                    return True
                else:
                    logger.warning(
                        f"Jira returned {response.status_code}: {response.text[:200]}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Jira issue creation failed: {e}")
            return False

    def _build_description(self, finding: dict[str, Any]) -> str:
        """Build Jira issue description in Jira markdown format."""
        resource = finding.get("resource_name") or finding.get("resource_id", "Unknown")
        account = finding.get("account_id", "Unknown")
        region = finding.get("region", "Unknown")
        description = finding.get("description", "")
        remediation = finding.get("remediation", "")

        jira_desc = f"""
h2. Security Finding Details

*Resource:* {resource}
*Account:* {account}
*Region:* {region}
*Provider:* {finding.get('provider', 'Unknown')}

h3. Description
{description}

h3. Remediation Steps
{remediation}

h3. Compliance Impact
"""
        
        # Add compliance mappings
        compliance = finding.get("compliance_mapping", [])
        if compliance:
            for mapping in compliance:
                framework = mapping.get("framework", "")
                control = mapping.get("control", "")
                jira_desc += f"\n* {framework}: {control}"
        else:
            jira_desc += "\nNo compliance mappings"

        jira_desc += f"""

---
[View in CloudVisor|https://app.cloudvisor.io/findings/{finding.get('id')}]

_This issue was automatically created by CloudVisor._
"""
        return jira_desc.strip()

    async def sync_status(self, jira_issue_key: str, jira_status: str) -> dict[str, Any]:
        """
        Sync Jira issue status back to CloudVisor finding.
        Called by webhook handler when Jira issue status changes.
        """
        # Map Jira status to CloudVisor status
        status_map = {
            "To Do": "open",
            "In Progress": "in_progress",
            "Done": "resolved",
            "Closed": "resolved",
            "Won't Do": "accepted_risk",
        }
        
        cloudvisor_status = status_map.get(jira_status, "open")
        
        return {
            "jira_issue_key": jira_issue_key,
            "jira_status": jira_status,
            "cloudvisor_status": cloudvisor_status,
        }
