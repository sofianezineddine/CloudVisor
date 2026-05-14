"""Unit tests for IAM Analyzer business logic."""

import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from app.services.iam_analyzer import (
    analyze_cross_account_trusts,
    assign_escalation_severity,
    assign_severity_from_ratio,
    compute_effective_permissions,
    compute_excess_permissions,
    compute_excess_ratio,
    compute_service_account_risk_score,
    detect_admin_mfa_issues,
    detect_dormant_identity,
    detect_overly_permissive_trust,
    discover_escalation_paths,
    generate_least_privilege_policy,
    match_known_patterns,
    store_escalation_path_in_graph,
    store_trust_in_graph,
    KNOWN_ESCALATION_PATTERNS,
)


# ─── compute_effective_permissions ────────────────────────────────────────────


class TestComputeEffectivePermissions:
    """Tests for compute_effective_permissions."""

    def test_single_allow_policy(self):
        policies = [
            {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"]}]}
        ]
        result = compute_effective_permissions(policies)
        assert result == {"s3:GetObject", "s3:PutObject"}

    def test_multiple_policies_union(self):
        policies = [
            {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject"]}]},
            {"Statement": [{"Effect": "Allow", "Action": ["ec2:DescribeInstances"]}]},
        ]
        result = compute_effective_permissions(policies)
        assert result == {"s3:GetObject", "ec2:DescribeInstances"}

    def test_explicit_deny_removes_permissions(self):
        policies = [
            {
                "Statement": [
                    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]},
                    {"Effect": "Deny", "Action": ["s3:DeleteObject"]},
                ]
            }
        ]
        result = compute_effective_permissions(policies)
        assert result == {"s3:GetObject", "s3:PutObject"}

    def test_scp_restricts_permissions(self):
        policies = [
            {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "ec2:*"]}]}
        ]
        scps = [
            {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"]}]}
        ]
        result = compute_effective_permissions(policies, scp_policies=scps)
        assert result == {"s3:GetObject", "s3:PutObject"}

    def test_permission_boundary_restricts(self):
        policies = [
            {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "iam:CreateUser"]}]}
        ]
        boundaries = [
            {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"]}]}
        ]
        result = compute_effective_permissions(policies, permission_boundaries=boundaries)
        assert result == {"s3:GetObject", "s3:PutObject"}

    def test_scp_and_boundary_combined(self):
        policies = [
            {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "ec2:*", "iam:CreateUser"]}]}
        ]
        scps = [
            {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "ec2:*"]}]}
        ]
        boundaries = [
            {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "iam:CreateUser"]}]}
        ]
        # Intersection of SCP and boundary: only s3:GetObject, s3:PutObject
        result = compute_effective_permissions(policies, scp_policies=scps, permission_boundaries=boundaries)
        assert result == {"s3:GetObject", "s3:PutObject"}

    def test_empty_policies(self):
        result = compute_effective_permissions([])
        assert result == set()

    def test_action_as_string_not_list(self):
        policies = [
            {"Statement": [{"Effect": "Allow", "Action": "s3:GetObject"}]}
        ]
        result = compute_effective_permissions(policies)
        assert result == {"s3:GetObject"}

    def test_deny_takes_precedence_over_scp_allow(self):
        policies = [
            {
                "Statement": [
                    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"]},
                    {"Effect": "Deny", "Action": ["s3:PutObject"]},
                ]
            }
        ]
        scps = [
            {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"]}]}
        ]
        result = compute_effective_permissions(policies, scp_policies=scps)
        assert result == {"s3:GetObject"}


# ─── compute_excess_permissions ───────────────────────────────────────────────


class TestComputeExcessPermissions:
    """Tests for compute_excess_permissions."""

    def test_all_permissions_used(self):
        granted = {"s3:GetObject", "s3:PutObject"}
        used = {"s3:GetObject", "s3:PutObject"}
        assert compute_excess_permissions(granted, used) == set()

    def test_some_permissions_unused(self):
        granted = {"s3:GetObject", "s3:PutObject", "s3:DeleteObject"}
        used = {"s3:GetObject"}
        assert compute_excess_permissions(granted, used) == {"s3:PutObject", "s3:DeleteObject"}

    def test_no_permissions_used(self):
        granted = {"s3:GetObject", "s3:PutObject"}
        used: set[str] = set()
        assert compute_excess_permissions(granted, used) == granted

    def test_empty_granted(self):
        granted: set[str] = set()
        used = {"s3:GetObject"}
        assert compute_excess_permissions(granted, used) == set()


# ─── compute_excess_ratio ─────────────────────────────────────────────────────


class TestComputeExcessRatio:
    """Tests for compute_excess_ratio."""

    def test_no_excess(self):
        granted = {"s3:GetObject", "s3:PutObject"}
        excess: set[str] = set()
        assert compute_excess_ratio(granted, excess) == 0.0

    def test_all_excess(self):
        granted = {"s3:GetObject", "s3:PutObject"}
        excess = {"s3:GetObject", "s3:PutObject"}
        assert compute_excess_ratio(granted, excess) == 1.0

    def test_half_excess(self):
        granted = {"s3:GetObject", "s3:PutObject"}
        excess = {"s3:PutObject"}
        assert compute_excess_ratio(granted, excess) == 0.5

    def test_empty_granted_returns_zero(self):
        granted: set[str] = set()
        excess: set[str] = set()
        assert compute_excess_ratio(granted, excess) == 0.0


# ─── assign_severity_from_ratio ───────────────────────────────────────────────


class TestAssignSeverityFromRatio:
    """Tests for assign_severity_from_ratio."""

    def test_critical_at_90_percent(self):
        assert assign_severity_from_ratio(0.9) == "CRITICAL"
        assert assign_severity_from_ratio(0.95) == "CRITICAL"
        assert assign_severity_from_ratio(1.0) == "CRITICAL"

    def test_high_at_70_percent(self):
        assert assign_severity_from_ratio(0.7) == "HIGH"
        assert assign_severity_from_ratio(0.85) == "HIGH"

    def test_medium_at_30_percent(self):
        assert assign_severity_from_ratio(0.3) == "MEDIUM"
        assert assign_severity_from_ratio(0.5) == "MEDIUM"

    def test_low_below_30_percent(self):
        assert assign_severity_from_ratio(0.0) == "LOW"
        assert assign_severity_from_ratio(0.1) == "LOW"
        assert assign_severity_from_ratio(0.29) == "LOW"


# ─── generate_least_privilege_policy ──────────────────────────────────────────


class TestGenerateLeastPrivilegePolicy:
    """Tests for generate_least_privilege_policy."""

    def test_generates_policy_with_used_permissions(self):
        used = {"s3:GetObject", "s3:PutObject", "ec2:DescribeInstances"}
        policy = generate_least_privilege_policy(used, identity_arn="arn:aws:iam::123:user/test")

        assert policy["Version"] == "2012-10-17"
        assert len(policy["Statement"]) == 2  # s3 and ec2 groups

        all_actions = []
        for stmt in policy["Statement"]:
            assert stmt["Effect"] == "Allow"
            all_actions.extend(stmt["Action"])

        assert set(all_actions) == used

    def test_empty_permissions_returns_empty_statement(self):
        policy = generate_least_privilege_policy(set())
        assert policy["Version"] == "2012-10-17"
        assert policy["Statement"] == []

    def test_policy_groups_by_service(self):
        used = {"s3:GetObject", "s3:PutObject", "ec2:DescribeInstances", "ec2:StartInstances"}
        policy = generate_least_privilege_policy(used)

        services_in_statements = set()
        for stmt in policy["Statement"]:
            for action in stmt["Action"]:
                services_in_statements.add(action.split(":")[0])

        assert services_in_statements == {"s3", "ec2"}

    def test_policy_contains_metadata(self):
        used = {"s3:GetObject"}
        policy = generate_least_privilege_policy(used, identity_arn="arn:aws:iam::123:user/test")
        assert "metadata" in policy
        assert policy["metadata"]["identity_arn"] == "arn:aws:iam::123:user/test"
        assert policy["metadata"]["permission_count"] == 1


# ─── detect_dormant_identity ──────────────────────────────────────────────────


class TestDetectDormantIdentity:
    """Tests for detect_dormant_identity."""

    def test_none_activity_is_dormant(self):
        assert detect_dormant_identity(None) is True

    def test_recent_activity_not_dormant(self):
        recent = datetime.now(timezone.utc) - timedelta(days=10)
        assert detect_dormant_identity(recent) is False

    def test_old_activity_is_dormant(self):
        old = datetime.now(timezone.utc) - timedelta(days=100)
        assert detect_dormant_identity(old) is True

    def test_exactly_at_threshold(self):
        at_threshold = datetime.now(timezone.utc) - timedelta(days=90)
        assert detect_dormant_identity(at_threshold) is True

    def test_custom_threshold(self):
        activity = datetime.now(timezone.utc) - timedelta(days=50)
        assert detect_dormant_identity(activity, lookback_days=30) is True
        assert detect_dormant_identity(activity, lookback_days=60) is False

    def test_naive_datetime_handled(self):
        # Naive datetime (no tzinfo) should still work
        old = datetime.utcnow() - timedelta(days=100)
        assert detect_dormant_identity(old) is True


# ─── detect_admin_mfa_issues ─────────────────────────────────────────────────


class TestDetectAdminMfaIssues:
    """Tests for detect_admin_mfa_issues."""

    def test_non_admin_returns_empty(self):
        findings = detect_admin_mfa_issues(is_admin=False, has_mfa=False)
        assert findings == []

    def test_admin_without_mfa_critical(self):
        findings = detect_admin_mfa_issues(is_admin=True, has_mfa=False)
        assert len(findings) >= 1
        mfa_finding = next(f for f in findings if f["issue_type"] == "admin_no_mfa")
        assert mfa_finding["severity"] == "CRITICAL"

    def test_root_without_mfa_critical(self):
        findings = detect_admin_mfa_issues(is_admin=False, has_mfa=False, is_root=True)
        assert len(findings) >= 1
        mfa_finding = next(f for f in findings if f["issue_type"] == "admin_no_mfa")
        assert mfa_finding["severity"] == "CRITICAL"

    def test_admin_daily_usage_high(self):
        recent = datetime.now(timezone.utc) - timedelta(days=2)
        findings = detect_admin_mfa_issues(
            is_admin=True, has_mfa=True, last_activity_at=recent
        )
        assert len(findings) == 1
        assert findings[0]["severity"] == "HIGH"
        assert findings[0]["issue_type"] == "admin_daily_usage"

    def test_admin_no_mfa_and_daily_usage(self):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        findings = detect_admin_mfa_issues(
            is_admin=True, has_mfa=False, last_activity_at=recent
        )
        assert len(findings) == 2
        severities = {f["severity"] for f in findings}
        assert "CRITICAL" in severities
        assert "HIGH" in severities

    def test_admin_with_mfa_no_recent_usage(self):
        old = datetime.now(timezone.utc) - timedelta(days=30)
        findings = detect_admin_mfa_issues(
            is_admin=True, has_mfa=True, last_activity_at=old
        )
        assert findings == []


# ─── compute_service_account_risk_score ───────────────────────────────────────


class TestComputeServiceAccountRiskScore:
    """Tests for compute_service_account_risk_score."""

    def test_zero_risk(self):
        score = compute_service_account_risk_score(
            permission_breadth=0, resource_scope=[], key_age_days=0
        )
        assert score == 0

    def test_max_risk(self):
        score = compute_service_account_risk_score(
            permission_breadth=100, resource_scope=["*"] * 30, key_age_days=180
        )
        assert score == 100

    def test_moderate_risk(self):
        score = compute_service_account_risk_score(
            permission_breadth=25, resource_scope=["arn:aws:s3:::bucket1"] * 10, key_age_days=45
        )
        assert 0 < score < 100

    def test_score_increases_with_breadth(self):
        low = compute_service_account_risk_score(
            permission_breadth=5, resource_scope=[], key_age_days=0
        )
        high = compute_service_account_risk_score(
            permission_breadth=50, resource_scope=[], key_age_days=0
        )
        assert high > low

    def test_score_increases_with_scope(self):
        low = compute_service_account_risk_score(
            permission_breadth=0, resource_scope=["arn:1"], key_age_days=0
        )
        high = compute_service_account_risk_score(
            permission_breadth=0, resource_scope=["arn:1"] * 20, key_age_days=0
        )
        assert high > low

    def test_score_increases_with_key_age(self):
        low = compute_service_account_risk_score(
            permission_breadth=0, resource_scope=[], key_age_days=10
        )
        high = compute_service_account_risk_score(
            permission_breadth=0, resource_scope=[], key_age_days=90
        )
        assert high > low

    def test_score_bounded_0_to_100(self):
        score = compute_service_account_risk_score(
            permission_breadth=1000, resource_scope=["*"] * 100, key_age_days=9999
        )
        assert score <= 100
        assert score >= 0


# ─── analyze_cross_account_trusts ─────────────────────────────────────────────


class TestAnalyzeCrossAccountTrusts:
    """Tests for analyze_cross_account_trusts."""

    def test_discovers_cross_account_trust(self):
        trust_policies = [
            {
                "RoleName": "CrossAccountRole",
                "RoleArn": "arn:aws:iam::111111111111:role/CrossAccountRole",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
                        "Action": "sts:AssumeRole",
                        "Condition": {"StringEquals": {"sts:ExternalId": "ext-123"}},
                    }
                ],
            }
        ]
        result = analyze_cross_account_trusts(trust_policies, source_account_id="111111111111")
        assert len(result) == 1
        trust = result[0]
        assert trust["source_account_id"] == "111111111111"
        assert trust["target_account_id"] == "222222222222"
        assert trust["trusted_principal"] == "arn:aws:iam::222222222222:root"
        assert trust["has_external_id"] is True
        assert trust["has_wildcard_principal"] is False
        assert trust["is_overly_permissive"] is False

    def test_skips_same_account_trust(self):
        trust_policies = [
            {
                "RoleName": "SameAccountRole",
                "RoleArn": "arn:aws:iam::111111111111:role/SameAccountRole",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "arn:aws:iam::111111111111:role/OtherRole"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ]
        result = analyze_cross_account_trusts(trust_policies, source_account_id="111111111111")
        assert len(result) == 0

    def test_detects_wildcard_principal(self):
        trust_policies = [
            {
                "RoleName": "WildcardRole",
                "RoleArn": "arn:aws:iam::111111111111:role/WildcardRole",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ]
        result = analyze_cross_account_trusts(trust_policies, source_account_id="111111111111")
        assert len(result) == 1
        trust = result[0]
        assert trust["has_wildcard_principal"] is True
        assert trust["is_overly_permissive"] is True
        assert trust["target_account_id"] == "*"

    def test_detects_missing_external_id(self):
        trust_policies = [
            {
                "RoleName": "NoExternalIdRole",
                "RoleArn": "arn:aws:iam::111111111111:role/NoExternalIdRole",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "arn:aws:iam::333333333333:root"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ]
        result = analyze_cross_account_trusts(trust_policies, source_account_id="111111111111")
        assert len(result) == 1
        trust = result[0]
        assert trust["has_external_id"] is False
        assert trust["is_overly_permissive"] is True

    def test_multiple_principals_in_single_statement(self):
        trust_policies = [
            {
                "RoleName": "MultiPrincipalRole",
                "RoleArn": "arn:aws:iam::111111111111:role/MultiPrincipalRole",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": [
                                "arn:aws:iam::222222222222:root",
                                "arn:aws:iam::333333333333:role/SomeRole",
                            ]
                        },
                        "Action": "sts:AssumeRole",
                        "Condition": {"StringEquals": {"sts:ExternalId": "ext-456"}},
                    }
                ],
            }
        ]
        result = analyze_cross_account_trusts(trust_policies, source_account_id="111111111111")
        assert len(result) == 2
        account_ids = {t["target_account_id"] for t in result}
        assert account_ids == {"222222222222", "333333333333"}

    def test_skips_deny_statements(self):
        trust_policies = [
            {
                "RoleName": "DenyRole",
                "RoleArn": "arn:aws:iam::111111111111:role/DenyRole",
                "Statement": [
                    {
                        "Effect": "Deny",
                        "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ]
        result = analyze_cross_account_trusts(trust_policies, source_account_id="111111111111")
        assert len(result) == 0

    def test_empty_trust_policies(self):
        result = analyze_cross_account_trusts([], source_account_id="111111111111")
        assert result == []

    def test_risk_score_higher_for_wildcard(self):
        trust_policies_wildcard = [
            {
                "RoleName": "WildcardRole",
                "RoleArn": "arn:aws:iam::111111111111:role/WildcardRole",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ]
        trust_policies_specific = [
            {
                "RoleName": "SpecificRole",
                "RoleArn": "arn:aws:iam::111111111111:role/SpecificRole",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
                        "Action": "sts:AssumeRole",
                        "Condition": {"StringEquals": {"sts:ExternalId": "ext-789"}},
                    }
                ],
            }
        ]
        wildcard_result = analyze_cross_account_trusts(trust_policies_wildcard, "111111111111")
        specific_result = analyze_cross_account_trusts(trust_policies_specific, "111111111111")
        assert wildcard_result[0]["risk_score"] > specific_result[0]["risk_score"]


# ─── detect_overly_permissive_trust ───────────────────────────────────────────


class TestDetectOverlyPermissiveTrust:
    """Tests for detect_overly_permissive_trust."""

    def test_wildcard_principal_is_permissive(self):
        assert detect_overly_permissive_trust("*", {}) is True

    def test_missing_external_id_is_permissive(self):
        assert detect_overly_permissive_trust(
            "arn:aws:iam::222222222222:root", {}
        ) is True

    def test_with_external_id_not_permissive(self):
        conditions = {"StringEquals": {"sts:ExternalId": "my-external-id"}}
        assert detect_overly_permissive_trust(
            "arn:aws:iam::222222222222:root", conditions
        ) is False

    def test_external_id_in_string_like(self):
        conditions = {"StringLike": {"sts:ExternalId": "ext-*"}}
        assert detect_overly_permissive_trust(
            "arn:aws:iam::222222222222:root", conditions
        ) is False

    def test_wildcard_principal_with_external_id_still_permissive(self):
        # Wildcard principal is always permissive regardless of conditions
        conditions = {"StringEquals": {"sts:ExternalId": "ext-123"}}
        assert detect_overly_permissive_trust("*", conditions) is True

    def test_other_conditions_without_external_id_still_permissive(self):
        conditions = {"StringEquals": {"aws:PrincipalOrgID": "o-12345"}}
        assert detect_overly_permissive_trust(
            "arn:aws:iam::222222222222:root", conditions
        ) is True


# ─── store_trust_in_graph ─────────────────────────────────────────────────────


class TestStoreTrustInGraph:
    """Tests for store_trust_in_graph."""

    @pytest.mark.asyncio
    async def test_stores_trust_edge(self):
        """Test that store_trust_in_graph calls graph_client.query with correct params."""
        from unittest.mock import AsyncMock

        mock_graph_client = AsyncMock()
        mock_graph_client.query.return_value = [{"r": {"type": "TRUSTS"}}]

        trust_rel = {
            "source_account_id": "111111111111",
            "target_account_id": "222222222222",
            "trusted_principal": "arn:aws:iam::222222222222:root",
            "conditions": {"StringEquals": {"sts:ExternalId": "ext-123"}},
            "risk_score": 10,
            "is_overly_permissive": False,
            "has_external_id": True,
            "has_wildcard_principal": False,
            "role_arn": "arn:aws:iam::111111111111:role/TestRole",
        }

        result = await store_trust_in_graph(
            graph_client=mock_graph_client,
            trust_relationship=trust_rel,
            organization_id="org-123",
        )

        mock_graph_client.query.assert_called_once()
        call_kwargs = mock_graph_client.query.call_args
        assert "MERGE" in call_kwargs.kwargs.get("cypher", call_kwargs[1].get("cypher", ""))
        params = call_kwargs.kwargs.get("parameters", call_kwargs[1].get("parameters", {}))
        assert params["source_account"] == "111111111111"
        assert params["target_account"] == "222222222222"
        assert params["org_id"] == "org-123"
        assert params["risk_score"] == 10

    @pytest.mark.asyncio
    async def test_stores_overly_permissive_trust(self):
        """Test storing an overly permissive trust relationship."""
        from unittest.mock import AsyncMock

        mock_graph_client = AsyncMock()
        mock_graph_client.query.return_value = [{"r": {"type": "TRUSTS"}}]

        trust_rel = {
            "source_account_id": "111111111111",
            "target_account_id": "*",
            "trusted_principal": "*",
            "conditions": {},
            "risk_score": 85,
            "is_overly_permissive": True,
            "has_external_id": False,
            "has_wildcard_principal": True,
            "role_arn": "arn:aws:iam::111111111111:role/WildcardRole",
        }

        result = await store_trust_in_graph(
            graph_client=mock_graph_client,
            trust_relationship=trust_rel,
            organization_id="org-456",
        )

        mock_graph_client.query.assert_called_once()
        call_kwargs = mock_graph_client.query.call_args
        params = call_kwargs.kwargs.get("parameters", call_kwargs[1].get("parameters", {}))
        assert params["is_overly_permissive"] is True
        assert params["has_wildcard_principal"] is True
        assert params["risk_score"] == 85


# ─── match_known_patterns ─────────────────────────────────────────────────────


class TestMatchKnownPatterns:
    """Tests for match_known_patterns."""

    def test_matches_create_role_attach_policy_pattern(self):
        path_details = [
            {"permission": "iam:CreateRole", "identity": "user1", "action": "create", "target": "role1"},
            {"permission": "iam:AttachRolePolicy", "identity": "role1", "action": "attach", "target": "admin"},
        ]
        result = match_known_patterns(path_details)
        assert 0 in result  # Pattern index 0: ("iam:CreateRole", "iam:AttachRolePolicy")

    def test_matches_pass_role_lambda_pattern(self):
        path_details = [
            {"permission": "iam:PassRole", "identity": "user1", "action": "pass", "target": "lambda_role"},
            {"permission": "lambda:CreateFunction", "identity": "lambda_role", "action": "create", "target": "admin"},
        ]
        result = match_known_patterns(path_details)
        assert 1 in result  # Pattern index 1: ("iam:PassRole", "lambda:CreateFunction")

    def test_matches_single_permission_pattern(self):
        path_details = [
            {"permission": "sts:AssumeRole", "identity": "user1", "action": "assume", "target": "admin"},
        ]
        result = match_known_patterns(path_details)
        assert 2 in result  # Pattern index 2: ("sts:AssumeRole",)

    def test_matches_create_access_key_pattern(self):
        path_details = [
            {"permission": "iam:CreateAccessKey", "identity": "user1", "action": "create", "target": "admin"},
        ]
        result = match_known_patterns(path_details)
        assert 4 in result  # Pattern index 4: ("iam:CreateAccessKey",)

    def test_matches_update_login_profile_pattern(self):
        path_details = [
            {"permission": "iam:UpdateLoginProfile", "identity": "user1", "action": "update", "target": "admin"},
        ]
        result = match_known_patterns(path_details)
        assert 5 in result  # Pattern index 5: ("iam:UpdateLoginProfile",)

    def test_no_match_for_unrelated_permissions(self):
        path_details = [
            {"permission": "s3:GetObject", "identity": "user1", "action": "get", "target": "bucket"},
            {"permission": "s3:PutObject", "identity": "bucket", "action": "put", "target": "admin"},
        ]
        result = match_known_patterns(path_details)
        assert result == []

    def test_empty_path_details(self):
        result = match_known_patterns([])
        assert result == []

    def test_multiple_patterns_matched(self):
        # Path that contains permissions matching multiple patterns
        path_details = [
            {"permission": "iam:CreateRole", "identity": "user1", "action": "create", "target": "role1"},
            {"permission": "iam:AttachRolePolicy", "identity": "role1", "action": "attach", "target": "role2"},
            {"permission": "sts:AssumeRole", "identity": "role2", "action": "assume", "target": "admin"},
        ]
        result = match_known_patterns(path_details)
        assert 0 in result  # ("iam:CreateRole", "iam:AttachRolePolicy")
        assert 2 in result  # ("sts:AssumeRole",)

    def test_partial_pattern_not_matched(self):
        # Only one permission from a two-permission pattern
        path_details = [
            {"permission": "iam:CreateRole", "identity": "user1", "action": "create", "target": "role1"},
        ]
        result = match_known_patterns(path_details)
        # Pattern 0 requires BOTH iam:CreateRole AND iam:AttachRolePolicy
        assert 0 not in result


# ─── assign_escalation_severity ───────────────────────────────────────────────


class TestAssignEscalationSeverity:
    """Tests for assign_escalation_severity."""

    def test_critical_for_short_path_to_admin(self):
        # Fewer than 3 hops to admin (level >= 9)
        assert assign_escalation_severity(1, 10) == "CRITICAL"
        assert assign_escalation_severity(2, 9) == "CRITICAL"

    def test_high_for_3_4_hops_to_admin(self):
        assert assign_escalation_severity(3, 10) == "HIGH"
        assert assign_escalation_severity(4, 9) == "HIGH"

    def test_medium_for_5_6_hops_to_admin(self):
        assert assign_escalation_severity(5, 10) == "MEDIUM"
        assert assign_escalation_severity(6, 9) == "MEDIUM"

    def test_low_for_long_path_to_admin(self):
        assert assign_escalation_severity(7, 10) == "LOW"
        assert assign_escalation_severity(10, 10) == "LOW"

    def test_low_for_non_admin_target(self):
        # Non-admin targets (level < 9) are always LOW
        assert assign_escalation_severity(1, 5) == "LOW"
        assert assign_escalation_severity(1, 8) == "LOW"
        assert assign_escalation_severity(2, 3) == "LOW"

    def test_string_label_admin(self):
        assert assign_escalation_severity(1, "admin") == "CRITICAL"
        assert assign_escalation_severity(3, "admin") == "HIGH"
        assert assign_escalation_severity(5, "admin") == "MEDIUM"
        assert assign_escalation_severity(7, "admin") == "LOW"

    def test_string_label_power_user(self):
        # power_user maps to level 7, which is < 9, so always LOW
        assert assign_escalation_severity(1, "power_user") == "LOW"

    def test_string_label_read_only(self):
        # read_only maps to level 3, which is < 9, so always LOW
        assert assign_escalation_severity(1, "read_only") == "LOW"

    def test_zero_hops_to_admin(self):
        # Edge case: 0 hops (direct access) to admin
        assert assign_escalation_severity(0, 10) == "CRITICAL"


# ─── discover_escalation_paths ────────────────────────────────────────────────


class TestDiscoverEscalationPaths:
    """Tests for discover_escalation_paths."""

    @pytest.mark.asyncio
    async def test_discovers_paths_from_graph(self):
        """Test that discover_escalation_paths processes graph results correctly."""
        from unittest.mock import AsyncMock

        mock_graph_client = AsyncMock()
        mock_graph_client.query.return_value = [
            {
                "path": {
                    "nodes": [
                        {"identity_arn": "arn:aws:iam::123:user/dev", "id": "node1"},
                        {"identity_arn": "arn:aws:iam::123:role/admin", "id": "node2"},
                    ],
                    "relationships": [
                        {"permission": "sts:AssumeRole", "type": "CAN_ASSUME", "action": "assume"},
                    ],
                },
                "hops": 1,
                "target_level": 10,
            }
        ]

        result = await discover_escalation_paths(
            graph_client=mock_graph_client,
            organization_id="org-123",
        )

        assert len(result) == 1
        path = result[0]
        assert path["source_identity"] == "arn:aws:iam::123:user/dev"
        assert path["target_identity"] == "arn:aws:iam::123:role/admin"
        assert path["path_hops"] == 1
        assert path["severity"] == "CRITICAL"
        assert path["target_privilege_level"] == "admin"
        assert 2 in path["pattern_ids"]  # sts:AssumeRole pattern

    @pytest.mark.asyncio
    async def test_empty_graph_results(self):
        """Test that empty graph results return empty list."""
        from unittest.mock import AsyncMock

        mock_graph_client = AsyncMock()
        mock_graph_client.query.return_value = []

        result = await discover_escalation_paths(
            graph_client=mock_graph_client,
            organization_id="org-123",
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_skips_paths_with_insufficient_nodes(self):
        """Test that paths with fewer than 2 nodes are skipped."""
        from unittest.mock import AsyncMock

        mock_graph_client = AsyncMock()
        mock_graph_client.query.return_value = [
            {
                "path": {
                    "nodes": [{"identity_arn": "arn:aws:iam::123:user/dev"}],
                    "relationships": [],
                },
                "hops": 0,
                "target_level": 10,
            }
        ]

        result = await discover_escalation_paths(
            graph_client=mock_graph_client,
            organization_id="org-123",
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_raises_on_graph_error(self):
        """Test that graph errors are propagated."""
        from unittest.mock import AsyncMock

        from app.core.graph_client import GraphClientError

        mock_graph_client = AsyncMock()
        mock_graph_client.query.side_effect = GraphClientError("Connection failed")

        with pytest.raises(GraphClientError):
            await discover_escalation_paths(
                graph_client=mock_graph_client,
                organization_id="org-123",
            )


# ─── store_escalation_path_in_graph ───────────────────────────────────────────


class TestStoreEscalationPathInGraph:
    """Tests for store_escalation_path_in_graph."""

    @pytest.mark.asyncio
    async def test_stores_escalation_path(self):
        """Test that store_escalation_path_in_graph calls graph_client.query correctly."""
        from unittest.mock import AsyncMock

        mock_graph_client = AsyncMock()
        mock_graph_client.query.return_value = [{"r": {"type": "ESCALATES_TO"}}]

        escalation_path = {
            "source_identity": "arn:aws:iam::123:user/dev",
            "target_identity": "arn:aws:iam::123:role/admin",
            "path_hops": 2,
            "path_details": [
                {"identity": "user/dev", "permission": "iam:PassRole", "action": "pass", "target": "role/lambda"},
                {"identity": "role/lambda", "permission": "lambda:CreateFunction", "action": "create", "target": "role/admin"},
            ],
            "severity": "CRITICAL",
            "pattern_ids": [1],
            "target_privilege_level": "admin",
        }

        result = await store_escalation_path_in_graph(
            graph_client=mock_graph_client,
            escalation_path=escalation_path,
            organization_id="org-123",
        )

        mock_graph_client.query.assert_called_once()
        call_kwargs = mock_graph_client.query.call_args
        cypher = call_kwargs.kwargs.get("cypher", call_kwargs[1].get("cypher", ""))
        params = call_kwargs.kwargs.get("parameters", call_kwargs[1].get("parameters", {}))

        assert "MERGE" in cypher
        assert "ESCALATES_TO" in cypher
        assert params["source_identity"] == "arn:aws:iam::123:user/dev"
        assert params["target_identity"] == "arn:aws:iam::123:role/admin"
        assert params["path_hops"] == 2
        assert params["severity"] == "CRITICAL"
        assert params["org_id"] == "org-123"

    @pytest.mark.asyncio
    async def test_raises_on_graph_error(self):
        """Test that graph errors are propagated when storing."""
        from unittest.mock import AsyncMock

        from app.core.graph_client import GraphClientError

        mock_graph_client = AsyncMock()
        mock_graph_client.query.side_effect = GraphClientError("Write failed")

        escalation_path = {
            "source_identity": "arn:aws:iam::123:user/dev",
            "target_identity": "arn:aws:iam::123:role/admin",
            "path_hops": 1,
            "path_details": [],
            "severity": "CRITICAL",
            "pattern_ids": [],
            "target_privilege_level": "admin",
        }

        with pytest.raises(GraphClientError):
            await store_escalation_path_in_graph(
                graph_client=mock_graph_client,
                escalation_path=escalation_path,
                organization_id="org-123",
            )
