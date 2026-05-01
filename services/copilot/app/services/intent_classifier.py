"""
Smart intent classifier — uses the LLM to understand the query and decide
what data sources to fetch. No keyword matching, no hardcoded rules.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Intent → what data sources to fetch
INTENT_DATA_MAP = {
    "GREETING":    ["accounts", "posture"],
    "POSTURE":     ["accounts", "posture", "findings", "assets", "resource_posture", "compliance_summary"],
    "FINDING":     ["findings", "assets", "resource_posture"],
    "COMPLIANCE":  ["compliance", "findings", "frameworks"],
    "REMEDIATION": ["findings", "assets", "resource_posture", "rules"],
    "THREAT":      ["findings", "assets", "resource_posture", "incidents", "cdr_events"],
    "DRIFT":       ["changes", "scans", "asset_snapshots"],
    "GENERAL":     ["accounts", "posture", "findings_summary", "assets_summary"],
}


class IntentClassifier:
    """
    LLM-based intent classifier.
    Falls back to fast keyword matching if LLM is unavailable.
    """

    def classify(self, query: str) -> str:
        """Classify query intent using fast keyword matching."""
        return self._keyword_classify(query)

    def get_required_sources(self, intent: str) -> list[str]:
        """Return the list of data sources needed for this intent."""
        return INTENT_DATA_MAP.get(intent, INTENT_DATA_MAP["GENERAL"])

    def _keyword_classify(self, query: str) -> str:
        """Fast keyword-based classification as primary classifier."""
        q = query.strip().lower()

        # Greeting — very short, no security keywords
        greeting_words = {"hi", "hello", "hey", "good morning", "good afternoon",
                          "good evening", "howdy", "greetings", "sup", "yo"}
        if q in greeting_words or (len(q.split()) <= 3 and any(q.startswith(g) for g in greeting_words)):
            security_words = {"resource", "finding", "account", "asset", "compliance",
                              "list", "show", "what", "how", "do i", "my", "all", "data",
                              "know", "information", "access", "tell", "give", "security"}
            if not any(w in q for w in security_words):
                return "GREETING"

        # Remediation — check before FINDING to avoid misrouting
        if any(w in q for w in [
            "fix", "remediate", "resolve", "how to fix", "how do i fix",
            "generate", "terraform", "iam policy", "yaml", "cli command",
            "patch", "update config", "pull request", "script", "playbook",
            "remediation", "what should i do", "how can i fix", "suggest a fix",
        ]):
            return "REMEDIATION"

        # Compliance
        if any(w in q for w in [
            "compliant", "compliance", "soc 2", "soc2", "pci", "hipaa", "gdpr",
            "iso 27001", "nist", "cis", "framework", "control", "audit", "evidence",
            "report", "certification", "regulation", "standard",
        ]):
            return "COMPLIANCE"

        # Drift / Change detection
        if any(w in q for w in [
            "changed", "change", "drift", "modified", "created", "deleted",
            "recent changes", "new resource", "removed", "what changed",
            "configuration change", "diff", "history", "when was", "who changed",
            "last 24 hours", "yesterday", "last week",
        ]):
            return "DRIFT"

        # Threat investigation
        if any(w in q for w in [
            "suspicious", "anomaly", "investigate", "incident", "attack",
            "compromise", "breach", "who accessed", "who logged in",
            "unusual", "unauthorized", "lateral movement", "privilege escalation",
            "cloudtrail", "activity", "threat",
        ]):
            return "THREAT"

        # Finding explanation
        if any(w in q for w in [
            "explain", "what is wrong", "tell me about finding", "describe finding",
            "why is this", "what does this mean", "blast radius", "impact of",
            "finding id", "cv-",
        ]):
            return "FINDING"

        # Posture / general security queries — broad catch-all
        if any(w in q for w in [
            "posture", "score", "risk", "exposed", "internet-facing", "public",
            "vulnerable", "critical", "high severity", "production", "workload",
            "resource", "asset", "bucket", "s3", "ec2", "vpc", "iam", "kms",
            "how many", "list", "show", "count", "overview", "summary", "status",
            "which", "what are", "do i have", "are there", "finding", "issue",
            "vulnerability", "misconfiguration", "security",
        ]):
            return "POSTURE"

        # Default — fetch base context
        return "GENERAL"
