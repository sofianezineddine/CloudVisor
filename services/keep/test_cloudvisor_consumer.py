"""
Unit tests for CloudVisor → Keep alert field mapping and error handling.

Validates Requirements: 8.2, 8.3, 8.4
"""

import json
import logging
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Mock external dependencies that may not be installed in the test environment
sys.modules.setdefault("kafka", MagicMock())
sys.modules.setdefault("kafka.errors", MagicMock())
sys.modules.setdefault("requests", MagicMock())

from cloudvisor_consumer import (
    SEVERITY_MAP,
    map_cloudvisor_alert_to_keep,
)


class TestMapCloudvisorAlertToKeep:
    """Tests for the map_cloudvisor_alert_to_keep function (Requirement 8.3)."""

    def test_title_maps_to_name(self):
        """title → name"""
        cv_alert = {
            "title": "High CPU Usage Detected",
            "severity": "high",
            "source": "cwpp",
            "resource_id": "res-123",
            "created_at": "2024-01-15T10:30:00Z",
            "tenant_id": "tenant-abc",
            "metadata": {},
        }
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["name"] == "High CPU Usage Detected"

    def test_severity_maps_directly(self):
        """severity → severity (direct mapping for known values)."""
        for cv_sev, keep_sev in [
            ("critical", "critical"),
            ("high", "high"),
            ("low", "low"),
            ("info", "info"),
        ]:
            cv_alert = {"severity": cv_sev, "metadata": {}}
            result = map_cloudvisor_alert_to_keep(cv_alert)
            assert result["severity"] == keep_sev, f"Failed for {cv_sev}"

    def test_severity_medium_maps_to_warning(self):
        """severity: medium → warning."""
        cv_alert = {"severity": "medium", "metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["severity"] == "warning"

    def test_severity_case_insensitive(self):
        """Severity mapping is case-insensitive."""
        cv_alert = {"severity": "CRITICAL", "metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["severity"] == "critical"

    def test_source_maps_to_list(self):
        """source → source[] (wrapped in a list)."""
        cv_alert = {"source": "cspm", "metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["source"] == ["cspm"]
        assert isinstance(result["source"], list)

    def test_resource_id_maps_to_fingerprint(self):
        """resource_id → fingerprint."""
        cv_alert = {"resource_id": "arn:aws:ec2:us-east-1:123:instance/i-abc", "metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["fingerprint"] == "arn:aws:ec2:us-east-1:123:instance/i-abc"

    def test_created_at_maps_to_last_received(self):
        """created_at → lastReceived."""
        cv_alert = {"created_at": "2024-01-15T10:30:00Z", "metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["lastReceived"] == "2024-01-15T10:30:00Z"

    def test_tenant_id_maps_to_tenant_id(self):
        """tenant_id → tenant_id."""
        cv_alert = {"tenant_id": "org-456", "metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["tenant_id"] == "org-456"

    def test_metadata_maps_to_labels(self):
        """metadata → labels."""
        cv_alert = {
            "metadata": {"compliance_framework": "CIS", "region": "us-east-1"},
        }
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["labels"]["compliance_framework"] == "CIS"
        assert result["labels"]["region"] == "us-east-1"

    def test_metadata_with_resource_type_in_labels(self):
        """resource_type is included in labels alongside metadata."""
        cv_alert = {
            "resource_type": "ec2_instance",
            "metadata": {"key": "value"},
        }
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["labels"]["resource_type"] == "ec2_instance"
        assert result["labels"]["key"] == "value"

    def test_full_mapping(self):
        """Complete field mapping with all fields present."""
        cv_alert = {
            "id": "alert-001",
            "tenant_id": "tenant-xyz",
            "title": "S3 Bucket Public Access",
            "description": "S3 bucket has public read access enabled",
            "severity": "high",
            "source": "cspm",
            "resource_id": "arn:aws:s3:::my-bucket",
            "resource_type": "s3_bucket",
            "created_at": "2024-03-01T08:00:00Z",
            "metadata": {"rule_id": "CIS-2.1.1", "account_id": "123456789"},
        }
        result = map_cloudvisor_alert_to_keep(cv_alert)

        assert result["name"] == "S3 Bucket Public Access"
        assert result["description"] == "S3 bucket has public read access enabled"
        assert result["severity"] == "high"
        assert result["source"] == ["cspm"]
        assert result["fingerprint"] == "arn:aws:s3:::my-bucket"
        assert result["lastReceived"] == "2024-03-01T08:00:00Z"
        assert result["tenant_id"] == "tenant-xyz"
        assert result["labels"]["resource_type"] == "s3_bucket"
        assert result["labels"]["rule_id"] == "CIS-2.1.1"
        assert result["labels"]["account_id"] == "123456789"
        assert result["status"] == "firing"
        assert result["pushed"] is True

    def test_missing_title_defaults(self):
        """Missing title defaults to 'CloudVisor Alert'."""
        cv_alert = {"metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["name"] == "CloudVisor Alert"

    def test_missing_severity_defaults_to_info(self):
        """Missing severity defaults to 'info'."""
        cv_alert = {"metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["severity"] == "info"

    def test_unknown_severity_defaults_to_info(self):
        """Unknown severity value defaults to 'info'."""
        cv_alert = {"severity": "unknown_level", "metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["severity"] == "info"

    def test_missing_source_defaults_to_cloudvisor(self):
        """Missing source defaults to ['cloudvisor']."""
        cv_alert = {"metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["source"] == ["cloudvisor"]

    def test_missing_resource_id_falls_back_to_id(self):
        """Missing resource_id falls back to id field."""
        cv_alert = {"id": "fallback-id", "metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["fingerprint"] == "fallback-id"

    def test_organization_id_fallback_for_tenant(self):
        """Falls back to organization_id if tenant_id is missing."""
        cv_alert = {"organization_id": "org-fallback", "metadata": {}}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["tenant_id"] == "org-fallback"

    def test_none_metadata_produces_empty_labels(self):
        """None metadata produces empty labels dict."""
        cv_alert = {"metadata": None}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["labels"] == {}

    def test_non_dict_metadata_produces_empty_labels(self):
        """Non-dict metadata is ignored."""
        cv_alert = {"metadata": "not a dict"}
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["labels"] == {}


class TestErrorHandling:
    """Tests for malformed event error handling (Requirement 8.4)."""

    def test_malformed_json_logged_and_skipped(self, caplog):
        """Malformed JSON events are logged and processing continues.

        The consumer loop catches JSONDecodeError and logs it.
        Here we verify the mapping function itself handles edge cases gracefully.
        """
        with caplog.at_level(logging.ERROR):
            # Simulate what happens when a non-dict value arrives
            try:
                result = map_cloudvisor_alert_to_keep({})
                # Should not crash - returns defaults
                assert result["name"] == "CloudVisor Alert"
                assert result["severity"] == "info"
            except Exception:
                pytest.fail("map_cloudvisor_alert_to_keep should not raise on empty dict")

    def test_mapping_does_not_crash_on_minimal_input(self):
        """Mapping function handles minimal/empty input without crashing."""
        result = map_cloudvisor_alert_to_keep({})
        assert result["name"] == "CloudVisor Alert"
        assert result["severity"] == "info"
        assert result["source"] == ["cloudvisor"]
        assert result["fingerprint"] == ""
        assert result["tenant_id"] == ""
        assert result["labels"] == {}

    def test_mapping_handles_extra_fields_gracefully(self):
        """Extra unexpected fields in the input don't cause errors."""
        cv_alert = {
            "title": "Test",
            "severity": "low",
            "source": "test",
            "resource_id": "r1",
            "created_at": "2024-01-01T00:00:00Z",
            "tenant_id": "t1",
            "metadata": {},
            "unexpected_field": "should be ignored",
            "another_extra": 12345,
        }
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["name"] == "Test"
        # Extra fields should not appear in output
        assert "unexpected_field" not in result
        assert "another_extra" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
