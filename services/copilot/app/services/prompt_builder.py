"""Prompt construction for the refactored copilot.

Design principles:
1. System prompt is SHORT — no templates, no examples the model can copy.
2. Context is INJECTED ONLY when needed (based on query_router classification).
3. Conversation history is passed as real chat turns, not embedded text.
4. Each query type gets a focused prompt tailored to what the user asked.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any

from .query_router import QueryType

logger = logging.getLogger(__name__)


# Short, rule-based identity. No templates, no hardcoded examples.
IDENTITY = (
    "You are CloudVisor Q, a cloud security analyst embedded in the CloudVisor "
    "platform. You have read access to the user's live cloud security data.\n\n"
    "Rules:\n"
    "- Answer only what the user asks. Keep responses focused and proportional.\n"
    "- Never repeat information already given in the conversation.\n"
    "- Never start follow-up messages with an introduction.\n"
    "- Use exact numbers, IDs, and names from the provided data. Never invent values.\n"
    "- If asked a simple question, give a simple answer.\n"
    "- Format with markdown when helpful (lists, code blocks). Plain prose otherwise."
)


class PromptBuilder:
    """Builds system + messages for the LLM based on query classification."""

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────

    def build_messages(
        self,
        query: str,
        context: dict[str, Any],
        query_type: QueryType,
        conversation_history: list[dict] | None = None,
    ) -> list[dict]:
        """
        Build the full messages array to send to the LLM.
        Returns: [{"role": "system", ...}, {"role": "user", ...}, ...]
        """
        system_prompt = self._build_system_prompt(query, context, query_type)
        messages: list[dict] = [{"role": "system", "content": system_prompt}]

        # Real multi-turn: prior turns as actual chat messages
        for msg in (conversation_history or [])[-8:]:
            role = msg.get("role", "user")
            content = str(msg.get("content", "")).strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": query})
        logger.info(
            f"Built {len(messages)} messages for query_type={query_type}, "
            f"system={len(system_prompt)} chars, history={len(messages) - 2}"
        )
        return messages

    # ─────────────────────────────────────────────────────────────────────
    # System prompt construction — one method per query type
    # ─────────────────────────────────────────────────────────────────────

    def _build_system_prompt(
        self,
        query: str,
        context: dict[str, Any],
        query_type: QueryType,
    ) -> str:
        """Dispatch to the right prompt builder based on query type."""
        ui_block = self._format_ui_context(context)

        if query_type == QueryType.SMALL_TALK:
            return (
                f"{IDENTITY}\n\n"
                "The user sent a short greeting or small-talk message. "
                "Reply briefly and naturally. Do NOT output any security data, "
                "posture summary, or findings unless asked."
            )

        if query_type == QueryType.META:
            return (
                f"{IDENTITY}\n\n"
                "The user is asking what you can do. Briefly describe your "
                "capabilities (answer questions about their cloud security posture, "
                "findings, assets, compliance, and remediation). Keep it under "
                "80 words. Do not dump security data."
            )

        if query_type == QueryType.ACCOUNTS:
            data_block = self._format_accounts_only(context)
            return (
                f"{IDENTITY}\n\n"
                f"## Connected Cloud Accounts\n{data_block}\n"
                f"{ui_block}\n"
                "Answer the user's question about their connected accounts. "
                "Be concise."
            )

        if query_type == QueryType.POSTURE:
            data_block = self._format_posture_summary(context)
            return (
                f"{IDENTITY}\n\n"
                f"## Current Security Posture\n{data_block}\n"
                f"{ui_block}\n"
                "Answer the posture question directly using the numbers above."
            )

        if query_type == QueryType.FINDINGS:
            data_block = self._format_findings_focused(context, query)
            return (
                f"{IDENTITY}\n\n"
                f"## Security Findings\n{data_block}\n"
                f"{ui_block}\n"
                "Answer the user's question about findings. "
                "List specific ones with severity and resource when relevant."
            )

        if query_type == QueryType.ASSETS:
            data_block = self._format_assets_focused(context, query)
            return (
                f"{IDENTITY}\n\n"
                f"## Cloud Assets\n{data_block}\n"
                f"{ui_block}\n"
                "Answer the user's question about their cloud resources/assets."
            )

        if query_type == QueryType.COMPLIANCE:
            data_block = self._format_compliance(context)
            return (
                f"{IDENTITY}\n\n"
                f"## Compliance Status\n{data_block}\n"
                f"{ui_block}\n"
                "Answer the compliance question directly. Cite framework pass rates "
                "and failed controls where relevant."
            )

        if query_type == QueryType.REMEDIATION:
            data_block = self._format_remediation_context(context)
            return (
                f"{IDENTITY}\n\n"
                f"## Relevant Data\n{data_block}\n"
                f"{ui_block}\n"
                "Provide a concrete fix. Structure:\n"
                "1. What is the issue (1-2 sentences)\n"
                "2. Why it matters (1 sentence)\n"
                "3. Fix — provide AWS CLI / Terraform / IAM policy as appropriate\n"
                "4. Verification step\n"
                "Use the exact resource IDs from the data above."
            )

        if query_type in (QueryType.COUNT, QueryType.LIST):
            data_block = self._format_broad_summary(context)
            return (
                f"{IDENTITY}\n\n"
                f"## Available Data\n{data_block}\n"
                f"{ui_block}\n"
                "Answer the user's count/list question precisely using the data above."
            )

        # GENERAL fallback
        data_block = self._format_broad_summary(context)
        return (
            f"{IDENTITY}\n\n"
            f"## Security Data\n{data_block}\n"
            f"{ui_block}\n"
            "Answer the user's question using the data above. Be specific and concise."
        )

    # ─────────────────────────────────────────────────────────────────────
    # Focused context formatters — each returns compact, relevant data only
    # ─────────────────────────────────────────────────────────────────────

    def _format_accounts_only(self, context: dict[str, Any]) -> str:
        accounts = context.get("cloud_accounts") or []
        if not accounts:
            return "No cloud accounts are currently connected."

        lines = [f"Total: {len(accounts)} account(s)"]
        for a in accounts:
            lines.append(
                f"- {a.get('provider', '?').upper()} | {a.get('account_id', '?')}"
                f" | status: {a.get('status', '?')}"
                f" | resources: {a.get('resource_count', 0)}"
                f" | last sync: {a.get('last_sync_at', 'never')}"
            )
        return "\n".join(lines)

    def _format_posture_summary(self, context: dict[str, Any]) -> str:
        lines = []

        accounts = context.get("cloud_accounts") or []
        if accounts:
            providers = sorted({a.get("provider", "?").upper() for a in accounts})
            total_resources = sum(a.get("resource_count", 0) for a in accounts)
            lines.append(
                f"Providers: {', '.join(providers)} "
                f"({len(accounts)} account(s), {total_resources} resources)"
            )

        snapshots = context.get("posture_snapshots") or []
        if snapshots:
            latest = snapshots[0]
            lines.append(
                f"Posture score: {latest.get('posture_score', '?')}/100 "
                f"(Critical: {latest.get('critical_count', 0)}, "
                f"High: {latest.get('high_count', 0)}, "
                f"Medium: {latest.get('medium_count', 0)}, "
                f"Low: {latest.get('low_count', 0)})"
            )

        findings = context.get("findings") or []
        if findings:
            by_sev = Counter(f.get("severity", "?") for f in findings)
            lines.append(f"Active findings: {len(findings)} total — {dict(by_sev)}")

        return "\n".join(lines) if lines else "No posture data available."

    def _format_findings_focused(self, context: dict[str, Any], query: str) -> str:
        findings = context.get("findings") or []
        if not findings:
            return "No findings found."

        by_sev = Counter(f.get("severity", "?") for f in findings)
        lines = [f"Total findings: {len(findings)} — {dict(by_sev)}"]

        # Sort by severity
        severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        sorted_findings = sorted(
            findings,
            key=lambda f: severity_rank.get(str(f.get("severity", "")).upper(), 99),
        )

        # Show up to 20 most severe
        for f in sorted_findings[:20]:
            lines.append(
                f"- [{f.get('severity', '?')}] {f.get('title', '?')} "
                f"| resource: {f.get('resource_name', '?')} "
                f"({f.get('resource_type', '?')}) "
                f"| status: {f.get('status', '?')}"
            )

        if len(findings) > 20:
            lines.append(f"... and {len(findings) - 20} more findings")
        return "\n".join(lines)

    def _format_assets_focused(self, context: dict[str, Any], query: str) -> str:
        assets = context.get("assets") or []
        if not assets:
            return "No assets found."

        by_type = Counter(a.get("resource_type", "?") for a in assets)
        by_provider = Counter(str(a.get("provider", "?")).upper() for a in assets)
        public_count = sum(1 for a in assets if a.get("is_public"))

        lines = [
            f"Total: {len(assets)} resources | "
            f"providers: {dict(by_provider)} | "
            f"internet-exposed: {public_count}",
            "By type: " + ", ".join(
                f"{t}:{c}"
                for t, c in sorted(by_type.items(), key=lambda x: x[1], reverse=True)
            ),
        ]

        # Try to match assets to the query terms (e.g. "s3", "ec2")
        q_lower = query.lower()
        matching_types = [t for t in by_type.keys() if t.lower() in q_lower]
        if matching_types:
            lines.append("\nMatching your query:")
            for a in assets:
                if a.get("resource_type") in matching_types:
                    lines.append(
                        f"- {a.get('name', a.get('asset_id', '?'))} "
                        f"({a.get('resource_type', '?')}, "
                        f"{a.get('region', '?')}, "
                        f"public={'yes' if a.get('is_public') else 'no'})"
                    )
                    if len(lines) > 30:
                        break

        return "\n".join(lines)

    def _format_compliance(self, context: dict[str, Any]) -> str:
        results = context.get("compliance_results") or []
        if not results:
            return "No compliance data available."

        by_fw: dict[str, dict[str, int]] = {}
        for r in results:
            fw = r.get("framework", "?")
            if fw not in by_fw:
                by_fw[fw] = {"passed": 0, "failed": 0, "other": 0}
            status = str(r.get("status", "")).lower()
            if status in ("passed", "pass"):
                by_fw[fw]["passed"] += 1
            elif status in ("failed", "fail"):
                by_fw[fw]["failed"] += 1
            else:
                by_fw[fw]["other"] += 1

        lines = [f"Total controls evaluated: {len(results)}"]
        for fw, counts in by_fw.items():
            total = sum(counts.values())
            pct = int(counts["passed"] / total * 100) if total else 0
            lines.append(
                f"- {fw}: {pct}% pass "
                f"({counts['passed']}/{total}, {counts['failed']} failed)"
            )

        return "\n".join(lines)

    def _format_remediation_context(self, context: dict[str, Any]) -> str:
        lines = []

        # If a specific finding was preloaded, focus on that
        if context.get("finding"):
            lines.append("## Target finding")
            lines.append(json.dumps(context["finding"], indent=2, default=str)[:1500])
            return "\n".join(lines)

        findings = context.get("findings") or []
        if findings:
            lines.append(f"## Active findings ({len(findings)})")
            for f in findings[:10]:
                lines.append(
                    f"- [{f.get('severity', '?')}] {f.get('title', '?')} "
                    f"on {f.get('resource_name', '?')} ({f.get('resource_type', '?')})"
                )

        rules = context.get("rules") or []
        if rules:
            lines.append(f"\n## Security rules (top {min(len(rules), 5)})")
            for r in rules[:5]:
                lines.append(
                    f"- [{r.get('severity', '?')}] {r.get('title', '?')} "
                    f"(id: {r.get('rule_id', '?')})"
                )

        return "\n".join(lines) if lines else "No remediation context available."

    def _format_broad_summary(self, context: dict[str, Any]) -> str:
        """Compact summary for GENERAL / COUNT / LIST queries."""
        lines = []

        accounts = context.get("cloud_accounts") or []
        if accounts:
            providers = sorted({a.get("provider", "?").upper() for a in accounts})
            total_resources = sum(a.get("resource_count", 0) for a in accounts)
            lines.append(
                f"Accounts: {len(accounts)} connected "
                f"({', '.join(providers)}) | total resources: {total_resources}"
            )

        snapshots = context.get("posture_snapshots") or []
        if snapshots:
            latest = snapshots[0]
            lines.append(
                f"Posture: {latest.get('posture_score', '?')}/100 | "
                f"Critical: {latest.get('critical_count', 0)}, "
                f"High: {latest.get('high_count', 0)}, "
                f"Medium: {latest.get('medium_count', 0)}"
            )

        findings = context.get("findings") or []
        if findings:
            by_sev = Counter(f.get("severity", "?") for f in findings)
            lines.append(f"Findings: {len(findings)} total — {dict(by_sev)}")

        assets = context.get("assets") or []
        if assets:
            by_type = Counter(a.get("resource_type", "?") for a in assets)
            top_types = ", ".join(
                f"{t}:{c}"
                for t, c in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5]
            )
            lines.append(f"Assets: {len(assets)} total | top types: {top_types}")

        return "\n".join(lines) if lines else "No data available yet."

    def _format_ui_context(self, context: dict[str, Any]) -> str:
        ui = context.get("ui_context")
        if not ui:
            return ""

        parts = ["\n## UI Context"]
        page = ui.get("current_page") or ui.get("current_path", "")
        if page:
            parts.append(f"- Current page: {page}")

        scope = ui.get("scope") or {}
        if scope and scope.get("label"):
            parts.append(
                f"- Scope: {scope.get('label', '')} "
                f"(provider: {scope.get('provider', '')})"
            )
        return "\n".join(parts)
