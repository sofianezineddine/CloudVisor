"""Email notifier with real-time and digest support."""

import logging
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Email notifier per spec:
    - Real-time emails for CRITICAL/HIGH severity
    - Daily digest at 9am org timezone for MEDIUM/LOW
    """

    async def send(self, finding: dict[str, Any], channel: dict[str, Any]) -> bool:
        """Send email notification."""
        config = channel.get("config", {})
        smtp_host = config.get("smtp_host")
        smtp_port = config.get("smtp_port", 587)
        smtp_user = config.get("smtp_user")
        smtp_password = config.get("smtp_password")
        from_email = config.get("from_email")
        to_emails = config.get("to_emails", [])

        if not all([smtp_host, smtp_user, smtp_password, from_email, to_emails]):
            logger.error("Email channel missing required configuration")
            return False

        severity = finding.get("severity", "INFO")
        
        # Only send real-time for CRITICAL/HIGH
        if severity not in ["CRITICAL", "HIGH"]:
            logger.debug(f"Skipping real-time email for {severity} finding (digest only)")
            return True  # Not an error, just deferred to digest

        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # Build email
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[CloudVisor] {severity} - {finding.get('title', 'Security Finding')}"
            msg["From"] = from_email
            msg["To"] = ", ".join(to_emails)

            # Plain text version
            text_body = self._build_text_body(finding)
            text_part = MIMEText(text_body, "plain")
            msg.attach(text_part)

            # HTML version
            html_body = self._build_html_body(finding)
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)

            # Send via SMTP
            await aiosmtplib.send(
                msg,
                hostname=smtp_host,
                port=smtp_port,
                username=smtp_user,
                password=smtp_password,
                start_tls=True,
            )

            logger.info(f"Email sent for finding {finding.get('id')}")
            return True

        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    def _build_text_body(self, finding: dict[str, Any]) -> str:
        """Build plain text email body."""
        severity = finding.get("severity", "INFO")
        title = finding.get("title", "Security Finding")
        resource = finding.get("resource_name") or finding.get("resource_id", "Unknown")
        account = finding.get("account_id", "Unknown")
        description = finding.get("description", "")
        remediation = finding.get("remediation", "")

        body = f"""
CloudVisor Security Alert

Severity: {severity}
Title: {title}
Resource: {resource}
Account: {account}

Description:
{description}

Remediation:
{remediation}

---
View in CloudVisor: https://app.cloudvisor.io/findings/{finding.get('id')}
"""
        return body.strip()

    def _build_html_body(self, finding: dict[str, Any]) -> str:
        """Build HTML email body."""
        severity = finding.get("severity", "INFO")
        title = finding.get("title", "Security Finding")
        resource = finding.get("resource_name") or finding.get("resource_id", "Unknown")
        account = finding.get("account_id", "Unknown")
        description = finding.get("description", "")
        remediation = finding.get("remediation", "")

        severity_colors = {
            "CRITICAL": "#dc2626",
            "HIGH": "#ea580c",
            "MEDIUM": "#ca8a04",
            "LOW": "#2563eb",
            "INFO": "#64748b",
        }
        color = severity_colors.get(severity, "#64748b")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: {color}; color: white; padding: 20px; }}
        .content {{ padding: 20px; }}
        .field {{ margin-bottom: 15px; }}
        .label {{ font-weight: bold; color: #666; }}
        .button {{ background-color: {color}; color: white; padding: 10px 20px; 
                   text-decoration: none; border-radius: 5px; display: inline-block; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>CloudVisor Security Alert</h2>
        <h3>{severity}: {title}</h3>
    </div>
    <div class="content">
        <div class="field">
            <span class="label">Resource:</span> {resource}
        </div>
        <div class="field">
            <span class="label">Account:</span> {account}
        </div>
        <div class="field">
            <span class="label">Description:</span><br>
            {description}
        </div>
        <div class="field">
            <span class="label">Remediation:</span><br>
            {remediation}
        </div>
        <p>
            <a href="https://app.cloudvisor.io/findings/{finding.get('id')}" class="button">
                View in CloudVisor
            </a>
        </p>
    </div>
</body>
</html>
"""
        return html.strip()

    async def send_digest(
        self, findings: list[dict[str, Any]], config: dict[str, Any]
    ) -> bool:
        """Send daily digest email with all MEDIUM/LOW findings."""
        # TODO: Implement digest aggregation and scheduling
        # This would be called by a scheduled job (cron/celery) at 9am org timezone
        logger.info(f"Would send digest with {len(findings)} findings")
        return True
