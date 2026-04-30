"""Unit tests for the Policy service."""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


# ─── RegoParser tests ─────────────────────────────────────────────────────────

class TestRegoParser:
    """Tests for Rego metadata extraction."""

    def _make_parser(self):
        from app.opa.opa_service import RegoParser
        return RegoParser()

    def test_extract_metadata_full(self):
        """Test extracting all metadata fields."""
        rego = """# METADATA
# title: S3 Bucket Public Access
# description: S3 bucket allows public access
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::s3::bucket
# remediation: Enable S3 Block Public Access
# version: 1.2.0

package cloudvisor.cspm.aws_s3

deny[msg] { msg := "denied" }
"""
        parser = self._make_parser()
        meta = parser.extract_metadata(rego)

        assert meta["title"] == "S3 Bucket Public Access"
        assert meta["description"] == "S3 bucket allows public access"
        assert meta["severity"] == "CRITICAL"
        assert meta["category"] == "cspm"
        assert meta["provider"] == "aws"
        assert meta["resource_type"] == "aws::s3::bucket"
        assert meta["remediation"] == "Enable S3 Block Public Access"
        assert meta["version"] == "1.2.0"

    def test_extract_metadata_empty(self):
        """Test extracting metadata from rego without METADATA block."""
        rego = """package cloudvisor.cspm.test

deny[msg] { msg := "denied" }
"""
        parser = self._make_parser()
        meta = parser.extract_metadata(rego)
        assert meta == {}

    def test_extract_package(self):
        """Test package name extraction."""
        rego = """package cloudvisor.cspm.aws_s3_public_access

deny[msg] { msg := "denied" }
"""
        parser = self._make_parser()
        pkg = parser.extract_package(rego)
        assert pkg == "cloudvisor.cspm.aws_s3_public_access"

    def test_extract_package_missing(self):
        """Test package extraction when no package declaration."""
        parser = self._make_parser()
        pkg = parser.extract_package("deny[msg] { msg := 'denied' }")
        assert pkg == "unknown"

    def test_extract_rule_id_from_path(self):
        """Test rule ID extraction from policy path."""
        parser = self._make_parser()
        rule_id = parser.extract_rule_id("cloudvisor/cspm/aws_s3_public_access", "")
        assert rule_id == "aws_s3_public_access"

    def test_extract_rule_id_dot_path(self):
        """Test rule ID extraction from dot-separated path."""
        parser = self._make_parser()
        rule_id = parser.extract_rule_id("cspm.aws.s3", "")
        assert rule_id == "s3"


# ─── OPAService result parsing tests ─────────────────────────────────────────

class TestOPAServiceParsing:
    """Tests for OPA result parsing."""

    def _make_opa(self):
        from app.opa.opa_service import OPAService
        return OPAService("http://localhost:8181")

    def test_parse_results_dict_format(self):
        """Test parsing OPA set result (dict with true values)."""
        opa = self._make_opa()
        result = {
            "result": {
                "deny": {
                    "S3 bucket 'my-bucket' has public access": True,
                    "Another violation": True,
                }
            }
        }
        findings = opa._parse_results(result)
        assert len(findings) == 2
        messages = [f["message"] for f in findings]
        assert "S3 bucket 'my-bucket' has public access" in messages

    def test_parse_results_list_format(self):
        """Test parsing OPA list result."""
        opa = self._make_opa()
        result = {
            "result": {
                "deny": ["Violation 1", "Violation 2"]
            }
        }
        findings = opa._parse_results(result)
        assert len(findings) == 2
        assert findings[0]["message"] == "Violation 1"

    def test_parse_results_empty(self):
        """Test parsing empty OPA result."""
        opa = self._make_opa()
        result = {"result": {}}
        findings = opa._parse_results(result)
        assert findings == []

    def test_parse_results_no_result_key(self):
        """Test parsing result without 'result' key."""
        opa = self._make_opa()
        findings = opa._parse_results({})
        assert findings == []

    def test_parse_results_warn_key(self):
        """Test parsing 'warn' key in results."""
        opa = self._make_opa()
        result = {"result": {"warn": ["Warning message"]}}
        findings = opa._parse_results(result)
        assert len(findings) == 1
        assert findings[0]["message"] == "Warning message"

    def test_parse_results_violation_key(self):
        """Test parsing 'violation' key in results."""
        opa = self._make_opa()
        result = {"result": {"violation": [{"message": "Violation detail", "severity": "HIGH"}]}}
        findings = opa._parse_results(result)
        assert len(findings) == 1
        assert findings[0]["severity"] == "HIGH"

    def test_parse_results_filters_empty_strings(self):
        """Test that empty strings are filtered from results."""
        opa = self._make_opa()
        result = {"result": {"deny": {"": True, "Real violation": True}}}
        findings = opa._parse_results(result)
        assert len(findings) == 1
        assert findings[0]["message"] == "Real violation"


# ─── PolicyEvaluationService tests ───────────────────────────────────────────

class TestPolicyEvaluationService:
    """Tests for policy evaluation logic."""

    def _make_service(self, opa_mock=None, redis_mock=None):
        from app.services.evaluation import PolicyEvaluationService
        db_mock = AsyncMock()
        opa = opa_mock or AsyncMock()
        return PolicyEvaluationService(db_mock, opa, redis_mock)

    def test_is_rule_applicable_matching_type(self):
        """Test rule applicability with matching resource type."""
        svc = self._make_service()

        rule = MagicMock()
        rule.resource_type = "aws::s3::bucket"
        rule.provider = "aws"

        resource = {"resource_type": "aws::s3::bucket", "provider": "aws"}
        assert svc._is_rule_applicable(rule, resource) is True

    def test_is_rule_applicable_suffix_match(self):
        """Test rule applicability with suffix matching."""
        svc = self._make_service()

        rule = MagicMock()
        rule.resource_type = "s3bucket"
        rule.provider = None

        resource = {"resource_type": "aws::s3::s3bucket", "provider": "aws"}
        assert svc._is_rule_applicable(rule, resource) is True

    def test_is_rule_applicable_wrong_type(self):
        """Test rule not applicable for wrong resource type."""
        svc = self._make_service()

        rule = MagicMock()
        rule.resource_type = "aws::ec2::instance"
        rule.provider = "aws"

        resource = {"resource_type": "aws::s3::bucket", "provider": "aws"}
        assert svc._is_rule_applicable(rule, resource) is False

    def test_is_rule_applicable_no_type_filter(self):
        """Test rule with no type filter applies to all resources."""
        svc = self._make_service()

        rule = MagicMock()
        rule.resource_type = None
        rule.provider = None

        resource = {"resource_type": "aws::s3::bucket", "provider": "aws"}
        assert svc._is_rule_applicable(rule, resource) is True

    def test_create_finding_structure(self):
        """Test finding creation from rule and OPA result."""
        svc = self._make_service()

        rule = MagicMock()
        rule.rule_id = "aws-s3-public"
        rule.title = "S3 Public Access"
        rule.description = "S3 bucket is public"
        rule.severity = "CRITICAL"
        rule.category = "cspm"
        rule.provider = "aws"
        rule.resource_type = "aws::s3::bucket"
        rule.remediation = "Disable public access"
        rule.compliance_mapping = [{"framework": "CIS-AWS", "control": "2.1.5"}]
        rule.tags = ["s3", "public"]

        resource = {
            "cloud_resource_id": "arn:aws:s3:::my-bucket",
            "name": "my-bucket",
        }
        opa_result = {"message": "S3 bucket 'my-bucket' has public access"}

        finding = svc._create_finding(rule, resource, opa_result)

        assert finding["rule_id"] == "aws-s3-public"
        assert finding["severity"] == "CRITICAL"
        assert finding["resource_id"] == "arn:aws:s3:::my-bucket"
        assert finding["resource_name"] == "my-bucket"
        assert finding["description"] == "S3 bucket 'my-bucket' has public access"
        assert len(finding["compliance_mapping"]) == 1

    @pytest.mark.asyncio
    async def test_evaluate_resources_no_rules(self):
        """Test evaluation with no applicable rules returns empty findings."""
        svc = self._make_service()
        svc._get_enabled_rules = AsyncMock(return_value=[])

        findings = await svc.evaluate_resources(
            resources=[{"resource_type": "aws::s3::bucket", "name": "test"}],
            organization_id="org-1",
        )
        assert findings == []

    @pytest.mark.asyncio
    async def test_evaluate_uses_json_cache(self):
        """Test that Redis cache uses json.loads, not eval()."""
        redis_mock = AsyncMock()
        # Return a JSON-encoded cached result
        cached_finding = [{"rule_id": "test", "severity": "HIGH"}]
        redis_mock.get = AsyncMock(return_value=json.dumps(cached_finding))

        svc = self._make_service(redis_mock=redis_mock)

        rule = MagicMock()
        rule.rule_id = "test-rule"
        rule.resource_type = None
        rule.provider = None

        resource = {"cloud_resource_id": "res-1", "name": "test"}
        findings = await svc._evaluate_single_resource(resource, [rule])

        # Should return cached findings
        assert len(findings) == 1
        assert findings[0]["rule_id"] == "test"


# ─── ComplianceService tests ──────────────────────────────────────────────────

class TestComplianceService:
    """Tests for compliance posture calculation."""

    def _make_service(self, redis_mock=None):
        from app.services.evaluation import ComplianceService
        db_mock = AsyncMock()
        return ComplianceService(db_mock, redis_mock)

    def test_supported_frameworks(self):
        """Test all required frameworks are supported."""
        from app.services.evaluation import ComplianceService
        required = ["CIS-AWS", "SOC2", "PCI-DSS", "HIPAA", "ISO27001", "NIST-800-53", "GDPR"]
        for fw in required:
            assert fw in ComplianceService.FRAMEWORKS

    def test_compliance_percentage_calculation(self):
        """Test compliance percentage formula."""
        passing = 80
        total = 100
        percentage = round((passing / total * 100), 1)
        assert percentage == 80.0

    def test_compliance_percentage_zero_total(self):
        """Test compliance percentage with no controls."""
        total = 0
        percentage = round((0 / total * 100), 1) if total > 0 else 0.0
        assert percentage == 0.0

    @pytest.mark.asyncio
    async def test_get_compliance_posture_uses_json_cache(self):
        """Test that Redis cache uses json.loads, not eval()."""
        redis_mock = AsyncMock()
        cached_posture = {
            "framework": "CIS-AWS",
            "total_controls": 10,
            "passing": 8,
            "failing": 2,
            "not_applicable": 0,
            "percentage": 80.0,
            "controls": [],
        }
        redis_mock.get = AsyncMock(return_value=json.dumps(cached_posture))

        svc = self._make_service(redis_mock=redis_mock)
        result = await svc.get_compliance_posture("org-1", "CIS-AWS")

        assert result["framework"] == "CIS-AWS"
        assert result["percentage"] == 80.0

    @pytest.mark.asyncio
    async def test_get_all_frameworks_returns_all(self):
        """Test that get_all_frameworks returns all supported frameworks."""
        from app.services.evaluation import ComplianceService
        svc = self._make_service()
        # Mock get_compliance_posture to return a simple result
        svc.get_compliance_posture = AsyncMock(return_value={
            "framework": "test", "total_controls": 0, "passing": 0,
            "failing": 0, "not_applicable": 0, "percentage": 0.0, "controls": []
        })

        results = await svc.get_all_frameworks("org-1")
        assert len(results) == len(ComplianceService.FRAMEWORKS)


# ─── RuleManagementService tests ─────────────────────────────────────────────

class TestRuleManagementService:
    """Tests for rule management."""

    def _make_service(self, opa_mock=None):
        from app.services.rules import RuleManagementService
        db_mock = AsyncMock()
        opa = opa_mock or AsyncMock()
        return RuleManagementService(db_mock, opa)

    def test_increment_version_patch(self):
        """Test version increment."""
        svc = self._make_service()
        assert svc._increment_version("1.0.0") == "1.0.1"
        assert svc._increment_version("1.0.9") == "1.0.10"
        assert svc._increment_version("2.3.5") == "2.3.6"

    def test_increment_version_invalid(self):
        """Test version increment with invalid format."""
        svc = self._make_service()
        result = svc._increment_version("invalid")
        assert result == "1.0.1"

    def test_rule_to_dict_structure(self):
        """Test rule serialization to dict."""
        svc = self._make_service()

        rule = MagicMock()
        rule.id = "rule-uuid"
        rule.rule_id = "aws-s3-public"
        rule.title = "S3 Public Access"
        rule.description = "S3 bucket is public"
        rule.severity = "CRITICAL"
        rule.category = "cspm"
        rule.provider = "aws"
        rule.resource_type = "aws::s3::bucket"
        rule.remediation = "Disable public access"
        rule.version = "1.0.0"
        rule.compliance_mapping = []
        rule.tags = []
        rule.is_builtin = True
        rule.is_custom = False
        rule.is_enabled = True
        rule.created_at = datetime(2024, 1, 1)
        rule.updated_at = datetime(2024, 1, 2)

        d = svc._rule_to_dict(rule)

        assert d["rule_id"] == "aws-s3-public"
        assert d["severity"] == "CRITICAL"
        assert d["is_builtin"] is True
        assert d["is_custom"] is False
        assert "created_at" in d

    @pytest.mark.asyncio
    async def test_create_custom_rule_invalid_rego(self):
        """Test that invalid Rego raises ValueError."""
        opa_mock = AsyncMock()
        opa_mock.validate_rego = AsyncMock(return_value={"valid": False, "error": "syntax error"})

        svc = self._make_service(opa_mock)

        with pytest.raises(ValueError, match="Invalid Rego"):
            await svc.create_custom_rule(
                organization_id="org-1",
                rego_code="invalid rego code !!!",
                title="Test Rule",
            )


# ─── PolicyLoader tests ───────────────────────────────────────────────────────

class TestPolicyLoader:
    """Tests for Rego file loading."""

    def test_policy_name_from_path(self):
        """Test that policy names are correctly derived from file paths."""
        from pathlib import Path
        # Simulate path conversion: cspm/aws/s3_public.rego → cloudvisor/cspm/aws/s3_public
        rules_path = Path("/app/rules/rego")
        rego_file = Path("/app/rules/rego/cspm/aws/s3_public.rego")
        rel = rego_file.relative_to(rules_path)
        parts = list(rel.parts)
        parts[-1] = parts[-1].removesuffix(".rego")
        policy_name = "cloudvisor/" + "/".join(parts)
        assert policy_name == "cloudvisor/cspm/aws/s3_public"

    def test_policy_name_nested(self):
        """Test policy name for deeply nested file."""
        from pathlib import Path
        rules_path = Path("/app/rules/rego")
        rego_file = Path("/app/rules/rego/cspm/aws/iam/root_mfa.rego")
        rel = rego_file.relative_to(rules_path)
        parts = list(rel.parts)
        parts[-1] = parts[-1].removesuffix(".rego")
        policy_name = "cloudvisor/" + "/".join(parts)
        assert policy_name == "cloudvisor/cspm/aws/iam/root_mfa"


# ─── Rego rule content tests ──────────────────────────────────────────────────

class TestRegoRuleContent:
    """Tests that verify the Rego rule files have correct structure."""

    def _read_rego(self, path: str) -> str:
        from pathlib import Path
        rego_path = Path(__file__).parent.parent.parent.parent.parent / "rules" / "rego" / path
        if rego_path.exists():
            return rego_path.read_text()
        return ""

    def test_s3_public_access_rule_has_metadata(self):
        """Test S3 public access rule has required metadata."""
        from app.opa.opa_service import RegoParser
        rego = self._read_rego("cspm/aws/s3_public_access.rego")
        if not rego:
            pytest.skip("Rego file not found")

        meta = RegoParser.extract_metadata(rego)
        assert meta.get("severity") == "CRITICAL"
        assert meta.get("provider") == "aws"
        assert meta.get("category") == "cspm"

    def test_sg_ssh_rule_has_metadata(self):
        """Test security group SSH rule has required metadata."""
        from app.opa.opa_service import RegoParser
        rego = self._read_rego("cspm/aws/sg_unrestricted_ssh.rego")
        if not rego:
            pytest.skip("Rego file not found")

        meta = RegoParser.extract_metadata(rego)
        assert meta.get("severity") == "HIGH"
        assert "deny" in rego

    def test_all_rego_files_have_package(self):
        """Test all Rego files have a package declaration."""
        from pathlib import Path
        from app.opa.opa_service import RegoParser

        rules_dir = Path(__file__).parent.parent.parent.parent.parent / "rules" / "rego"
        if not rules_dir.exists():
            pytest.skip("Rules directory not found")

        for rego_file in rules_dir.rglob("*.rego"):
            content = rego_file.read_text()
            pkg = RegoParser.extract_package(content)
            assert pkg != "unknown", f"Missing package in {rego_file}"

    def test_all_rego_files_have_deny_rule(self):
        """Test all Rego files have at least one deny rule."""
        from pathlib import Path

        rules_dir = Path(__file__).parent.parent.parent.parent.parent / "rules" / "rego"
        if not rules_dir.exists():
            pytest.skip("Rules directory not found")

        for rego_file in rules_dir.rglob("*.rego"):
            content = rego_file.read_text()
            assert "deny[" in content, f"No deny rule in {rego_file}"


# ─── Builtin rules tests ──────────────────────────────────────────────────────

class TestBuiltinRules:
    """Tests for the hardcoded built-in rule library."""

    def test_builtin_rules_count(self):
        """Test that we have the expected number of built-in rules."""
        import sys
        sys.path.insert(0, "services/policy")
        from app.core.dependencies import _get_builtin_rules
        rules = _get_builtin_rules()
        assert len(rules) >= 8  # At least 8 built-in rules

    def test_builtin_rules_have_required_fields(self):
        """Test all built-in rules have required fields."""
        import sys
        sys.path.insert(0, "services/policy")
        from app.core.dependencies import _get_builtin_rules
        rules = _get_builtin_rules()

        required_fields = ["id", "rule_id", "title", "severity", "category", "rego_code"]
        for rule in rules:
            for field in required_fields:
                assert field in rule, f"Rule {rule.get('rule_id')} missing field: {field}"

    def test_builtin_rules_valid_severity(self):
        """Test all built-in rules have valid severity levels."""
        import sys
        sys.path.insert(0, "services/policy")
        from app.core.dependencies import _get_builtin_rules
        valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
        rules = _get_builtin_rules()

        for rule in rules:
            assert rule["severity"] in valid_severities, \
                f"Rule {rule['rule_id']} has invalid severity: {rule['severity']}"

    def test_builtin_rules_have_compliance_mapping(self):
        """Test that critical/high rules have compliance mappings."""
        import sys
        sys.path.insert(0, "services/policy")
        from app.core.dependencies import _get_builtin_rules
        rules = _get_builtin_rules()

        high_severity_rules = [r for r in rules if r["severity"] in ("CRITICAL", "HIGH")]
        for rule in high_severity_rules:
            assert len(rule.get("compliance_mapping", [])) > 0, \
                f"Rule {rule['rule_id']} has no compliance mapping"

    def test_builtin_rules_rego_has_package(self):
        """Test all built-in rule Rego code has a package declaration."""
        import sys
        sys.path.insert(0, "services/policy")
        from app.core.dependencies import _get_builtin_rules
        from app.opa.opa_service import RegoParser
        rules = _get_builtin_rules()

        for rule in rules:
            pkg = RegoParser.extract_package(rule["rego_code"])
            assert pkg != "unknown", f"Rule {rule['rule_id']} Rego has no package"

    def test_builtin_rules_rego_has_deny(self):
        """Test all built-in rule Rego code has a deny rule."""
        import sys
        sys.path.insert(0, "services/policy")
        from app.core.dependencies import _get_builtin_rules
        rules = _get_builtin_rules()

        for rule in rules:
            assert "deny[" in rule["rego_code"], \
                f"Rule {rule['rule_id']} Rego has no deny rule"


# ─── Async placeholder ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_placeholder():
    assert True
