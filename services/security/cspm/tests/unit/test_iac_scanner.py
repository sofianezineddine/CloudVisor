"""Unit tests for IaC Scanner template parsers and secret detection."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from app.services.iac_scanner import (
    IaCFinding,
    IaCParseError,
    IaCParseResult,
    ParsedResource,
    detect_secrets,
    evaluate_against_rules,
    parse_cloudformation,
    parse_kubernetes,
    parse_terraform,
    scan_template,
    _redact_value,
    _estimate_line_number,
    _get_rule_paths_for_resource,
)


# ─── parse_terraform ───────────────────────────────────────────────────────────


class TestParseTerraform:
    """Tests for parse_terraform."""

    def test_parse_single_resource(self):
        hcl_content = '''
resource "aws_s3_bucket" "my_bucket" {
  bucket = "my-test-bucket"
  acl    = "private"
}
'''
        result = parse_terraform(hcl_content, "main.tf")
        assert len(result.errors) == 0
        assert len(result.resources) == 1
        res = result.resources[0]
        assert res.resource_type == "aws_s3_bucket"
        assert res.resource_identifier == "aws_s3_bucket.my_bucket"
        assert res.file_path == "main.tf"
        # python-hcl2 preserves string values (may include quotes in some versions)
        bucket_val = res.properties.get("bucket", "")
        assert "my-test-bucket" in bucket_val

    def test_parse_multiple_resources(self):
        hcl_content = '''
resource "aws_s3_bucket" "bucket_a" {
  bucket = "bucket-a"
}

resource "aws_security_group" "sg" {
  name = "my-sg"
}
'''
        result = parse_terraform(hcl_content, "infra.tf")
        assert len(result.errors) == 0
        assert len(result.resources) == 2
        types = {r.resource_type for r in result.resources}
        assert "aws_s3_bucket" in types
        assert "aws_security_group" in types

    def test_parse_malformed_hcl_returns_error(self):
        bad_content = "resource { this is not valid HCL }"
        result = parse_terraform(bad_content, "bad.tf")
        assert len(result.errors) > 0
        assert result.errors[0].file_path == "bad.tf"
        assert "Failed to parse Terraform HCL" in result.errors[0].error_message

    def test_parse_empty_content(self):
        result = parse_terraform("", "empty.tf")
        assert len(result.resources) == 0
        assert len(result.errors) == 0


# ─── parse_cloudformation ──────────────────────────────────────────────────────


class TestParseCloudFormation:
    """Tests for parse_cloudformation."""

    def test_parse_yaml_template(self):
        cf_yaml = """
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-bucket
      VersioningConfiguration:
        Status: Enabled
"""
        result = parse_cloudformation(cf_yaml, "template.yaml")
        assert len(result.errors) == 0
        assert len(result.resources) == 1
        res = result.resources[0]
        assert res.resource_type == "AWS::S3::Bucket"
        assert res.resource_identifier == "MyBucket"
        assert res.properties["BucketName"] == "my-bucket"

    def test_parse_json_template(self):
        cf_json = '''{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Resources": {
    "MySecurityGroup": {
      "Type": "AWS::EC2::SecurityGroup",
      "Properties": {
        "GroupDescription": "Test SG"
      }
    }
  }
}'''
        result = parse_cloudformation(cf_json, "template.json")
        assert len(result.errors) == 0
        assert len(result.resources) == 1
        assert result.resources[0].resource_type == "AWS::EC2::SecurityGroup"

    def test_parse_malformed_yaml_returns_error(self):
        bad_yaml = "Resources:\n  - invalid: [unclosed"
        result = parse_cloudformation(bad_yaml, "bad.yaml")
        assert len(result.errors) > 0
        assert "bad.yaml" == result.errors[0].file_path

    def test_missing_resources_section(self):
        no_resources = """
AWSTemplateFormatVersion: '2010-09-09'
Description: No resources here
"""
        result = parse_cloudformation(no_resources, "empty.yaml")
        # Should return error about missing Resources section
        assert len(result.resources) == 0

    def test_empty_content_returns_error(self):
        result = parse_cloudformation("", "empty.yaml")
        assert len(result.errors) > 0


# ─── parse_kubernetes ──────────────────────────────────────────────────────────


class TestParseKubernetes:
    """Tests for parse_kubernetes."""

    def test_parse_single_document(self):
        k8s_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: production
spec:
  replicas: 3
"""
        result = parse_kubernetes(k8s_yaml, "deployment.yaml")
        assert len(result.errors) == 0
        assert len(result.resources) == 1
        res = result.resources[0]
        assert res.resource_type == "apps/v1/Deployment"
        assert res.resource_identifier == "production/Deployment/my-app"
        assert res.properties["spec"]["replicas"] == 3

    def test_parse_multi_document(self):
        multi_yaml = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
  namespace: default
spec:
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
spec:
  replicas: 2
"""
        result = parse_kubernetes(multi_yaml, "manifests.yaml")
        assert len(result.errors) == 0
        assert len(result.resources) == 2
        kinds = {r.properties["kind"] for r in result.resources}
        assert "Service" in kinds
        assert "Deployment" in kinds

    def test_parse_malformed_yaml_returns_error(self):
        bad_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: [unclosed"
        result = parse_kubernetes(bad_yaml, "bad.yaml")
        assert len(result.errors) > 0

    def test_parse_empty_document_skipped(self):
        yaml_with_empty = """
---
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
"""
        result = parse_kubernetes(yaml_with_empty, "config.yaml")
        # Empty documents should be skipped
        assert len(result.resources) == 1
        assert result.resources[0].properties["kind"] == "ConfigMap"


# ─── detect_secrets ────────────────────────────────────────────────────────────


class TestDetectSecrets:
    """Tests for detect_secrets."""

    def test_detect_aws_access_key(self):
        content = 'aws_access_key = "AKIAIOSFODNN7EXAMPLE"'
        findings = detect_secrets(content, "main.tf")
        assert len(findings) == 1
        assert findings[0].secret_type == "AWS Access Key"
        assert findings[0].is_secret is True
        assert findings[0].severity == "CRITICAL"
        # Value should be redacted
        assert "AKIAIOSFODNN7EXAMPLE" not in findings[0].description
        assert "AKIA****REDACTED****" in findings[0].description

    def test_detect_hardcoded_password(self):
        content = 'password = "super_secret_password_123"'
        findings = detect_secrets(content, "config.yaml")
        assert len(findings) == 1
        assert findings[0].secret_type == "Hardcoded Secret"
        assert findings[0].is_secret is True

    def test_detect_private_key(self):
        content = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA..."
        findings = detect_secrets(content, "key.pem")
        assert len(findings) == 1
        assert findings[0].secret_type == "Private Key"

    def test_detect_github_token(self):
        content = 'token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"'
        findings = detect_secrets(content, "ci.yaml")
        assert len(findings) == 1
        assert findings[0].secret_type == "GitHub Personal Access Token"

    def test_no_secrets_in_clean_content(self):
        content = """
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"
  acl    = "private"
}
"""
        findings = detect_secrets(content, "clean.tf")
        assert len(findings) == 0

    def test_secret_value_is_redacted(self):
        content = 'api_key = "very_long_secret_value_here"'
        findings = detect_secrets(content, "config.tf")
        assert len(findings) == 1
        # The actual secret should not appear in the finding
        assert "very_long_secret_value_here" not in findings[0].description

    def test_line_number_is_correct(self):
        content = "line1\nline2\npassword = \"mysecretpassword123\"\nline4"
        findings = detect_secrets(content, "test.tf")
        assert len(findings) == 1
        assert findings[0].line_number == 3


# ─── evaluate_against_rules ────────────────────────────────────────────────────


class TestEvaluateAgainstRules:
    """Tests for evaluate_against_rules."""

    @pytest.mark.asyncio
    async def test_returns_findings_from_opa_violations(self):
        mock_client = AsyncMock()
        mock_client.evaluate_rule.return_value = {
            "result": {
                "violations": [
                    {
                        "rule_id": "s3_encryption",
                        "severity": "HIGH",
                        "title": "S3 bucket not encrypted",
                        "description": "Enable encryption",
                        "remediation": "Add encryption config",
                    }
                ]
            }
        }

        resources = [
            ParsedResource(
                resource_type="aws_s3_bucket",
                resource_identifier="aws_s3_bucket.test",
                properties={"bucket": "test"},
                file_path="main.tf",
                line_number=5,
            )
        ]

        findings = await evaluate_against_rules(
            resources, rule_paths=["cspm/iac/terraform/aws_s3_bucket"], opa_client=mock_client
        )
        assert len(findings) == 1
        assert findings[0].rule_id == "s3_encryption"
        assert findings[0].severity == "HIGH"
        assert findings[0].is_secret is False

    @pytest.mark.asyncio
    async def test_handles_opa_error_gracefully(self):
        from app.core.opa_client import OPAClientError

        mock_client = AsyncMock()
        mock_client.evaluate_rule.side_effect = OPAClientError("Service unavailable")

        resources = [
            ParsedResource(
                resource_type="aws_s3_bucket",
                resource_identifier="aws_s3_bucket.test",
                properties={},
                file_path="main.tf",
                line_number=1,
            )
        ]

        findings = await evaluate_against_rules(
            resources, rule_paths=["cspm/iac/terraform/aws_s3_bucket"], opa_client=mock_client
        )
        # Should not raise, just return empty findings
        assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_no_violations_returns_empty(self):
        mock_client = AsyncMock()
        mock_client.evaluate_rule.return_value = {"result": {"violations": []}}

        resources = [
            ParsedResource(
                resource_type="aws_s3_bucket",
                resource_identifier="aws_s3_bucket.test",
                properties={},
                file_path="main.tf",
                line_number=1,
            )
        ]

        findings = await evaluate_against_rules(
            resources, rule_paths=["cspm/iac/terraform/aws_s3_bucket"], opa_client=mock_client
        )
        assert len(findings) == 0


# ─── Helper Functions ──────────────────────────────────────────────────────────


class TestHelpers:
    """Tests for helper functions."""

    def test_redact_value_short(self):
        assert _redact_value("abc") == "****REDACTED****"

    def test_redact_value_long(self):
        result = _redact_value("AKIAIOSFODNN7EXAMPLE")
        assert result == "AKIA****REDACTED****"
        assert "IOSFODNN7EXAMPLE" not in result

    def test_estimate_line_number_found(self):
        content = "line1\nline2\ntarget_line\nline4"
        assert _estimate_line_number(content, "target_line") == 3

    def test_estimate_line_number_not_found(self):
        content = "line1\nline2\nline3"
        assert _estimate_line_number(content, "nonexistent") is None

    def test_get_rule_paths_for_aws_resource(self):
        resource = ParsedResource(
            resource_type="aws_s3_bucket",
            resource_identifier="aws_s3_bucket.test",
            properties={},
            file_path="main.tf",
        )
        paths = _get_rule_paths_for_resource(resource)
        assert paths == ["cspm/iac/terraform/aws_s3_bucket"]

    def test_get_rule_paths_for_cloudformation_resource(self):
        resource = ParsedResource(
            resource_type="AWS::S3::Bucket",
            resource_identifier="MyBucket",
            properties={},
            file_path="template.yaml",
        )
        paths = _get_rule_paths_for_resource(resource)
        assert paths == ["cspm/iac/cloudformation/s3_bucket"]

    def test_get_rule_paths_for_kubernetes_resource(self):
        resource = ParsedResource(
            resource_type="apps/v1/Deployment",
            resource_identifier="default/Deployment/my-app",
            properties={},
            file_path="deploy.yaml",
        )
        paths = _get_rule_paths_for_resource(resource)
        assert paths == ["cspm/iac/kubernetes/deployment"]


# ─── scan_template integration ─────────────────────────────────────────────────


class TestScanTemplate:
    """Tests for the high-level scan_template function."""

    @pytest.mark.asyncio
    async def test_scan_cloudformation_with_secrets(self):
        cf_content = """
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-bucket
      AccessKey: AKIAIOSFODNN7EXAMPLE
"""
        mock_client = AsyncMock()
        mock_client.evaluate_rule.return_value = {"result": {"violations": []}}

        findings, errors = await scan_template(
            cf_content, "template.yaml", "cloudformation", opa_client=mock_client
        )
        # Should detect the AWS access key as a secret
        secret_findings = [f for f in findings if f.is_secret]
        assert len(secret_findings) >= 1
        assert secret_findings[0].secret_type == "AWS Access Key"

    @pytest.mark.asyncio
    async def test_scan_unsupported_type_returns_error(self):
        findings, errors = await scan_template(
            "content", "file.txt", "unsupported_type"
        )
        assert len(errors) > 0
        assert "Unsupported template type" in errors[0].error_message
