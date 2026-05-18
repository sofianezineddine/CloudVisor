"""
Property-based tests for malformed alert resilience.

**Validates: Requirements 8.4**

Property 6: Malformed Alert Resilience
For any malformed or invalid JSON payload consumed from the `cloudvisor.alerts`
Kafka topic, the Keep consumer SHALL log the error with the payload details and
SHALL continue processing subsequent valid events without interruption or crash.

This test verifies that `map_cloudvisor_alert_to_keep()` never raises an exception
regardless of input, and always produces a valid dict with required Keep alert fields.
"""

import sys
from unittest.mock import MagicMock

# Mock external dependencies that may not be installed in the test environment
sys.modules.setdefault("kafka", MagicMock())
sys.modules.setdefault("kafka.errors", MagicMock())
sys.modules.setdefault("requests", MagicMock())

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from cloudvisor_consumer import map_cloudvisor_alert_to_keep


# --- Strategies for generating malformed inputs ---

# Strategy: arbitrary JSON-like values (non-dict)
json_primitives = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=True, allow_infinity=True),
    st.text(),
    st.binary(),
    st.lists(st.integers()),
    st.lists(st.text()),
)

# Strategy: dicts with random keys and values (wrong types for expected fields)
garbage_values = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=True, allow_infinity=True),
    st.text(),
    st.binary(),
    st.lists(st.integers()),
    st.dictionaries(st.text(), st.text()),
)

malformed_dicts = st.dictionaries(
    keys=st.text(min_size=0, max_size=50),
    values=garbage_values,
    min_size=0,
    max_size=20,
)

# Strategy: dicts with expected field names but wrong types
wrong_type_fields = st.fixed_dictionaries(
    {},
    optional={
        "title": garbage_values,
        "severity": garbage_values,
        "source": garbage_values,
        "resource_id": garbage_values,
        "created_at": garbage_values,
        "tenant_id": garbage_values,
        "description": garbage_values,
        "metadata": garbage_values,
        "resource_type": garbage_values,
        "id": garbage_values,
        "organization_id": garbage_values,
        "environment": garbage_values,
    },
)

# Strategy: mix of valid and invalid fields
mixed_dicts = st.one_of(
    malformed_dicts,
    wrong_type_fields,
    st.fixed_dictionaries({}),  # empty dict
)

# Required fields that must always be present in the output
REQUIRED_KEEP_FIELDS = {
    "name",
    "description",
    "severity",
    "status",
    "source",
    "fingerprint",
    "lastReceived",
    "tenant_id",
    "labels",
    "pushed",
    "environment",
}


class TestMalformedAlertResilience:
    """Property 6: Malformed Alert Resilience.

    **Validates: Requirements 8.4**
    """

    @given(payload=malformed_dicts)
    @settings(max_examples=200)
    def test_random_dict_payloads_never_crash(self, payload):
        """map_cloudvisor_alert_to_keep never raises for any dict input."""
        # Should never raise an exception
        result = map_cloudvisor_alert_to_keep(payload)

        # Must always return a dict
        assert isinstance(result, dict)

        # Must always contain all required Keep alert fields
        for field in REQUIRED_KEEP_FIELDS:
            assert field in result, f"Missing required field: {field}"

    @given(payload=wrong_type_fields)
    @settings(max_examples=200)
    def test_wrong_type_fields_never_crash(self, payload):
        """map_cloudvisor_alert_to_keep handles wrong types for known fields."""
        result = map_cloudvisor_alert_to_keep(payload)

        assert isinstance(result, dict)
        for field in REQUIRED_KEEP_FIELDS:
            assert field in result, f"Missing required field: {field}"

    @given(payload=mixed_dicts)
    @settings(max_examples=200)
    def test_mixed_payloads_produce_valid_output_types(self, payload):
        """Output fields always have correct types regardless of input."""
        result = map_cloudvisor_alert_to_keep(payload)

        # Verify output field types are always correct
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

    @given(payload=malformed_dicts)
    @settings(max_examples=200)
    def test_severity_always_valid(self, payload):
        """Output severity is always a recognized Keep severity value."""
        valid_severities = {"critical", "high", "warning", "low", "info"}

        result = map_cloudvisor_alert_to_keep(payload)
        assert result["severity"] in valid_severities

    @given(payload=malformed_dicts)
    @settings(max_examples=200)
    def test_source_always_non_empty_list(self, payload):
        """Output source is always a non-empty list."""
        result = map_cloudvisor_alert_to_keep(payload)
        assert isinstance(result["source"], list)
        assert len(result["source"]) >= 1

    @given(payload=mixed_dicts)
    @settings(max_examples=100)
    def test_labels_values_are_strings(self, payload):
        """All label values in the output are strings."""
        result = map_cloudvisor_alert_to_keep(payload)
        for key, value in result["labels"].items():
            assert isinstance(key, str), f"Label key {key!r} is not a string"
            assert isinstance(value, str), f"Label value for {key!r} is not a string"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
