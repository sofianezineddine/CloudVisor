"""Prompt construction service for the RAG pipeline."""

import json
import logging
from typing import Any
from collections import Counter

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Builds system and user prompts from retrieved context."""

    # ─────────────────────────────────────────────────────────────────────────
    # System prompt: data block FIRST, then short instructions.
    # llama3.2:3b reads top-down — put the facts before the rules.
    # ─────────────────────────────────────────────────────────────────────────
    SYSTEM_PROMPT_TEMPLATE = """You are CloudVisor Q. Customer data:

=== DATA ===
{context_blocks}
=== END ===
{ui_context_block}
Use the data above to answer. Be direct and specific."""

    REMEDIATION_PROMPT_TEMPLATE = """You are CloudVisor Q generating a security remediation.

=== FINDING DATA ===
{context_blocks}
=== END ===
{ui_context_block}
Generate:
### What is wrong
### Why it matters
### Fix — Terraform
### Fix — AWS CLI
### Verification
Use real resource names/IDs/ARNs from the data above. Code is for human review only."""

    GENERAL_PROMPT = """You are CloudVisor Q, a cloud security assistant for the CloudVisor CNAPP platform.

{env_summary}

You help with: security posture, findings, compliance, remediation, threat investigation, and change analysis.
Answer helpfully. If the user asks about their data, use the environment summary above."""

    def build_prompts(self, query: str, context: dict[str, Any]) -> tuple[str, str]:
        """Build system and user prompts from query and context."""
        intent = context.get("intent", "POSTURE")
        ui_block = self._format_ui_context(context)
        history_block = self._format_conversation_history(context)

        if intent == "GENERAL":
            # For GENERAL, inject a rich environment summary so the model
            # can answer "what do you know about me" type questions
            env_summary = self._format_full_environment_summary(context)

            # If org has no data, use a clear onboarding message
            if not context.get("cloud_accounts"):
                system = (
                    "You are CloudVisor Q, a cloud security assistant.\n\n"
                    "This organization has no cloud accounts connected yet. "
                    "Respond helpfully and guide the user to connect a cloud account via Settings → Cloud Accounts."
                )
                user = f"{history_block}\n{query}" if history_block else query
                logger.info("Built GENERAL prompt: empty org")
                return system, user

            system = self.GENERAL_PROMPT.format(env_summary=env_summary)
            if ui_block:
                system += f"\n\n{ui_block}"
            user = f"{history_block}\n{query}" if history_block else query
            logger.info(f"Built GENERAL prompt: system={len(system)} chars")
            return system, user

        context_blocks = self._format_context_blocks(context)

        if intent == "REMEDIATION":
            system_prompt = self.REMEDIATION_PROMPT_TEMPLATE.format(
                ui_context_block=ui_block,
                context_blocks=context_blocks,
            )
        else:
            system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
                ui_context_block=ui_block,
                context_blocks=context_blocks,
            )

        # User prompt: pre-format the answer structure so the model fills in real values
        data_hint = self._build_data_hint(context, query)
        if history_block:
            user_prompt = f"{history_block}\n\nQuestion: {query}\n\n{data_hint}"
        else:
            user_prompt = f"Question: {query}\n\n{data_hint}"

        logger.info(
            f"Built prompts for intent={intent}: "
            f"system={len(system_prompt)} chars, user={len(user_prompt)} chars"
        )
        return system_prompt, user_prompt

    def _build_data_hint(self, context: dict[str, Any], query: str) -> str:
        """
        Pre-structure the answer so the model just fills in real values.
        This is the key technique for small models — give them the answer skeleton.
        """
        q = query.lower()
        hints = []

        # For listing queries, pre-fill the count so the model can't get it wrong
        if any(w in q for w in ["list", "show", "all", "what are"]):
            if context.get("findings") and any(w in q for w in ["finding", "issue", "vulnerability"]):
                findings = context["findings"]
                hints.append(f"There are {len(findings)} security findings. List them all from the [SECURITY FINDINGS] section above.")
            elif context.get("assets") and any(w in q for w in ["resource", "asset", "ec2", "s3", "iam"]):
                assets = context["assets"]
                hints.append(f"There are {len(assets)} resources. List them from the [ASSET INVENTORY] section above.")

        # For count queries
        if any(w in q for w in ["how many", "count", "number of"]):
            if context.get("findings") and any(w in q for w in ["finding", "issue"]):
                hints.append(f"The answer is {len(context['findings'])} findings.")
            elif context.get("assets") and any(w in q for w in ["resource", "asset"]):
                hints.append(f"The answer is {len(context['assets'])} resources.")

        # For "what do you know" queries
        if any(w in q for w in ["know about", "information", "tell me about", "what data"]):
            parts = []
            if context.get("cloud_accounts"):
                acc = context["cloud_accounts"][0]
                parts.append(f"1 {acc.get('provider','?').upper()} account (ID: {acc.get('account_id','?')}, {acc.get('resource_count',0)} resources)")
            if context.get("assets"):
                parts.append(f"{len(context['assets'])} discovered resources")
            if context.get("findings"):
                parts.append(f"{len(context['findings'])} security findings")
            if context.get("posture_snapshots"):
                latest = context["posture_snapshots"][0]
                parts.append(f"posture score: {latest.get('posture_score','?')}")
            if context.get("compliance_results"):
                parts.append(f"{len(context['compliance_results'])} compliance controls")
            if parts:
                hints.append("Summary of what I know: " + " | ".join(parts))

        return "\n".join(hints) if hints else "Answer directly from the data shown above."

    # ─────────────────────────────────────────────────────────────────────────
    # Context block assembly — query-aware, 6000-char budget.
    # qwen2.5:0.5b handles 6k chars in ~90s on CPU.
    # Each section has its own sub-limit to ensure all sections get space.
    # ─────────────────────────────────────────────────────────────────────────
    def _format_context_blocks(self, context: dict[str, Any]) -> str:
        MAX_CHARS = 6000
        SECTION_LIMITS = {
            "findings": 2000,    # ~25 findings at 80 chars each
            "assets": 2000,      # ~25 assets at 80 chars each
            "compliance": 400,   # summary only
            "posture": 300,      # 5 rows
            "resource_posture": 600,  # top 10
            "scans": 300,
            "accounts": 200,
        }
        intent = context.get("intent", "POSTURE")
        blocks: list[str] = []
        used = 0

        def add(label: str, text: str, limit: int = 0) -> bool:
            nonlocal used
            if used >= MAX_CHARS:
                return False
            if limit and len(text) > limit:
                text = text[:limit] + "\n...(truncated)"
            block = f"[{label}]\n{text}"
            remaining = MAX_CHARS - used
            if len(block) > remaining:
                block = block[:remaining] + "\n...(more data available)"
            blocks.append(block)
            used += len(block)
            return True

        # ── Always: cloud accounts ───────────────────────────────────────────
        if context.get("cloud_accounts"):
            add("CLOUD ACCOUNTS", self._format_cloud_accounts(context["cloud_accounts"]), SECTION_LIMITS["accounts"])

        # ── Intent-prioritized sections ──────────────────────────────────────
        if intent in ("POSTURE", "FINDING", "REMEDIATION"):
            if context.get("findings"):
                add("SECURITY FINDINGS", self._format_findings(context["findings"]), SECTION_LIMITS["findings"])
            if context.get("finding"):
                add("FINDING DETAIL", self._format_finding(context["finding"]))
            if context.get("assets"):
                add("ASSET INVENTORY", self._format_assets(context["assets"]), SECTION_LIMITS["assets"])
            if context.get("asset"):
                add("ASSET DETAIL", self._format_asset(context["asset"]))
            if context.get("preloaded_asset"):
                add("ASSET DETAIL", self._format_asset(context["preloaded_asset"]))
            if context.get("posture_snapshots"):
                add("POSTURE TREND", self._format_posture_snapshots(context["posture_snapshots"]), SECTION_LIMITS["posture"])
            if context.get("resource_posture"):
                add("RESOURCE POSTURE", self._format_resource_posture(context["resource_posture"]), SECTION_LIMITS["resource_posture"])
            if context.get("compliance_results"):
                add("COMPLIANCE", self._format_compliance_results(context["compliance_results"]), SECTION_LIMITS["compliance"])
            if context.get("recent_scans"):
                add("RECENT SCANS", self._format_scans(context["recent_scans"]), SECTION_LIMITS["scans"])

        elif intent == "COMPLIANCE":
            if context.get("compliance_results"):
                add("COMPLIANCE RESULTS", self._format_compliance_results(context["compliance_results"]), SECTION_LIMITS["compliance"])
            if context.get("compliance"):
                add("COMPLIANCE POSTURE", self._format_compliance(context["compliance"]), 400)
            if context.get("frameworks"):
                add("FRAMEWORKS", self._format_frameworks(context["frameworks"]), 300)
            if context.get("findings"):
                add("SECURITY FINDINGS", self._format_findings(context["findings"]), SECTION_LIMITS["findings"])
            if context.get("rules"):
                add("SECURITY RULES", self._format_rules(context["rules"]), 500)

        elif intent == "THREAT":
            if context.get("cdr_events"):
                add("CDR EVENTS", self._format_cdr_events(context["cdr_events"]), 800)
            if context.get("changes"):
                add("AUDIT LOG", self._format_changes(context["changes"]), 800)
            if context.get("incidents"):
                add("INCIDENTS", self._format_incidents(context["incidents"]), 400)
            if context.get("assets"):
                add("ASSET INVENTORY", self._format_assets(context["assets"]), SECTION_LIMITS["assets"])
            if context.get("resource_posture"):
                add("RESOURCE POSTURE", self._format_resource_posture(context["resource_posture"]), SECTION_LIMITS["resource_posture"])

        elif intent == "DRIFT":
            if context.get("changes"):
                add("AUDIT LOG", self._format_changes(context["changes"]), 1000)
            if context.get("asset_snapshots"):
                tw = context.get("time_window_hours", 24)
                add(f"ASSET CHANGES last {tw}h", self._format_asset_snapshots(context["asset_snapshots"], tw), 1000)
            if context.get("recent_scans"):
                add("RECENT SCANS", self._format_scans(context["recent_scans"]), SECTION_LIMITS["scans"])

        else:
            # Default: everything in priority order with limits
            for key, label, fmt, lim in [
                ("findings", "SECURITY FINDINGS", lambda: self._format_findings(context["findings"]), SECTION_LIMITS["findings"]),
                ("assets", "ASSET INVENTORY", lambda: self._format_assets(context["assets"]), SECTION_LIMITS["assets"]),
                ("posture_snapshots", "POSTURE TREND", lambda: self._format_posture_snapshots(context["posture_snapshots"]), SECTION_LIMITS["posture"]),
                ("compliance_results", "COMPLIANCE", lambda: self._format_compliance_results(context["compliance_results"]), SECTION_LIMITS["compliance"]),
                ("resource_posture", "RESOURCE POSTURE", lambda: self._format_resource_posture(context["resource_posture"]), SECTION_LIMITS["resource_posture"]),
                ("recent_scans", "RECENT SCANS", lambda: self._format_scans(context["recent_scans"]), SECTION_LIMITS["scans"]),
            ]:
                if context.get(key):
                    add(label, fmt(), lim)

        # ── Always append finding/asset history if present ───────────────────
        if context.get("finding_history"):
            add("FINDING HISTORY", self._format_finding_history(context["finding_history"]))
        if context.get("suppression_rules"):
            add("SUPPRESSION RULES", self._format_suppression_rules(context["suppression_rules"]))

        if not blocks:
            blocks.append("[NO DATA — no cloud accounts or resources found for this organization]")

        return "\n\n".join(blocks)

    def _format_full_environment_summary(self, context: dict[str, Any]) -> str:
        """Rich environment summary for GENERAL intent — covers everything the client has."""
        lines = []

        # Cloud accounts
        if context.get("cloud_accounts"):
            for acc in context["cloud_accounts"]:
                lines.append(
                    f"- Cloud account: {acc.get('provider','?').upper()} "
                    f"'{acc.get('account_name','?')}' "
                    f"(ID: {acc.get('account_id','?')}, "
                    f"status: {acc.get('status','?')}, "
                    f"resources: {acc.get('resource_count',0)}, "
                    f"last sync: {acc.get('last_sync_at','never')})"
                )

        # Assets
        if context.get("assets"):
            assets = context["assets"]
            by_type = Counter(a.get("resource_type", "?") for a in assets)
            by_provider = Counter(a.get("provider", "?").upper() for a in assets)
            public = sum(1 for a in assets if a.get("is_public"))
            lines.append(
                f"- Total resources: {len(assets)} "
                f"(providers: {dict(by_provider)}, internet-exposed: {public})"
            )
            lines.append(
                "  Types: " + ", ".join(f"{t}:{c}" for t, c in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:8])
            )

        # Findings
        if context.get("findings"):
            findings = context["findings"]
            by_sev = Counter(f.get("severity", "?") for f in findings)
            lines.append(f"- Security findings: {len(findings)} total — {dict(by_sev)}")

        # Posture
        if context.get("posture_snapshots"):
            latest = context["posture_snapshots"][0]
            lines.append(
                f"- Latest posture score: {latest.get('posture_score','?')} "
                f"(Critical: {latest.get('critical_count',0)}, "
                f"High: {latest.get('high_count',0)}, "
                f"Medium: {latest.get('medium_count',0)}, "
                f"Low: {latest.get('low_count',0)})"
            )

        # Compliance
        if context.get("compliance_results"):
            results = context["compliance_results"]
            by_fw: dict[str, dict] = {}
            for r in results:
                fw = r.get("framework", "?")
                if fw not in by_fw:
                    by_fw[fw] = {"passed": 0, "failed": 0}
                if r.get("status") in ("passed", "pass"):
                    by_fw[fw]["passed"] += 1
                elif r.get("status") in ("failed", "fail"):
                    by_fw[fw]["failed"] += 1
            for fw, d in by_fw.items():
                total = d["passed"] + d["failed"]
                pct = int(d["passed"] / total * 100) if total else 0
                lines.append(f"- Compliance {fw}: {pct}% pass ({d['passed']}/{total} controls)")

        # Scans
        if context.get("recent_scans"):
            lines.append(f"- Recent scans: {len(context['recent_scans'])} scans on record")

        if not lines:
            lines.append("- No data available yet. Connect a cloud account to get started.")

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # Individual formatters — compact but complete
    # ─────────────────────────────────────────────────────────────────────────

    def _format_cloud_accounts(self, accounts: list[dict]) -> str:
        if not accounts:
            return "No cloud accounts connected."
        lines = []
        for a in accounts:
            lines.append(
                f"- {a.get('provider','?').upper()} | Name: {a.get('account_name','?')} | "
                f"ID: {a.get('account_id','?')} | Status: {a.get('status','?')} | "
                f"Resources: {a.get('resource_count',0)} | Last sync: {a.get('last_sync_at','never')}"
            )
        return "\n".join(lines)

    def _format_assets(self, assets: list[dict]) -> str:
        if not assets:
            return "No assets found."
        by_type = Counter(a.get("resource_type", "?") for a in assets)
        by_provider = Counter(a.get("provider", "?").upper() for a in assets)
        public = sum(1 for a in assets if a.get("is_public"))
        # Compact one-line per asset, show all
        lines = [
            f"Total:{len(assets)} | Providers:{dict(by_provider)} | Public:{public}",
            "Types: " + " | ".join(f"{t}:{c}" for t, c in sorted(by_type.items(), key=lambda x: x[1], reverse=True)),
        ]
        # Show all assets in ultra-compact format
        for a in assets:
            pub = "Y" if a.get("is_public") else "N"
            lines.append(
                f"{a.get('name','?')}|{a.get('resource_type','?')}|{a.get('region','?')}|pub={pub}|f={a.get('open_findings_count',0)}"
            )
        return "\n".join(lines)

    def _format_asset(self, asset: dict) -> str:
        return json.dumps(asset, indent=2, default=str)

    def _format_findings(self, findings: list[dict]) -> str:
        if not findings:
            return "No findings found."
        by_sev = Counter(f.get("severity", "?") for f in findings)
        lines = [
            f"Total:{len(findings)} | {dict(by_sev)}",
        ]
        # Ultra-compact: one line per finding
        for f in findings:
            lines.append(
                f"[{f.get('severity','?')}] {f.get('title','?')} | "
                f"{f.get('resource_name','?')}({f.get('resource_type','?')}) | "
                f"{f.get('status','?')} | {(f.get('created_at') or f.get('last_seen_at','?'))[:10]}"
            )
        return "\n".join(lines)

    def _format_finding(self, finding: dict) -> str:
        return json.dumps(finding, indent=2, default=str)

    def _format_posture_snapshots(self, snapshots: list[dict]) -> str:
        if not snapshots:
            return "No posture history."
        lines = ["date         | score | critical | high | medium | low"]
        lines.append("-" * 55)
        for s in snapshots[:10]:
            lines.append(
                f"{s.get('snapshot_date','?'):<12} | "
                f"{s.get('posture_score',0):>5} | "
                f"{s.get('critical_count',0):>8} | "
                f"{s.get('high_count',0):>4} | "
                f"{s.get('medium_count',0):>6} | "
                f"{s.get('low_count',0):>3}"
            )
        return "\n".join(lines)

    def _format_resource_posture(self, resources: list[dict]) -> str:
        if not resources:
            return "No resource posture data."
        lines = [f"Top {min(len(resources),20)} by risk:"]
        for r in resources[:20]:
            flags = ""
            if r.get("is_internet_exposed"):
                flags += "[EXPOSED]"
            if r.get("contains_sensitive_data"):
                flags += "[SENSITIVE]"
            lines.append(
                f"{r.get('resource_name') or r.get('resource_id','?')}"
                f"({r.get('resource_type','?')},{r.get('region','?')})"
                f"{flags} risk={r.get('risk_score',0)} "
                f"C:{r.get('critical_count',0)} H:{r.get('high_count',0)} "
                f"M:{r.get('medium_count',0)} L:{r.get('low_count',0)}"
            )
        return "\n".join(lines)

    def _format_compliance_results(self, results: list[dict]) -> str:
        if not results:
            return "No compliance results."
        by_fw: dict[str, dict] = {}
        for r in results:
            fw = r.get("framework", "?")
            if fw not in by_fw:
                by_fw[fw] = {"passed": 0, "failed": 0, "unknown": 0}
            s = r.get("status", "unknown")
            if s in ("passed", "pass"):
                by_fw[fw]["passed"] += 1
            elif s in ("failed", "fail"):
                by_fw[fw]["failed"] += 1
            else:
                by_fw[fw]["unknown"] += 1
        lines = [f"Total controls: {len(results)}"]
        for fw, d in by_fw.items():
            total = d["passed"] + d["failed"] + d["unknown"]
            pct = int(d["passed"] / total * 100) if total else 0
            lines.append(f"{fw}: {pct}% pass ({d['passed']}/{total}, {d['failed']} failed)")
        return "\n".join(lines)

    def _format_compliance(self, compliance: dict) -> str:
        if not compliance:
            return "No compliance data."
        lines = []
        for k, v in list(compliance.items())[:15]:
            lines.append(f"- {k}: {str(v)[:120]}")
        return "\n".join(lines)

    def _format_frameworks(self, frameworks: list[dict]) -> str:
        if not frameworks:
            return "No frameworks."
        return "\n".join(
            f"- {f.get('display_name', f.get('name','?'))} v{f.get('version','?')} ({f.get('control_count',0)} controls)"
            for f in frameworks
        )

    def _format_scans(self, scans: list[dict]) -> str:
        if not scans:
            return "No recent scans."
        lines = []
        for s in scans[:10]:
            lines.append(
                f"- {s.get('scan_type','?')} | {s.get('status','?')} | "
                f"started: {s.get('started_at','?')} | "
                f"resources: {s.get('resources_scanned',0)} | "
                f"findings created: {s.get('findings_created',0)}"
            )
        return "\n".join(lines)

    def _format_incidents(self, incidents: list[dict]) -> str:
        if not incidents:
            return "No incidents."
        lines = [f"Total: {len(incidents)}"]
        for i in incidents[:10]:
            lines.append(
                f"- [{i.get('severity','?')}] {i.get('title','?')} "
                f"(status: {i.get('status','?')}, findings: {i.get('finding_count',0)})"
            )
        return "\n".join(lines)

    def _format_cdr_events(self, events: list[dict]) -> str:
        if not events:
            return "No CDR events."
        lines = []
        for e in events[:15]:
            lines.append(
                f"- {e.get('event_name','?')} | time: {e.get('event_time','?')} | "
                f"user: {e.get('user_identity','?')} | ip: {e.get('source_ip','?')}"
            )
        return "\n".join(lines)

    def _format_changes(self, changes: list[dict]) -> str:
        if not changes:
            return "No changes."
        lines = [f"Total: {len(changes)} changes"]
        for c in changes[:15]:
            lines.append(
                f"- [{c.get('timestamp','?')}] {c.get('action','?')} "
                f"{c.get('resource_type','')} {c.get('resource_id','')}"
            )
        return "\n".join(lines)

    def _format_rules(self, rules: list[dict]) -> str:
        if not rules:
            return "No rules."
        lines = []
        for r in rules[:15]:
            lines.append(
                f"- [{r.get('severity','?')}] {r.get('title','?')} "
                f"(id: {r.get('rule_id','?')}, category: {r.get('category','?')})"
            )
        return "\n".join(lines)

    def _format_suppression_rules(self, rules: list[dict]) -> str:
        if not rules:
            return "No suppression rules."
        lines = [f"Active: {len(rules)}"]
        for r in rules[:10]:
            lines.append(
                f"- rule: {r.get('rule_id','*')} | reason: {r.get('reason','?')} | "
                f"by: {r.get('created_by','?')} | expires: {r.get('expires_at','never')}"
            )
        return "\n".join(lines)

    def _format_finding_history(self, history: list[dict]) -> str:
        if not history:
            return "No history."
        lines = []
        for h in history:
            lines.append(
                f"- {h.get('changed_at','?')}: {h.get('old_status','?')} → "
                f"{h.get('new_status','?')} by {h.get('changed_by','?')}"
            )
        return "\n".join(lines)

    def _format_asset_snapshots(self, snapshots: list[dict], hours: int = 24) -> str:
        if not snapshots:
            return f"No changes in last {hours}h."
        lines = [f"{len(snapshots)} resources changed in last {hours}h:"]
        for s in snapshots[:20]:
            diff = s.get("diff_from_previous") or {}
            changed = list(diff.keys())[:5] if isinstance(diff, dict) else []
            flag = " [NOW-PUBLIC]" if s.get("is_public") else ""
            lines.append(
                f"  {s.get('name', s.get('asset_id','?'))} "
                f"({s.get('resource_type','?')}, {s.get('region','?')}){flag}"
                + (f" changed: {', '.join(changed)}" if changed else "")
            )
        return "\n".join(lines)

    def _format_users(self, users: list[dict]) -> str:
        if not users:
            return "No users."
        lines = []
        for u in users:
            roles = [r for r in (u.get("roles") or []) if r]
            lines.append(
                f"- {u.get('full_name','?')} ({u.get('email','?')}) | "
                f"active={u.get('is_active',False)} | "
                f"roles={','.join(roles) if roles else 'none'} | "
                f"last login: {u.get('last_login_at','never')}"
            )
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # UI context + conversation history
    # ─────────────────────────────────────────────────────────────────────────

    def _format_ui_context(self, context: dict[str, Any]) -> str:
        ui = context.get("ui_context")
        if not ui:
            return ""
        lines = ["[USER CONTEXT]"]
        page = ui.get("current_page") or ui.get("current_path", "")
        if page:
            lines.append(f"Current page: {page}")
        scope = ui.get("scope", {})
        if scope:
            lines.append(
                f"Scope: {scope.get('label','')} "
                f"(provider: {scope.get('provider','')}, mode: {scope.get('mode','')})"
            )
            for acc in scope.get("accounts", []):
                lines.append(
                    f"  - {acc.get('name', acc.get('account_id','?'))} "
                    f"({acc.get('provider','?').upper()}) | "
                    f"resources: {acc.get('resource_count',0)} | "
                    f"critical: {acc.get('critical_count',0)}"
                )
        return "\n".join(lines)

    def _format_conversation_history(self, context: dict[str, Any]) -> str:
        history = context.get("conversation_history", [])
        if not history:
            return ""
        lines = ["[CONVERSATION HISTORY]"]
        for msg in history[-6:]:  # last 6 turns
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")[:400]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
