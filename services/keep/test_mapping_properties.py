"""
Property-Based Tests for CloudVisor → Keep Alert Field Mapping Correctness.

**Validates: Requirements 8.3**

Property 5: Alert Field Mapping Correctness
For any valid CloudVisor alert event consumed from Kafka with fields
(title, description, severity, source, resource_id, created_at, tenant_id, metadata),
the mapping function SHALL produce a valid Keep alert where:
  - name equals the original title
  - severity equals the mapped severity (medium→warning)
  - source contains the original source (wrapped in a list)
  - fingerprint equals the original resource_id
  - lastReceived equals the original created_at
  - tenant_id equals the original tenant_id
  - metadata is merged into labels (with resource_type)
  - The output is always a valid Keep alert structure
"""

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Mock external dependencies that may not be installed in the test environment
sys.modules.setdefault("kafka", MagicMock())
sys.modules.setdefault("kafka.errors", MagicMock())
sys.modules.setdefault("requests", MagicMock())

from cloudvisor_consumer import SEVERITY_MAP, map_cloudvisor_alert_to_keep


# --- Hypothesis Strategies ---

# Valid CloudVisor severity values
VALID_SEVERITIES = ["critical", "high", "medium", "low", "info", "warning"]

# Strategy for generating valid ISO 8601 timestamps
iso_timestamps = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
    timezones=st.just(timezone.utc),
).map(lambda dt: dt.isoformat())

# Strategy for non-empty text fields (identifiers, names, etc.)
non_empty_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S", "Z")),
    min_size=1,
    max_size=200,
).filter(lambda s: s.strip() != "")

# Strategy for source identifiers (e.g., "cspm", "cwpp", "cloudvisor")
source_identifiers = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != "")

# Strategy for metadata dictionaries (string keys and values)
metadata_strategy = st.dictionaries(
    keys=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=30,
    ).filter(lambda s: s.strip() != ""),
    values=st.one_of(
        st.text(min_size=0, max_size=100),
        st.integers(min_value=-1000, max_value=1000).map(str),
        st.booleans().map(str),
    ),
    max_size=10,
)

# Strategy for generating a complete valid CloudVisor alert
cloudvisor_alert_strategy = st.fixed_dictionaries({
    "id": non_empty_text,
    "tenant_id": non_empty_text,
    "title": non_empty_text,
    "description": st.text(min_size=0, max_size=500),
    "severity": st.sampled_from(VALID_SEVERITIES),
    "source": source_identifiers,
    "resource_id": non_empty_text,
    "resource_type": source_identifiers,
    "created_at": iso_timestamps,
    "metadata": metadata_strategy,
})


class TestAlertFieldMappingCorrectnessProperty:
    """
    Property 5: Alert Field Mapping Correctness

    For any valid CloudVisor alert, the mapping produces a correct Keep alert
    with all fields transformed correctly.

    **Validates: Requirements 8.3**
    """

    @given(cv_alert=cloudvisor_alert_strategy)
    @settings(max_examples=100)
    def test_title_maps_to_name(self, cv_alert):
        """Property: title → name mapping is always preserved."""
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["name"] == cv_alert["title"]

    @given(cv_alert=cloudvisor_alert_strategy)
    @settings(max_examples=100)
    def test_severity_maps_correctly(self, cv_alert):
        """Property: severity is mapped correctly (medium→warning, others preserved)."""
        result = map_cloudvisor_alert_to_keep(cv_alert)
        input_severity = cv_alert["severity"].lower()
        expected_severity = SEVERITY_MAP.get(input_severity, "info")
        assert result["severity"] == expected_severity

    @given(cv_alert=cloudvisor_alert_strategy)
    @settings(max_examples=100)
    def test_source_wrapped_in_list(self, cv_alert):
        """Property: source is always wrapped in a list containing the original value."""
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert isinstance(result["source"], list)
        assert len(result["source"]) == 1
        assert result["source"] == [cv_alert["source"]]

    @given(cv_alert=cloudvisor_alert_strategy)
    @settings(max_examples=100)
    def test_resource_id_maps_to_fingerprint(self, cv_alert):
        """Property: resource_id → fingerprint mapping is always preserved."""
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["fingerprint"] == cv_alert["resource_id"]

    @given(cv_alert=cloudvisor_alert_strategy)
    @settings(max_examples=100)
    def test_created_at_maps_to_last_received(self, cv_alert):
        """Property: created_at → lastReceived mapping is always preserved."""
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["lastReceived"] == cv_alert["created_at"]

    @given(cv_alert=cloudvisor_alert_strategy)
    @settings(max_examples=100)
    def test_tenant_id_maps_to_tenant_id(self, cv_alert):
        """Property: tenant_id → tenant_id mapping is always preserved."""
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert result["tenant_id"] == cv_alert["tenant_id"]

    @given(cv_alert=cloudvisor_alert_strategy)
    @settings(max_examples=100)
    def test_metadata_merged_into_labels(self, cv_alert):
        """Property: metadata dict entries are all present in labels."""
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert isinstance(result["labels"], dict)
        # All metadata keys should be present in labels
        for key, value in cv_alert["metadata"].items():
            assert key in result["labels"]
            assert result["labels"][key] == str(value)

    @given(cv_alert=cloudvisor_alert_strategy)
    @settings(max_examples=100)
    def test_resource_type_included_in_labels(self, cv_alert):
        """Property: resource_type is always included in labels."""
        result = map_cloudvisor_alert_to_keep(cv_alert)
        assert "resource_type" in result["labels"]
        assert result["labels"]["resource_type"] == cv_alert["resource_type"]

    @given(cv_alert=cloudvisor_alert_strategy)
    @settings(max_examples=100)
    def test_output_is_valid_keep_alert_structure(self, cv_alert):
        """Property: output always contains all required Keep alert fields with correct types."""
        result = map_cloudvisor_alert_to_keep(cv_alert)

        # Required fields must be present
        assert "name" in result
        assert "description" in result
        assert "severity" in result
        assert "status" in result
        assert "source" in result
        assert "fingerprint" in result
        assert "lastReceived" in result
        assert "tenant_id" in result
        assert "labels" in result
        assert "pushed" in result
        assert "environment" in result

        # Type checks
        assert isinstance(result["name"], str)
        assert isinstance(result["description"], str)
        assert isinstance(result["severity"], str)
        assert isinstance(result["status"], str)
        assert isinstance(result["source"], list)
        assert isinstance(result["fingerprint"], str)
        assert isinstance(result["lastReceived"], str)
        assert isinstance(result["tenant_id"], str)
        assert isinstance(result["labels"], dict)
        assert isinstance(result["pushed"], bool)
        assert isinstance(result["environment"], str)

        # Severity must be a valid Keep severity
        valid_keep_severities = {"critical", "high", "warning", "low", "info"}
        assert result["severity"] in valid_keep_severities

        # Status must be "firing" for newly mapped alerts
        assert result["status"] == "firing"

        # pushed must be True for ingested alerts
        assert result["pushed"] is True

    @given(cv_alert=cloudvisor_alert_strategy)
    @settings(max_examples=100)
    def test_medium_severity_always_maps_to_warning(self, cv_alert):
        """Property: when severity is 'medium', output severity is always 'warning'."""
        cv_alert_copy = dict(cv_alert)
        cv_alert_copy["severity"] = "medium"
        result = map_cloudvisor_alert_to_keep(cv_alert_copy)
        assert result["severity"] == "warning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
