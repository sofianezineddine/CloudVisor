"""Lightweight query classification to decide what context (if any) the LLM needs.

This is the heart of the refactored copilot: instead of dumping ALL data into every
prompt and hoping the model picks the right bits, we classify the query first and
only fetch the minimum context required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class QueryType(str, Enum):
    """Coarse classification of what the user wants."""

    SMALL_TALK = "SMALL_TALK"        # "hi", "thanks", "ok" — no data needed
    META = "META"                    # "what can you do" — capabilities only
    COUNT = "COUNT"                  # "how many X do I have"
    LIST = "LIST"                    # "show me my X", "list X"
    POSTURE = "POSTURE"              # "what's my security score", "overall posture"
    FINDINGS = "FINDINGS"            # "what findings / issues / vulnerabilities"
    ASSETS = "ASSETS"                # "what resources / ec2 / s3"
    COMPLIANCE = "COMPLIANCE"        # "compliance / gdpr / hipaa / soc2"
    REMEDIATION = "REMEDIATION"      # "how do I fix"
    ACCOUNTS = "ACCOUNTS"            # "what accounts do I have connected"
    GENERAL = "GENERAL"              # anything else — give it broad context


@dataclass
class QueryClassification:
    """Result of classifying a user query."""

    query_type: QueryType
    needs_data: bool                 # whether to retrieve any backend data at all
    needed_sources: list[str]        # which retriever methods to call


# ── Regex patterns keyed to coarse intents ────────────────────────────────────
_GREETINGS = {
    "hi", "hello", "hey", "yo", "sup", "howdy", "greetings",
    "good morning", "good afternoon", "good evening", "hiya",
}
_SMALL_TALK = {
    "thanks", "thank you", "ty", "ok", "okay", "got it", "cool",
    "bye", "goodbye", "see you", "nice", "great", "awesome",
}
_META_PATTERNS = re.compile(
    r"^(what|who)\s+(can|are)\s+you|"
    r"^(what do you do)|"
    r"^(tell me about yourself)|"
    r"^(capabilities|your capabilities)|"
    r"^(help)$|"
    r"^(what is cloudvisor)",
    re.IGNORECASE,
)
_COUNT_PATTERNS = re.compile(
    r"\bhow many\b|\bnumber of\b|\bcount of\b|\btotal\b",
    re.IGNORECASE,
)
_LIST_PATTERNS = re.compile(
    r"\blist\b|\bshow me\b|\bshow all\b|\bwhat are all\b|\bgive me all\b",
    re.IGNORECASE,
)
_POSTURE_PATTERNS = re.compile(
    r"\bposture\b|\bsecurity score\b|\boverall (security|risk)\b|"
    r"\bhow secure\b|\brisk level\b|\bsecurity state\b",
    re.IGNORECASE,
)
_FINDING_PATTERNS = re.compile(
    r"\bfinding(s)?\b|\bissue(s)?\b|\bvulnerabilit(y|ies)\b|"
    r"\balert(s)?\b|\brisk(s)?\b|\bmisconfig\w*\b|\bthreat(s)?\b",
    re.IGNORECASE,
)
_ASSET_PATTERNS = re.compile(
    r"\bresource(s)?\b|\basset(s)?\b|\bec2\b|\bs3\b|\brds\b|"
    r"\blambda\b|\bvpc(s)?\b|\biam\b|\bkms\b|\bbucket(s)?\b|"
    r"\binstance(s)?\b|\bvolume(s)?\b|\bsecurity group(s)?\b",
    re.IGNORECASE,
)
_COMPLIANCE_PATTERNS = re.compile(
    r"\bcompliance\b|\bcompliant\b|\bgdpr\b|\bhipaa\b|\bpci[\-\s]?dss\b|"
    r"\bsoc[\-\s]?2\b|\bnist\b|\biso\s*27001\b|\bframework(s)?\b|"
    r"\baudit\b|\bcontrol(s)?\b",
    re.IGNORECASE,
)
_REMEDIATION_PATTERNS = re.compile(
    r"\bhow (do|can|to) (i|we|you) fix\b|\bremediate\b|\bremediation\b|"
    r"\bhow to enable\b|\bhow to disable\b|\bfix (this|that|it)\b|"
    r"\btemplate\b|\bterraform\b|\bcli command\b",
    re.IGNORECASE,
)
_ACCOUNT_PATTERNS = re.compile(
    r"\b(cloud|connected)?\s*account(s)?\b|\bprovider(s)?\b|"
    r"\b(aws|azure|gcp|oci)\s+account\b|\borganization\b",
    re.IGNORECASE,
)


def classify_query(query: str, conversation_history: list[dict] | None = None) -> QueryClassification:
    """
    Classify a user query into one of the QueryType categories.
    Returns the minimum data sources needed to answer it well.
    
    Uses conversation_history to resolve ambiguous references like
    "list them", "show me more", "tell me about those".
    """
    q = query.strip().lower()
    clean = q.rstrip("!.,?")

    # ── Small talk / greetings — no data needed ──
    if clean in _GREETINGS or clean in _SMALL_TALK:
        return QueryClassification(QueryType.SMALL_TALK, needs_data=False, needed_sources=[])

    # Short messages (≤3 words) containing a greeting/small-talk token
    if len(clean.split()) <= 3 and any(g in clean for g in _GREETINGS | _SMALL_TALK):
        return QueryClassification(QueryType.SMALL_TALK, needs_data=False, needed_sources=[])

    # ── Meta questions about the assistant itself ──
    if _META_PATTERNS.search(query):
        return QueryClassification(QueryType.META, needs_data=False, needed_sources=[])

    # ── Ambiguous short queries — use conversation context to resolve ──
    if _is_ambiguous_reference(q) and conversation_history:
        resolved_type = _resolve_from_history(conversation_history)
        if resolved_type:
            return resolved_type

    # ── Remediation — specific and narrow ──
    if _REMEDIATION_PATTERNS.search(query):
        return QueryClassification(
            QueryType.REMEDIATION,
            needs_data=True,
            needed_sources=["findings", "rules"],
        )

    # ── Compliance ──
    if _COMPLIANCE_PATTERNS.search(query):
        return QueryClassification(
            QueryType.COMPLIANCE,
            needs_data=True,
            needed_sources=["compliance_results", "frameworks"],
        )

    # ── Accounts ──
    if _ACCOUNT_PATTERNS.search(query) and not _FINDING_PATTERNS.search(query):
        return QueryClassification(
            QueryType.ACCOUNTS,
            needs_data=True,
            needed_sources=["cloud_accounts"],
        )

    # ── Posture ──
    if _POSTURE_PATTERNS.search(query):
        return QueryClassification(
            QueryType.POSTURE,
            needs_data=True,
            needed_sources=["posture_snapshots", "cloud_accounts", "findings"],
        )

    # ── Findings ──
    if _FINDING_PATTERNS.search(query):
        return QueryClassification(
            QueryType.FINDINGS,
            needs_data=True,
            needed_sources=["findings", "cloud_accounts"],
        )

    # ── Assets ──
    if _ASSET_PATTERNS.search(query):
        return QueryClassification(
            QueryType.ASSETS,
            needs_data=True,
            needed_sources=["assets", "cloud_accounts"],
        )

    # ── Count / list without a specific subject — default to broad ──
    if _COUNT_PATTERNS.search(query) or _LIST_PATTERNS.search(query):
        return QueryClassification(
            QueryType.LIST if _LIST_PATTERNS.search(query) else QueryType.COUNT,
            needs_data=True,
            needed_sources=["cloud_accounts", "findings", "assets"],
        )

    # ── Fallback — give the model a modest amount of context ──
    return QueryClassification(
        QueryType.GENERAL,
        needs_data=True,
        needed_sources=["cloud_accounts", "posture_snapshots", "findings"],
    )


# ── Ambiguity resolution helpers ─────────────────────────────────────────────

_AMBIGUOUS_PATTERNS = re.compile(
    r"^(list|show|tell me|more|details|explain|what about)\s*(them|those|it|these|more)?[.!?]*$",
    re.IGNORECASE,
)


def _is_ambiguous_reference(query: str) -> bool:
    """Detect short queries that reference something from prior context."""
    return bool(_AMBIGUOUS_PATTERNS.match(query)) or query in (
        "list them", "show them", "show me", "tell me more",
        "more details", "explain", "go on", "continue",
    )


def _resolve_from_history(history: list[dict]) -> QueryClassification | None:
    """
    Look at the last few messages to figure out what 'them/those/it' refers to.
    Returns the appropriate classification or None if we can't determine.
    """
    # Look at the last assistant message and the last user message before that
    recent_text = ""
    for msg in reversed(history[-4:]):
        recent_text += " " + str(msg.get("content", ""))

    recent_lower = recent_text.lower()

    # Check what topic was being discussed
    if _ASSET_PATTERNS.search(recent_lower) or "resource" in recent_lower:
        return QueryClassification(
            QueryType.ASSETS,
            needs_data=True,
            needed_sources=["assets", "cloud_accounts"],
        )

    if _FINDING_PATTERNS.search(recent_lower):
        return QueryClassification(
            QueryType.FINDINGS,
            needs_data=True,
            needed_sources=["findings", "cloud_accounts"],
        )

    if _COMPLIANCE_PATTERNS.search(recent_lower):
        return QueryClassification(
            QueryType.COMPLIANCE,
            needs_data=True,
            needed_sources=["compliance_results", "frameworks"],
        )

    if _ACCOUNT_PATTERNS.search(recent_lower):
        return QueryClassification(
            QueryType.ACCOUNTS,
            needs_data=True,
            needed_sources=["cloud_accounts"],
        )

    # Can't determine — fall back to general
    return None
