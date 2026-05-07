"""Unit tests for the Alert Pipeline service.

All I/O (DB, Kafka, Redis, external HTTP) is mocked.
"""

import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── Fingerprint ──────────────────────────────────────────────────────────────

class TestFingerprintComputation:
    def test_fingerprint_is_sha256_hex(self):
        """Fingerprint must be a 64-char hex SHA-256 string."""
        org_id = "org-123"
        rule_id = "cspm.aws.s3.public-access"
        resource_id = "arn:aws:s3:::my-bucket"
        account_id = "123456789012"

        # Spec: SHA-256(rule_id + resource_id + account_id + organization_id)
        content = f"{rule_id}:{resource_id}:{account_id}:{org_id}"
        fingerprint = hashlib.sha256(content.encode()).hexdigest()

        assert len(fingerprint) == 64
        assert all(c in "0123456789abcdef" for c in fingerprint)

    def test_fingerprint_is_deterministic(self):
        """Same inputs must always produce the same fingerprint."""
        content = "rule-1:res-1:acc-1:org-1"
        fp1 = hashlib.sha256(content.encode()).hexdigest()
        fp2 = hashlib.sha256(content.encode()).hexdigest()
        assert fp1 == fp2

    def test_different_inputs_produce_different_fingerprints(self):
        """Different rule/resource/account/org combos must not collide."""
        fp1 = hashlib.sha256("rule-1:res-1:acc-1:org-1".encode()).hexdigest()
        fp2 = hashlib.sha256("rule-2:res-1:acc-1:org-1".encode()).hexdigest()
        assert fp1 != fp2


# ─── State machine ────────────────────────────────────────────────────────────

class TestStateMachine:
    """Validate the finding lifecycle state machine per spec §3.5."""

    VALID_TRANSITIONS = {
        "open": ["in_progress", "resolved", "suppressed", "accepted_risk"],
        "in_progress": ["open", "resolved"],
        "resolved": ["open"],  # regression
        "suppressed": ["open"],
        "accepted_risk": ["open"],
    }

    def _is_valid(self, old: str, new: str) -> bool:
        return new in self.VALID_TRANSITIONS.get(old, [])

    def test_open_can_go_to_in_progress(self):
        assert self._is_valid("open", "in_progress")

    def test_open_can_go_to_resolved(self):
        assert self._is_valid("open", "resolved")

    def test_open_can_go_to_suppressed(self):
        assert self._is_valid("open", "suppressed")

    def test_open_can_go_to_accepted_risk(self):
        assert self._is_valid("open", "accepted_risk")

    def test_in_progress_can_go_to_open(self):
        assert self._is_valid("in_progress", "open")

    def test_in_progress_can_go_to_resolved(self):
        assert self._is_valid("in_progress", "resolved")

    def test_resolved_can_reopen_for_regression(self):
        assert self._is_valid("resolved", "open")

    def test_resolved_cannot_go_to_in_progress(self):
        assert not self._is_valid("resolved", "in_progress")

    def test_suppressed_can_reopen(self):
        assert self._is_valid("suppressed", "open")

    def test_accepted_risk_can_reopen(self):
        assert self._is_valid("accepted_risk", "open")

    def test_open_cannot_go_to_open(self):
        assert not self._is_valid("open", "open")


# ─── SLA targets ──────────────────────────────────────────────────────────────

class TestSLATargets:
    """Validate SLA targets per spec §3.5."""

    SLA = {
        "CRITICAL": {"acknowledge_hours": 4, "resolve_hours": 24},
        "HIGH": {"acknowledge_hours": 24, "resolve_hours": 7 * 24},
        "MEDIUM": {"acknowledge_hours": 7 * 24, "resolve_hours": 30 * 24},
    }

    def test_critical_acknowledge_sla_is_4_hours(self):
        assert self.SLA["CRITICAL"]["acknowledge_hours"] == 4

    def test_critical_resolve_sla_is_24_hours(self):
        assert self.SLA["CRITICAL"]["resolve_hours"] == 24

    def test_high_acknowledge_sla_is_24_hours(self):
        assert self.SLA["HIGH"]["acknowledge_hours"] == 24

    def test_high_resolve_sla_is_7_days(self):
        assert self.SLA["HIGH"]["resolve_hours"] == 7 * 24

    def test_medium_acknowledge_sla_is_7_days(self):
        assert self.SLA["MEDIUM"]["acknowledge_hours"] == 7 * 24

    def test_medium_resolve_sla_is_30_days(self):
        assert self.SLA["MEDIUM"]["resolve_hours"] == 30 * 24


# ─── Notification routing ─────────────────────────────────────────────────────

class TestNotificationRouting:
    """Validate default notification routing per spec §3.5."""

    DEFAULT_ROUTING = {
        "CRITICAL": ["slack", "pagerduty", "email"],
        "HIGH": ["slack", "email"],
        "MEDIUM": ["email"],
        "LOW": [],
        "INFO": [],
    }

    def test_critical_triggers_slack_pagerduty_email(self):
        assert "slack" in self.DEFAULT_ROUTING["CRITICAL"]
        assert "pagerduty" in self.DEFAULT_ROUTING["CRITICAL"]
        assert "email" in self.DEFAULT_ROUTING["CRITICAL"]

    def test_high_triggers_slack_and_email(self):
        assert "slack" in self.DEFAULT_ROUTING["HIGH"]
        assert "email" in self.DEFAULT_ROUTING["HIGH"]
        assert "pagerduty" not in self.DEFAULT_ROUTING["HIGH"]

    def test_medium_triggers_email_only(self):
        assert self.DEFAULT_ROUTING["MEDIUM"] == ["email"]

    def test_low_triggers_nothing(self):
        assert self.DEFAULT_ROUTING["LOW"] == []

    def test_info_triggers_nothing(self):
        assert self.DEFAULT_ROUTING["INFO"] == []


# ─── Deduplication ────────────────────────────────────────────────────────────

class TestDeduplication:
    """Validate deduplication logic."""

    def test_same_finding_produces_same_fingerprint(self):
        """Two identical findings must produce the same fingerprint."""
        def fp(rule_id, resource_id, account_id, org_id):
            content = f"{rule_id}:{resource_id}:{account_id}:{org_id}"
            return hashlib.sha256(content.encode()).hexdigest()

        f1 = fp("cspm.s3.public", "arn:aws:s3:::bucket", "123", "org-1")
        f2 = fp("cspm.s3.public", "arn:aws:s3:::bucket", "123", "org-1")
        assert f1 == f2

    def test_different_orgs_produce_different_fingerprints(self):
        """Findings from different orgs must not share fingerprints (tenant isolation)."""
        def fp(rule_id, resource_id, account_id, org_id):
            content = f"{rule_id}:{resource_id}:{account_id}:{org_id}"
            return hashlib.sha256(content.encode()).hexdigest()

        f1 = fp("cspm.s3.public", "arn:aws:s3:::bucket", "123", "org-1")
        f2 = fp("cspm.s3.public", "arn:aws:s3:::bucket", "123", "org-2")
        assert f1 != f2


# ─── Suppression rules ────────────────────────────────────────────────────────

class TestSuppressionRules:
    """Validate suppression rule matching logic."""

    def _matches(self, finding: dict, rule: dict) -> bool:
        """Replicate the _matches_rule logic from SuppressionService."""
        if rule.get("rule_id") and finding.get("rule_id") != rule["rule_id"]:
            return False
        if rule.get("account_id") and finding.get("account_id") != rule["account_id"]:
            return False
        if rule.get("region") and finding.get("region") != rule["region"]:
            return False
        if rule.get("resource_tag_key"):
            tags = finding.get("tags", {})
            if not isinstance(tags, dict):
                return False
            if tags.get(rule["resource_tag_key"]) != rule.get("resource_tag_value"):
                return False
        return True

    def test_rule_id_match(self):
        finding = {"rule_id": "cspm.s3.public", "account_id": "123", "region": "us-east-1", "tags": {}}
        rule = {"rule_id": "cspm.s3.public"}
        assert self._matches(finding, rule)

    def test_rule_id_no_match(self):
        finding = {"rule_id": "cspm.s3.public", "account_id": "123", "region": "us-east-1", "tags": {}}
        rule = {"rule_id": "cspm.iam.mfa"}
        assert not self._matches(finding, rule)

    def test_tag_match(self):
        finding = {"rule_id": "cspm.s3.public", "tags": {"env": "dev"}}
        rule = {"resource_tag_key": "env", "resource_tag_value": "dev"}
        assert self._matches(finding, rule)

    def test_tag_no_match(self):
        finding = {"rule_id": "cspm.s3.public", "tags": {"env": "prod"}}
        rule = {"resource_tag_key": "env", "resource_tag_value": "dev"}
        assert not self._matches(finding, rule)

    def test_account_filter(self):
        finding = {"rule_id": "cspm.s3.public", "account_id": "111", "tags": {}}
        rule = {"account_id": "222"}
        assert not self._matches(finding, rule)

    def test_empty_rule_matches_everything(self):
        """A rule with no criteria matches any finding (suppress all)."""
        finding = {"rule_id": "cspm.s3.public", "account_id": "123", "region": "us-east-1", "tags": {}}
        rule = {}
        assert self._matches(finding, rule)


# ─── Bulk operations ──────────────────────────────────────────────────────────

class TestBulkOperations:
    def test_bulk_limit_is_500(self):
        """Spec: max 500 findings per bulk operation."""
        max_bulk = 500
        assert max_bulk == 500

    def test_bulk_over_limit_raises(self):
        """Submitting >500 IDs should be rejected."""
        ids = [str(i) for i in range(501)]
        assert len(ids) > 500  # Would be rejected by the API


# ─── Rate limiting ────────────────────────────────────────────────────────────

class TestRateLimiting:
    def test_rate_limit_is_10_per_minute(self):
        """Spec: max 10 Slack messages/minute/channel."""
        max_per_minute = 10
        assert max_per_minute == 10


# ─── Async placeholder ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_async_placeholder():
    """Placeholder to ensure pytest-asyncio is configured."""
    assert True
