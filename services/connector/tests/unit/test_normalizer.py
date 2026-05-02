"""Unit tests for the resource normalizer."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_normalizer(org_id: str = "org-123"):
    from app.services.normalizer import ResourceNormalizer
    return ResourceNormalizer(organization_id=org_id)


# ---------------------------------------------------------------------------
# Tag normalization
# ---------------------------------------------------------------------------

class TestTagNormalization:
    def test_aws_tags_list_to_dict(self):
        n = make_normalizer()
        raw = {"Tags": [{"Key": "Env", "Value": "Production"}, {"Key": "Team", "Value": "Security"}]}
        tags = n._normalize_tags(raw, "aws")
        assert tags == {"env": "production", "team": "security"}

    def test_azure_tags_dict(self):
        n = make_normalizer()
        raw = {"tags": {"Environment": "Staging", "Owner": "Alice"}}
        tags = n._normalize_tags(raw, "azure")
        assert tags == {"environment": "staging", "owner": "alice"}

    def test_gcp_labels(self):
        n = make_normalizer()
        raw = {"labels": {"env": "dev", "project": "cloudvisor"}}
        tags = n._normalize_tags(raw, "gcp")
        assert tags == {"env": "dev", "project": "cloudvisor"}

    def test_empty_tags(self):
        n = make_normalizer()
        assert n._normalize_tags({}, "aws") == {}

    def test_none_tags(self):
        n = make_normalizer()
        assert n._normalize_tags({"Tags": None}, "aws") == {}


# ---------------------------------------------------------------------------
# Environment inference
# ---------------------------------------------------------------------------

class TestEnvironmentInference:
    def test_prod_from_tag(self):
        n = make_normalizer()
        from cloudvisor_types.models import Environment
        env = n._infer_environment({"env": "production"}, "my-prod-server")
        assert env == Environment.PROD

    def test_staging_from_name(self):
        n = make_normalizer()
        from cloudvisor_types.models import Environment
        env = n._infer_environment({}, "staging-api-gateway")
        assert env == Environment.STAGING

    def test_dev_from_tag(self):
        n = make_normalizer()
        from cloudvisor_types.models import Environment
        env = n._infer_environment({"environment": "dev"}, "some-resource")
        assert env == Environment.DEV

    def test_unknown_fallback(self):
        n = make_normalizer()
        from cloudvisor_types.models import Environment
        env = n._infer_environment({}, "random-resource-xyz")
        assert env == Environment.UNKNOWN


# ---------------------------------------------------------------------------
# Public access detection
# ---------------------------------------------------------------------------

class TestPublicAccessDetection:
    def test_s3_public_block_disabled(self):
        n = make_normalizer()
        raw = {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": False,
                "BlockPublicPolicy": False,
            }
        }
        assert n._detect_public_access(raw, "aws::s3::bucket") is True

    def test_s3_public_block_enabled(self):
        n = make_normalizer()
        raw = {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            }
        }
        assert n._detect_public_access(raw, "aws::s3::bucket") is False

    def test_ec2_with_public_ip(self):
        n = make_normalizer()
        raw = {"PublicIpAddress": "1.2.3.4"}
        assert n._detect_public_access(raw, "aws::ec2::instance") is True

    def test_ec2_no_public_ip(self):
        n = make_normalizer()
        raw = {"PrivateIpAddress": "10.0.0.1"}
        assert n._detect_public_access(raw, "aws::ec2::instance") is False


# ---------------------------------------------------------------------------
# Region extraction
# ---------------------------------------------------------------------------

class TestRegionExtraction:
    def test_aws_az_to_region(self):
        n = make_normalizer()
        raw = {"Placement": {"AvailabilityZone": "us-east-1a"}}
        region = n._extract_region(raw, "aws")
        assert region == "us-east-1"

    def test_azure_location(self):
        n = make_normalizer()
        raw = {"location": "eastus"}
        region = n._extract_region(raw, "azure")
        assert region == "eastus"

    def test_gcp_zone_to_region(self):
        n = make_normalizer()
        raw = {"zone": "us-central1-a"}
        region = n._extract_region(raw, "gcp")
        assert region == "us-central1"

    def test_fallback_to_global(self):
        n = make_normalizer()
        region = n._extract_region({}, "aws")
        assert region == "global"
