"""Unit tests for toxic combination detection in Attack Path Engine."""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from app.services.attack_path_engine import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    TOXIC_PATTERNS,
    build_consolidated_finding,
    detect_toxic_combinations,
    elevate_severity,
    load_custom_toxic_rules,
)


# ─── detect_toxic_combinations ────────────────────────────────────────────────


class TestDetectToxicCombinations:
    """Tests for detect_toxic_combinations."""

    def test_detects_public_sensitive_unencrypted_pattern(self):
        """All three components present should trigger the pattern."""
        resource_configs = [
            {
                "resource_id": "bucket-1",
                "organization_id": "org-123",
                "misconfigurations": [
                    {"rule_id": "r1", "severity": "MEDIUM", "component_tag": "public_access", "description": "Public access enabled"},
                    {"rule_id": "r2", "severity": "LOW", "component_tag": "sensitive_data_tag", "description": "Contains sensitive data"},
                    {"rule_id": "r3", "severity": "MEDIUM", "component_tag": "no_encryption", "description": "No encryption"},
                ],
            }
        ]

        findings = detect_toxic_combinations(resource_configs)

        assert len(findings) == 1
        finding = findings[0]
        assert finding["pattern_id"] == "public-sensitive-unencrypted"
        assert finding["resource_id"] == "bucket-1"
        assert finding["organization_id"] == "org-123"
        assert finding["elevated_severity"] == SEVERITY_CRITICAL
        assert len(finding["component_finding_ids"]) == 3
        assert len(finding["component_details"]) == 3

    def test_detects_admin_no_mfa_external_trust_pattern(self):
        resource_configs = [
            {
                "resource_id": "iam-user-1",
                "organization_id": "org-456",
                "misconfigurations": [
                    {"rule_id": "r4", "severity": "HIGH", "component_tag": "admin_privileges", "description": "Admin access"},
                    {"rule_id": "r5", "severity": "MEDIUM", "component_tag": "no_mfa", "description": "MFA not enabled"},
                    {"rule_id": "r6", "severity": "MEDIUM", "component_tag": "external_trust", "description": "External trust"},
                ],
            }
        ]

        findings = detect_toxic_combinations(resource_configs)

        assert len(findings) == 1
        assert findings[0]["pattern_id"] == "admin-no-mfa-external-trust"
        assert findings[0]["elevated_severity"] == SEVERITY_CRITICAL

    def test_no_match_when_components_incomplete(self):
        """Only two of three components should not trigger."""
        resource_configs = [
            {
                "resource_id": "bucket-2",
                "organization_id": "org-123",
                "misconfigurations": [
                    {"rule_id": "r1", "severity": "MEDIUM", "component_tag": "public_access", "description": "Public"},
                    {"rule_id": "r2", "severity": "LOW", "component_tag": "sensitive_data_tag", "description": "Sensitive"},
                    # Missing no_encryption
                ],
            }
        ]

        findings = detect_toxic_combinations(resource_configs)
        assert findings == []

    def test_no_match_when_no_misconfigurations(self):
        resource_configs = [
            {
                "resource_id": "bucket-3",
                "organization_id": "org-123",
                "misconfigurations": [],
            }
        ]

        findings = detect_toxic_combinations(resource_configs)
        assert findings == []

    def test_empty_resource_configs(self):
        findings = detect_toxic_combinations([])
        assert findings == []

    def test_multiple_resources_multiple_patterns(self):
        """Each resource is checked independently."""
        resource_configs = [
            {
                "resource_id": "bucket-1",
                "organization_id": "org-123",
                "misconfigurations": [
                    {"rule_id": "r1", "severity": "MEDIUM", "component_tag": "public_access", "description": ""},
                    {"rule_id": "r2", "severity": "LOW", "component_tag": "sensitive_data_tag", "description": ""},
                    {"rule_id": "r3", "severity": "MEDIUM", "component_tag": "no_encryption", "description": ""},
                ],
            },
            {
                "resource_id": "iam-1",
                "organization_id": "org-123",
                "misconfigurations": [
                    {"rule_id": "r4", "severity": "HIGH", "component_tag": "admin_privileges", "description": ""},
                    {"rule_id": "r5", "severity": "MEDIUM", "component_tag": "no_mfa", "description": ""},
                    {"rule_id": "r6", "severity": "MEDIUM", "component_tag": "external_trust", "description": ""},
                ],
            },
        ]

        findings = detect_toxic_combinations(resource_configs)
        assert len(findings) == 2
        pattern_ids = {f["pattern_id"] for f in findings}
        assert pattern_ids == {"public-sensitive-unencrypted", "admin-no-mfa-external-trust"}

    def test_custom_patterns_override(self):
        """Custom patterns can be passed to override defaults."""
        custom_patterns = [
            {
                "id": "custom-combo",
                "components": ["tag_a", "tag_b"],
                "elevated_severity": "HIGH",
                "description": "Custom combination",
            }
        ]

        resource_configs = [
            {
                "resource_id": "res-1",
                "organization_id": "org-1",
                "misconfigurations": [
                    {"rule_id": "r1", "severity": "LOW", "component_tag": "tag_a", "description": ""},
                    {"rule_id": "r2", "severity": "LOW", "component_tag": "tag_b", "description": ""},
                ],
            }
        ]

        findings = detect_toxic_combinations(resource_configs, patterns=custom_patterns)
        assert len(findings) == 1
        assert findings[0]["pattern_id"] == "custom-combo"

    def test_finding_includes_detected_at_timestamp(self):
        resource_configs = [
            {
                "resource_id": "bucket-1",
                "organization_id": "org-123",
                "misconfigurations": [
                    {"rule_id": "r1", "severity": "MEDIUM", "component_tag": "public_access", "description": ""},
                    {"rule_id": "r2", "severity": "LOW", "component_tag": "sensitive_data_tag", "description": ""},
                    {"rule_id": "r3", "severity": "MEDIUM", "component_tag": "no_encryption", "description": ""},
                ],
            }
        ]

        findings = detect_toxic_combinations(resource_configs)
        assert findings[0]["detected_at"] is not None


# ─── elevate_severity ─────────────────────────────────────────────────────────


class TestElevateSeverity:
    """Tests for elevate_severity."""

    def test_pattern_severity_used_when_strictly_greater(self):
        """If pattern severity > max component, use pattern severity."""
        result = elevate_severity(
            component_severities=["LOW", "MEDIUM"],
            pattern_elevated_severity="CRITICAL",
        )
        assert result == SEVERITY_CRITICAL

    def test_bumps_when_pattern_not_strictly_greater(self):
        """If pattern severity == max component, bump one level."""
        result = elevate_severity(
            component_severities=["HIGH", "MEDIUM"],
            pattern_elevated_severity="HIGH",
        )
        # HIGH is max component (rank 3), so elevated must be rank 4 = CRITICAL
        assert result == SEVERITY_CRITICAL

    def test_bumps_low_to_medium(self):
        result = elevate_severity(
            component_severities=["LOW"],
            pattern_elevated_severity="LOW",
        )
        assert result == SEVERITY_MEDIUM

    def test_bumps_medium_to_high(self):
        result = elevate_severity(
            component_severities=["MEDIUM", "LOW"],
            pattern_elevated_severity="MEDIUM",
        )
        assert result == SEVERITY_HIGH

    def test_critical_components_stay_critical(self):
        """When max component is CRITICAL, elevated is still CRITICAL (capped)."""
        result = elevate_severity(
            component_severities=["CRITICAL"],
            pattern_elevated_severity="LOW",
        )
        # CRITICAL is rank 4, bump would be rank 5 but capped at 4 = CRITICAL
        assert result == SEVERITY_CRITICAL

    def test_empty_components_uses_pattern_severity(self):
        result = elevate_severity(
            component_severities=[],
            pattern_elevated_severity="HIGH",
        )
        assert result == SEVERITY_HIGH

    def test_elevated_is_strictly_greater_than_max_component(self):
        """Core requirement: elevated severity > max component severity."""
        from app.services.attack_path_engine import _SEVERITY_ORDER

        for components in [["LOW"], ["MEDIUM"], ["LOW", "MEDIUM"], ["HIGH"]]:
            result = elevate_severity(components, "CRITICAL")
            max_comp_rank = max(_SEVERITY_ORDER[s] for s in components)
            result_rank = _SEVERITY_ORDER[result]
            assert result_rank > max_comp_rank, (
                f"Elevated {result} should be > max component {components}"
            )


# ─── build_consolidated_finding ───────────────────────────────────────────────


class TestBuildConsolidatedFinding:
    """Tests for build_consolidated_finding."""

    def test_builds_finding_with_all_fields(self):
        pattern = {
            "id": "test-pattern",
            "components": ["a", "b"],
            "elevated_severity": "CRITICAL",
            "description": "Test pattern description",
        }
        misconfigs = [
            {"rule_id": "rule-1", "severity": "MEDIUM", "description": "Desc 1", "component_tag": "a"},
            {"rule_id": "rule-2", "severity": "LOW", "description": "Desc 2", "component_tag": "b"},
        ]

        finding = build_consolidated_finding(
            resource_id="res-1",
            organization_id="org-1",
            pattern=pattern,
            contributing_misconfigs=misconfigs,
            elevated_severity="CRITICAL",
        )

        assert finding["resource_id"] == "res-1"
        assert finding["organization_id"] == "org-1"
        assert finding["pattern_id"] == "test-pattern"
        assert finding["elevated_severity"] == "CRITICAL"
        assert finding["description"] == "Test pattern description"
        assert finding["component_finding_ids"] == ["rule-1", "rule-2"]
        assert len(finding["component_details"]) == 2
        assert finding["id"]  # UUID generated
        assert finding["detected_at"] is not None

    def test_includes_all_sub_findings(self):
        """All contributing misconfigurations must appear as sub-findings."""
        pattern = {"id": "p1", "components": ["x", "y", "z"], "elevated_severity": "HIGH", "description": ""}
        misconfigs = [
            {"rule_id": "r1", "severity": "LOW", "description": "d1", "component_tag": "x"},
            {"rule_id": "r2", "severity": "LOW", "description": "d2", "component_tag": "y"},
            {"rule_id": "r3", "severity": "MEDIUM", "description": "d3", "component_tag": "z"},
        ]

        finding = build_consolidated_finding("res", "org", pattern, misconfigs, "HIGH")

        assert len(finding["component_details"]) == 3
        assert all("rule_id" in d for d in finding["component_details"])
        assert all("severity" in d for d in finding["component_details"])

    def test_handles_empty_misconfigs(self):
        pattern = {"id": "p1", "components": [], "elevated_severity": "HIGH", "description": ""}

        finding = build_consolidated_finding("res", "org", pattern, [], "HIGH")

        assert finding["component_finding_ids"] == []
        assert finding["component_details"] == []


# ─── load_custom_toxic_rules ──────────────────────────────────────────────────


class TestLoadCustomToxicRules:
    """Tests for load_custom_toxic_rules."""

    def test_loads_valid_rego_file(self):
        """Should parse metadata from a well-formed Rego file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rego_content = """# METADATA
# pattern_id: exposed-db-weak-auth
# components: public_db, weak_authentication, no_encryption
# elevated_severity: CRITICAL
# description: Publicly exposed database with weak auth and no encryption

package cspm.toxic_combinations.exposed_db_weak_auth

default violation = false

violation {
    input.public_db == true
    input.weak_authentication == true
    input.no_encryption == true
}
"""
            rego_file = Path(tmpdir) / "exposed_db_weak_auth.rego"
            rego_file.write_text(rego_content, encoding="utf-8")

            patterns = load_custom_toxic_rules(tmpdir)

            assert len(patterns) == 1
            p = patterns[0]
            assert p["id"] == "exposed-db-weak-auth"
            assert p["components"] == ["public_db", "weak_authentication", "no_encryption"]
            assert p["elevated_severity"] == "CRITICAL"
            assert p["description"] == "Publicly exposed database with weak auth and no encryption"
            assert p["rego_file"] == "exposed_db_weak_auth.rego"

    def test_skips_files_without_metadata(self):
        """Rego files without METADATA block should be skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rego_content = """package cspm.toxic_combinations.no_metadata

default violation = false
"""
            rego_file = Path(tmpdir) / "no_metadata.rego"
            rego_file.write_text(rego_content, encoding="utf-8")

            patterns = load_custom_toxic_rules(tmpdir)
            assert patterns == []

    def test_returns_empty_for_nonexistent_directory(self):
        patterns = load_custom_toxic_rules("/nonexistent/path/to/rules")
        assert patterns == []

    def test_returns_empty_for_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            patterns = load_custom_toxic_rules(tmpdir)
            assert patterns == []

    def test_loads_multiple_rego_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                content = f"""# METADATA
# pattern_id: pattern-{i}
# components: comp_a, comp_b
# elevated_severity: HIGH
# description: Pattern {i} description

package cspm.toxic_combinations.pattern_{i}
"""
                (Path(tmpdir) / f"pattern_{i}.rego").write_text(content, encoding="utf-8")

            patterns = load_custom_toxic_rules(tmpdir)
            assert len(patterns) == 3
            ids = {p["id"] for p in patterns}
            assert ids == {"pattern-0", "pattern-1", "pattern-2"}

    def test_skips_incomplete_metadata(self):
        """Files with partial metadata (missing required fields) are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content = """# METADATA
# pattern_id: incomplete
# components: a, b
# No elevated_severity or description

package cspm.toxic_combinations.incomplete
"""
            (Path(tmpdir) / "incomplete.rego").write_text(content, encoding="utf-8")

            patterns = load_custom_toxic_rules(tmpdir)
            assert patterns == []
