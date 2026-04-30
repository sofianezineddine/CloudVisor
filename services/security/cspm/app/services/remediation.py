"""
CSPM Auto-Remediation — suggestion mode.
Generates fix suggestions using rule metadata and optionally Claude API.
"""
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Static remediation templates per rule_id (fast path — no LLM needed)
REMEDIATION_TEMPLATES: dict[str, dict[str, str]] = {
    "aws-s3-public-access": {
        "console": "S3 → Bucket → Permissions → Block Public Access → Enable all options",
        "cli": "aws s3api put-public-access-block --bucket BUCKET_NAME --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true",
        "terraform": 'resource "aws_s3_bucket_public_access_block" "example" {\n  bucket = aws_s3_bucket.example.id\n  block_public_acls       = true\n  block_public_policy     = true\n  ignore_public_acls      = true\n  restrict_public_buckets = true\n}',
    },
    "aws-s3-encryption": {
        "console": "S3 → Bucket → Properties → Default Encryption → Enable (SSE-S3 or SSE-KMS)",
        "cli": "aws s3api put-bucket-encryption --bucket BUCKET_NAME --server-side-encryption-configuration '{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"AES256\"}}]}'",
        "terraform": 'resource "aws_s3_bucket_server_side_encryption_configuration" "example" {\n  bucket = aws_s3_bucket.example.id\n  rule {\n    apply_server_side_encryption_by_default {\n      sse_algorithm = "AES256"\n    }\n  }\n}',
    },
    "aws-sg-unrestricted-ssh": {
        "console": "EC2 → Security Groups → Inbound Rules → Remove rule allowing 0.0.0.0/0 on port 22",
        "cli": "aws ec2 revoke-security-group-ingress --group-id SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0",
        "terraform": '# Remove or restrict the ingress rule:\n# cidr_blocks = ["10.0.0.0/8"]  # Replace with your VPN/bastion CIDR',
    },
    "aws-sg-unrestricted-rdp": {
        "console": "EC2 → Security Groups → Inbound Rules → Remove rule allowing 0.0.0.0/0 on port 3389",
        "cli": "aws ec2 revoke-security-group-ingress --group-id SG_ID --protocol tcp --port 3389 --cidr 0.0.0.0/0",
        "terraform": '# Remove or restrict the ingress rule:\n# cidr_blocks = ["10.0.0.0/8"]  # Replace with your VPN/bastion CIDR',
    },
    "aws-iam-root-mfa": {
        "console": "IAM → Dashboard → Activate MFA on your root account → Virtual MFA device",
        "cli": "# MFA must be enabled via the AWS Console — no CLI equivalent for root account",
        "terraform": "# Root account MFA cannot be managed via Terraform",
    },
    "aws-rds-publicly-accessible": {
        "console": "RDS → Databases → Modify → Connectivity → Publicly accessible → No",
        "cli": "aws rds modify-db-instance --db-instance-identifier DB_ID --no-publicly-accessible --apply-immediately",
        "terraform": 'resource "aws_db_instance" "example" {\n  # ...\n  publicly_accessible = false\n}',
    },
    "aws-cloudtrail-disabled": {
        "console": "CloudTrail → Create trail → Enable for all regions → Enable log file validation",
        "cli": "aws cloudtrail create-trail --name cloudvisor-trail --s3-bucket-name YOUR_BUCKET --is-multi-region-trail --enable-log-file-validation",
        "terraform": 'resource "aws_cloudtrail" "main" {\n  name                          = "cloudvisor-trail"\n  s3_bucket_name                = aws_s3_bucket.cloudtrail.id\n  is_multi_region_trail         = true\n  enable_log_file_validation    = true\n}',
    },
    "aws-kms-key-rotation": {
        "console": "KMS → Customer managed keys → Select key → Key rotation → Enable automatic rotation",
        "cli": "aws kms enable-key-rotation --key-id KEY_ID",
        "terraform": 'resource "aws_kms_key" "example" {\n  enable_key_rotation = true\n}',
    },
    "aws-vpc-flow-logs": {
        "console": "VPC → Your VPCs → Select VPC → Flow logs → Create flow log",
        "cli": "aws ec2 create-flow-logs --resource-type VPC --resource-ids VPC_ID --traffic-type ALL --log-destination-type cloud-watch-logs --log-group-name /aws/vpc/flowlogs",
        "terraform": 'resource "aws_flow_log" "example" {\n  vpc_id          = aws_vpc.example.id\n  traffic_type    = "ALL"\n  iam_role_arn    = aws_iam_role.flow_log.arn\n  log_destination = aws_cloudwatch_log_group.flow_log.arn\n}',
    },
}


async def get_remediation_suggestion(
    rule_id: str,
    resource_name: str,
    resource_type: str,
    provider: str,
    remediation_text: str | None = None,
) -> dict[str, Any]:
    """
    Return a structured remediation suggestion for a finding.
    Uses static templates first; falls back to Claude API if available.
    """
    # 1. Try static template
    template = REMEDIATION_TEMPLATES.get(rule_id)
    if template:
        return {
            "rule_id": rule_id,
            "resource_name": resource_name,
            "source": "template",
            "console_steps": template.get("console", ""),
            "cli_command": template.get("cli", ""),
            "terraform_snippet": template.get("terraform", ""),
            "raw_remediation": remediation_text or "",
        }

    # 2. Fall back to Claude API if key is available
    if ANTHROPIC_API_KEY:
        try:
            return await _claude_remediation(rule_id, resource_name, resource_type, provider, remediation_text)
        except Exception as e:
            logger.warning(f"Claude remediation failed: {e}")

    # 3. Return raw remediation text
    return {
        "rule_id": rule_id,
        "resource_name": resource_name,
        "source": "raw",
        "console_steps": remediation_text or "Review the resource configuration and apply security best practices.",
        "cli_command": "",
        "terraform_snippet": "",
        "raw_remediation": remediation_text or "",
    }


async def _claude_remediation(
    rule_id: str,
    resource_name: str,
    resource_type: str,
    provider: str,
    remediation_text: str | None,
) -> dict[str, Any]:
    """Call Claude API to generate a structured remediation suggestion."""
    import httpx

    prompt = f"""You are a cloud security expert. Generate a concise remediation for this security finding:

Rule: {rule_id}
Resource: {resource_name} ({resource_type})
Provider: {provider}
Description: {remediation_text or 'Security misconfiguration detected'}

Respond with JSON only:
{{
  "console_steps": "Step-by-step console instructions",
  "cli_command": "Exact CLI command with placeholders",
  "terraform_snippet": "Terraform HCL snippet"
}}"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["content"][0]["text"]

        import json
        parsed = json.loads(content)
        return {
            "rule_id": rule_id,
            "resource_name": resource_name,
            "source": "claude",
            "console_steps": parsed.get("console_steps", ""),
            "cli_command": parsed.get("cli_command", ""),
            "terraform_snippet": parsed.get("terraform_snippet", ""),
            "raw_remediation": remediation_text or "",
        }
