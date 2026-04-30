"""Intent classification service for query routing."""

import logging
import re

logger = logging.getLogger(__name__)

IntentType = str  # "POSTURE" | "FINDING" | "COMPLIANCE" | "REMEDIATION" | "THREAT" | "DRIFT" | "GENERAL"

# Short queries that don't need data retrieval — ONLY pure greetings
GENERAL_PATTERNS = [
    "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
    "how are you", "what are you", "who are you",
    "thanks", "thank you", "bye", "goodbye",
    "tell me about cloudvisor", "what is cloudvisor",
]


class IntentClassifier:
    """Classifies user queries into one of 7 intent domains."""

    # Ordered by priority — first match wins on tie-break
    INTENT_KEYWORDS: dict[str, list[str]] = {
        # Domain 4 — Remediation Generator (check before FINDING to avoid misrouting)
        "REMEDIATION": [
            "fix", "remediate", "resolve", "how to fix", "how do i fix",
            "generate", "terraform", "iam policy", "json policy", "yaml",
            "cli command", "aws cli", "patch", "update config", "pull request",
            "pr", "code to fix", "script", "playbook", "remediation steps",
            "what should i do", "how can i fix", "suggest a fix",
        ],
        # Domain 2 — Finding Explanation
        "FINDING": [
            "finding", "explain", "what is wrong", "tell me about", "describe",
            "cv-", "issue", "vulnerability", "misconfiguration", "why is this",
            "what does this mean", "blast radius", "impact", "severity",
        ],
        # Domain 3 — Compliance Assistant
        "COMPLIANCE": [
            "compliant", "compliance", "soc 2", "soc2", "pci", "pci-dss",
            "hipaa", "gdpr", "iso 27001", "nist", "cis", "framework",
            "control", "audit", "evidence", "report", "passing", "failing",
            "certification", "regulation", "standard",
        ],
        # Domain 5 — Threat Investigation
        "THREAT": [
            "what did", "activity", "cloudtrail", "suspicious", "anomaly",
            "investigate", "incident", "attack", "compromise", "breach",
            "who accessed", "who logged in", "iam user", "role assumption",
            "unusual", "unauthorized", "lateral movement", "privilege escalation",
            "last 24 hours", "last hour", "today", "this morning",
        ],
        # Domain 6 — Change & Drift Analysis
        "DRIFT": [
            "changed", "change", "drift", "modified", "created", "deleted",
            "last 24 hours", "yesterday", "recent changes", "new resource",
            "removed", "what changed", "configuration change", "diff",
            "before and after", "history", "when was", "who changed",
        ],
        # Domain 1 — Posture & Risk Querying (broad catch-all)
        "POSTURE": [
            "risk", "exposed", "internet-facing", "internet exposed", "public",
            "vulnerable", "critical", "high severity", "production", "prod",
            "workload", "resource", "asset", "bucket", "s3", "ec2", "vpc",
            "subnet", "security group", "iam", "kms", "how many", "list all",
            "list", "count", "posture", "score", "overview", "summary", "status",
            "which", "show me", "what are", "do i have", "are there",
            "what do you know", "what information", "tell me", "give me",
            "what can you", "what data", "access to", "know about",
            "environment", "infrastructure", "cloud", "account", "connected",
            "all my", "my resources", "my findings", "my assets",
        ],
    }

    def classify(self, query: str) -> IntentType:
        """Classify a query into one of 7 intent types."""
        query_lower = query.strip().lower()

        # Fast path: detect pure greeting queries (very short, no security keywords)
        # Only classify as GENERAL if the query is ONLY a greeting phrase
        if len(query_lower) < 50:
            for pattern in GENERAL_PATTERNS:
                if query_lower == pattern or query_lower.startswith(pattern + " ") or query_lower.endswith(" " + pattern):
                    # Make sure it's not also a data query
                    data_words = ["resource", "finding", "account", "asset", "compliance",
                                  "list", "show", "what", "how", "do i", "my", "all", "data",
                                  "know", "information", "access", "tell", "give"]
                    if not any(w in query_lower for w in data_words):
                        logger.info(f"Classified as GENERAL (greeting): {query[:60]}")
                        return "GENERAL"

        # Score each intent based on keyword matches (weighted by keyword length)
        scores: dict[str, float] = {intent: 0.0 for intent in self.INTENT_KEYWORDS}
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    # Longer keywords are more specific — weight them higher
                    scores[intent] += 1 + len(keyword.split()) * 0.5

        max_score = max(scores.values())

        if max_score == 0:
            # Default: treat as posture query — retrieve full context
            logger.info(f"No keywords matched, defaulting to POSTURE: {query[:100]}")
            return "POSTURE"

        best_intent = max(scores.items(), key=lambda x: x[1])[0]
        logger.info(
            f"Classified as {best_intent} (score={scores[best_intent]:.1f}) | "
            f"all scores: { {k: round(v,1) for k,v in scores.items() if v > 0} }"
        )
        return best_intent
