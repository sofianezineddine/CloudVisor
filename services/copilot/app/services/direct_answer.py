"""
Direct Answer Engine — generates precise, data-grounded answers without LLM hallucination.

For factual queries (counts, lists, status), we answer directly from the retrieved data.
The LLM is only called for complex analytical questions that require reasoning.
"""

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


class DirectAnswerEngine:
    """
    Intercepts queries where we have exact data and returns a precise answer.
    Bypasses the LLM entirely to prevent hallucination on factual questions.
    """

    def can_answer(self, query: str, context: dict[str, Any]) -> bool:
        """Return True if we can answer this query directly from data."""
        q = query.strip().lower()

        # Always handle empty-org case directly
        if self._is_empty_org(context):
            return True

        has_accounts = bool(context.get("cloud_accounts"))
        has_assets = bool(context.get("assets"))
        has_findings = bool(context.get("findings"))
        has_posture = bool(context.get("posture_snapshots"))
        has_compliance = bool(context.get("compliance_results"))

        # Count queries
        if any(w in q for w in ["how many", "how much", "count", "number of", "total"]):
            if any(w in q for w in ["resource", "asset", "instance", "ec2", "s3", "vpc"]) and has_assets:
                return True
            if any(w in q for w in ["finding", "issue", "vulnerability", "alert"]) and has_findings:
                return True
            if any(w in q for w in ["account", "cloud account"]) and has_accounts:
                return True

        # List queries
        if any(w in q for w in ["list", "show", "give me", "what are", "all my", "display"]):
            if any(w in q for w in ["resource", "asset", "instance", "ec2", "s3", "vpc", "iam", "kms", "subnet"]) and has_assets:
                return True
            if any(w in q for w in ["finding", "issue", "vulnerability", "alert", "security"]) and has_findings:
                return True
            if any(w in q for w in ["account", "cloud account", "connected"]) and has_accounts:
                return True

        # "What do you know about me" queries
        if any(w in q for w in ["what do you know", "what information", "know about me",
                                  "tell me about my", "what data", "my environment",
                                  "my account", "my infrastructure"]):
            return has_accounts or has_assets or has_findings

        # Status/posture queries
        if any(w in q for w in ["posture", "score", "security score", "overall status"]) and has_posture:
            return True

        # Account info queries
        if any(w in q for w in ["account id", "aws account", "which account", "connected account"]) and has_accounts:
            return True

        return False

    def answer(self, query: str, context: dict[str, Any]) -> str:
        """Generate a precise, data-grounded answer directly from context."""

        # Empty org — no cloud accounts connected yet
        if self._is_empty_org(context):
            return self._answer_empty_org()

        q = query.strip().lower()

        # ── "What do you know about me" ──────────────────────────────────────
        if any(w in q for w in ["what do you know", "what information", "know about me",
                                  "tell me about my", "what data", "my environment",
                                  "my account", "my infrastructure"]):
            return self._answer_environment_summary(context)

        # ── Count queries ────────────────────────────────────────────────────
        if any(w in q for w in ["how many", "how much", "count", "number of", "total"]):
            if any(w in q for w in ["resource", "asset", "instance", "ec2", "s3", "vpc", "iam", "kms", "subnet"]):
                return self._answer_resource_count(context, q)
            if any(w in q for w in ["finding", "issue", "vulnerability", "alert"]):
                return self._answer_finding_count(context, q)
            if any(w in q for w in ["account", "cloud account"]):
                return self._answer_account_count(context)

        # ── List queries ─────────────────────────────────────────────────────
        if any(w in q for w in ["list", "show", "give me", "what are", "all my", "display"]):
            if any(w in q for w in ["finding", "issue", "vulnerability", "alert", "security finding"]):
                return self._answer_list_findings(context, q)
            if any(w in q for w in ["resource", "asset", "instance", "ec2", "s3", "vpc", "iam", "kms", "subnet"]):
                return self._answer_list_resources(context, q)
            if any(w in q for w in ["account", "cloud account", "connected"]):
                return self._answer_list_accounts(context)

        # ── Posture/score queries ────────────────────────────────────────────
        if any(w in q for w in ["posture", "score", "security score", "overall status"]):
            return self._answer_posture(context)

        # ── Account info ─────────────────────────────────────────────────────
        if any(w in q for w in ["account id", "aws account", "which account", "connected account"]):
            return self._answer_account_info(context)

        # Fallback — shouldn't reach here if can_answer() was checked first
        return self._answer_environment_summary(context)

    def _is_empty_org(self, context: dict[str, Any]) -> bool:
        """Return True if this org has no cloud accounts connected."""
        accounts = context.get("cloud_accounts", [])
        return len(accounts) == 0

    def _answer_empty_org(self) -> str:
        """Clear message when the org has no cloud accounts connected."""
        return (
            "Your organization doesn't have any cloud accounts connected yet.\n\n"
            "To get started with CloudVisor Q, connect a cloud account:\n\n"
            "1. Go to **Settings → Cloud Accounts**\n"
            "2. Click **Connect Account**\n"
            "3. Choose your cloud provider (AWS, Azure, GCP, or OCI)\n"
            "4. Follow the onboarding steps\n\n"
            "Once connected, CloudVisor Q will have access to your real cloud security data "
            "and can answer questions about your resources, findings, compliance posture, and more."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Individual answer generators
    # ─────────────────────────────────────────────────────────────────────────

    def _answer_environment_summary(self, context: dict[str, Any]) -> str:
        """Full environment summary — answers 'what do you know about me'."""
        lines = ["Here's everything I know about your cloud environment:\n"]

        # Cloud accounts
        accounts = context.get("cloud_accounts", [])
        if accounts:
            lines.append(f"**Connected Cloud Accounts ({len(accounts)}):**")
            for acc in accounts:
                lines.append(
                    f"- {acc.get('provider','?').upper()} | "
                    f"Account: **{acc.get('account_name','?')}** (ID: `{acc.get('account_id','?')}`) | "
                    f"Status: {acc.get('status','?')} | "
                    f"Resources: {acc.get('resource_count',0)} | "
                    f"Last sync: {acc.get('last_sync_at','never')}"
                )
            lines.append("")

        # Resources
        assets = context.get("assets", [])
        if assets:
            by_type = Counter(a.get("resource_type", "?") for a in assets)
            by_provider = Counter(a.get("provider", "?").upper() for a in assets)
            public = sum(1 for a in assets if a.get("is_public"))
            lines.append(f"**Discovered Resources: {len(assets)} total**")
            lines.append(f"- Providers: {dict(by_provider)}")
            lines.append(f"- Internet-exposed: {public}")
            lines.append("- By type: " + ", ".join(f"{t}: {c}" for t, c in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:8]))
            lines.append("")

        # Findings
        findings = context.get("findings", [])
        if findings:
            by_sev = Counter(f.get("severity", "?") for f in findings)
            open_f = [f for f in findings if f.get("status") == "open"]
            lines.append(f"**Security Findings: {len(findings)} total**")
            lines.append(f"- By severity: {dict(by_sev)}")
            lines.append(f"- Open: {len(open_f)}")
            lines.append("")

        # Posture
        snapshots = context.get("posture_snapshots", [])
        if snapshots:
            latest = snapshots[0]
            lines.append(f"**Security Posture Score: {latest.get('posture_score','?')}**")
            lines.append(
                f"- Critical: {latest.get('critical_count',0)} | "
                f"High: {latest.get('high_count',0)} | "
                f"Medium: {latest.get('medium_count',0)} | "
                f"Low: {latest.get('low_count',0)}"
            )
            lines.append(f"- As of: {latest.get('snapshot_date','?')}")
            lines.append("")

        # Compliance
        compliance = context.get("compliance_results", [])
        if compliance:
            by_fw: dict[str, dict] = {}
            for r in compliance:
                fw = r.get("framework", "?")
                if fw not in by_fw:
                    by_fw[fw] = {"passed": 0, "failed": 0}
                if r.get("status") in ("passed", "pass"):
                    by_fw[fw]["passed"] += 1
                elif r.get("status") in ("failed", "fail"):
                    by_fw[fw]["failed"] += 1
            lines.append(f"**Compliance Controls: {len(compliance)} total**")
            for fw, d in by_fw.items():
                total = d["passed"] + d["failed"]
                pct = int(d["passed"] / total * 100) if total else 0
                lines.append(f"- {fw}: {pct}% pass ({d['passed']}/{total})")
            lines.append("")

        # Scans
        scans = context.get("recent_scans", [])
        if scans:
            lines.append(f"**Recent Scans: {len(scans)} on record**")

        if len(lines) == 1:
            return "No data available yet. Connect a cloud account to get started."

        return "\n".join(lines)

    def _answer_resource_count(self, context: dict[str, Any], q: str) -> str:
        """Answer 'how many resources do I have'."""
        assets = context.get("assets", [])
        if not assets:
            accounts = context.get("cloud_accounts", [])
            if accounts:
                total = sum(a.get("resource_count", 0) for a in accounts)
                return f"According to your connected cloud accounts, you have **{total} resources** synced."
            return "No resources found. Make sure your cloud account is connected and synced."

        by_provider = Counter(a.get("provider", "?").upper() for a in assets)
        by_type = Counter(a.get("resource_type", "?") for a in assets)
        public = sum(1 for a in assets if a.get("is_public"))

        # Filter by specific type if mentioned
        for rtype in ["ec2", "s3", "vpc", "iam", "kms", "subnet", "security group", "lambda", "rds"]:
            if rtype in q:
                matching = [a for a in assets if rtype.replace(" ", "").lower() in a.get("resource_type", "").lower()]
                if matching:
                    return f"You have **{len(matching)} {rtype.upper()} resources** in your environment."

        lines = [f"You have **{len(assets)} cloud resources** in total.\n"]
        lines.append(f"**By provider:** {dict(by_provider)}")
        lines.append(f"**Internet-exposed:** {public}")
        lines.append("\n**By resource type:**")
        for rtype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:10]:
            lines.append(f"- {rtype}: {count}")
        return "\n".join(lines)

    def _answer_finding_count(self, context: dict[str, Any], q: str) -> str:
        """Answer 'how many findings do I have'."""
        findings = context.get("findings", [])
        if not findings:
            return "No security findings found in your environment."

        by_sev = Counter(f.get("severity", "?") for f in findings)
        by_status = Counter(f.get("status", "?") for f in findings)
        open_f = by_status.get("open", 0)
        critical = by_sev.get("CRITICAL", 0)
        high = by_sev.get("HIGH", 0)

        lines = [f"You have **{len(findings)} security findings** in total.\n"]
        lines.append(f"**By severity:**")
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = by_sev.get(sev, 0)
            if count:
                lines.append(f"- {sev}: {count}")
        lines.append(f"\n**By status:**")
        for status, count in by_status.most_common():
            lines.append(f"- {status}: {count}")
        if critical > 0:
            lines.append(f"\n⚠️ **{critical} CRITICAL finding(s) require immediate attention.**")
        return "\n".join(lines)

    def _answer_account_count(self, context: dict[str, Any]) -> str:
        """Answer 'how many cloud accounts do I have'."""
        accounts = context.get("cloud_accounts", [])
        if not accounts:
            return "No cloud accounts are currently connected."
        by_provider = Counter(a.get("provider", "?").upper() for a in accounts)
        lines = [f"You have **{len(accounts)} connected cloud account(s)**.\n"]
        for provider, count in by_provider.items():
            lines.append(f"- {provider}: {count} account(s)")
        return "\n".join(lines)

    def _answer_list_findings(self, context: dict[str, Any], q: str) -> str:
        """Answer 'list all findings'."""
        findings = context.get("findings", [])
        if not findings:
            return "No security findings found in your environment."

        # Filter by severity if mentioned
        sev_filter = None
        for sev in ["critical", "high", "medium", "low"]:
            if sev in q:
                sev_filter = sev.upper()
                break

        # Filter by status if mentioned
        status_filter = None
        if "open" in q:
            status_filter = "open"
        elif "resolved" in q:
            status_filter = "resolved"

        filtered = findings
        if sev_filter:
            filtered = [f for f in filtered if f.get("severity", "").upper() == sev_filter]
        if status_filter:
            filtered = [f for f in filtered if f.get("status", "").lower() == status_filter]

        if not filtered:
            qualifier = f"{sev_filter} " if sev_filter else ""
            qualifier += f"{status_filter} " if status_filter else ""
            return f"No {qualifier}findings found."

        by_sev = Counter(f.get("severity", "?") for f in filtered)
        header = f"**{len(filtered)} security finding(s)**"
        if sev_filter or status_filter:
            header += f" (filtered: {sev_filter or ''} {status_filter or ''})"
        header += f"\nBy severity: {dict(by_sev)}\n"

        lines = [header]
        lines.append("| Severity | Title | Resource | Type | Status | Date |")
        lines.append("|----------|-------|----------|------|--------|------|")
        for f in filtered:
            date = (f.get("created_at") or f.get("last_seen_at") or "?")[:10]
            lines.append(
                f"| {f.get('severity','?')} "
                f"| {f.get('title','?')} "
                f"| {f.get('resource_name','?')} "
                f"| {f.get('resource_type','?')} "
                f"| {f.get('status','?')} "
                f"| {date} |"
            )
        return "\n".join(lines)

    def _answer_list_resources(self, context: dict[str, Any], q: str) -> str:
        """Answer 'list all resources'."""
        assets = context.get("assets", [])
        if not assets:
            return "No resources found. Make sure your cloud account is connected and synced."

        # Filter by type if mentioned
        type_filter = None
        for rtype in ["ec2", "s3", "vpc", "iam", "kms", "subnet", "security group", "lambda", "rds", "eks"]:
            if rtype in q:
                type_filter = rtype
                break

        filtered = assets
        if type_filter:
            filtered = [a for a in assets if type_filter.replace(" ", "").lower() in a.get("resource_type", "").lower()]

        if not filtered:
            return f"No {type_filter} resources found."

        by_type = Counter(a.get("resource_type", "?") for a in filtered)
        by_provider = Counter(a.get("provider", "?").upper() for a in filtered)
        public = sum(1 for a in filtered if a.get("is_public"))

        header = f"**{len(filtered)} resource(s)**"
        if type_filter:
            header += f" (type: {type_filter})"
        header += f"\nProviders: {dict(by_provider)} | Internet-exposed: {public}"
        header += "\nTypes: " + ", ".join(f"{t}:{c}" for t, c in sorted(by_type.items(), key=lambda x: x[1], reverse=True))

        lines = [header, ""]
        lines.append("| Name | Type | Region | Provider | Public | Findings |")
        lines.append("|------|------|--------|----------|--------|----------|")
        for a in filtered[:50]:  # Cap at 50 rows in the table
            lines.append(
                f"| {a.get('name','?')} "
                f"| {a.get('resource_type','?')} "
                f"| {a.get('region','?')} "
                f"| {a.get('provider','?').upper()} "
                f"| {'Yes' if a.get('is_public') else 'No'} "
                f"| {a.get('open_findings_count',0)} |"
            )
        if len(filtered) > 50:
            lines.append(f"\n*... and {len(filtered) - 50} more resources.*")
        return "\n".join(lines)

    def _answer_list_accounts(self, context: dict[str, Any]) -> str:
        """Answer 'list all connected accounts'."""
        accounts = context.get("cloud_accounts", [])
        if not accounts:
            return "No cloud accounts are currently connected."

        lines = [f"**{len(accounts)} connected cloud account(s):**\n"]
        lines.append("| Provider | Name | Account ID | Status | Resources | Last Sync |")
        lines.append("|----------|------|------------|--------|-----------|-----------|")
        for a in accounts:
            lines.append(
                f"| {a.get('provider','?').upper()} "
                f"| {a.get('account_name','?')} "
                f"| `{a.get('account_id','?')}` "
                f"| {a.get('status','?')} "
                f"| {a.get('resource_count',0)} "
                f"| {(a.get('last_sync_at') or 'never')[:10]} |"
            )
        return "\n".join(lines)

    def _answer_posture(self, context: dict[str, Any]) -> str:
        """Answer posture/score queries."""
        snapshots = context.get("posture_snapshots", [])
        if not snapshots:
            return "No posture data available yet."

        latest = snapshots[0]
        score = latest.get("posture_score", "?")
        critical = latest.get("critical_count", 0)
        high = latest.get("high_count", 0)
        medium = latest.get("medium_count", 0)
        low = latest.get("low_count", 0)
        date = latest.get("snapshot_date", "?")

        # Score interpretation
        if isinstance(score, (int, float)):
            if score >= 90:
                rating = "🟢 Excellent"
            elif score >= 70:
                rating = "🟡 Good"
            elif score >= 50:
                rating = "🟠 Fair"
            else:
                rating = "🔴 Poor"
        else:
            rating = "Unknown"

        lines = [
            f"**Security Posture Score: {score}/100** — {rating}",
            f"*As of {date}*\n",
            f"| Severity | Count |",
            f"|----------|-------|",
            f"| 🔴 Critical | {critical} |",
            f"| 🟠 High | {high} |",
            f"| 🟡 Medium | {medium} |",
            f"| 🔵 Low | {low} |",
        ]

        if critical > 0:
            lines.append(f"\n⚠️ **{critical} critical issue(s) require immediate attention.**")
        elif high > 0:
            lines.append(f"\n⚠️ **{high} high-severity issue(s) should be addressed soon.**")
        else:
            lines.append("\n✅ No critical or high-severity issues detected.")

        # Trend if we have history
        if len(snapshots) > 1:
            prev = snapshots[1]
            prev_score = prev.get("posture_score", score)
            if isinstance(score, (int, float)) and isinstance(prev_score, (int, float)):
                delta = score - prev_score
                if delta > 0:
                    lines.append(f"\n📈 Score improved by {delta} points since {prev.get('snapshot_date','?')}.")
                elif delta < 0:
                    lines.append(f"\n📉 Score decreased by {abs(delta)} points since {prev.get('snapshot_date','?')}.")

        return "\n".join(lines)

    def _answer_account_info(self, context: dict[str, Any]) -> str:
        """Answer account ID / account info queries."""
        accounts = context.get("cloud_accounts", [])
        if not accounts:
            return "No cloud accounts are currently connected."
        return self._answer_list_accounts(context)
