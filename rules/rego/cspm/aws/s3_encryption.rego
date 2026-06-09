# METADATA
# title: "S3 bucket server-side encryption not enabled"
# description: "The S3 bucket does not have server-side encryption (SSE) enabled. Data stored in unencrypted S3 buckets is at risk if access controls are misconfigured or if AWS credentials are compromised."
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::s3::bucket
# compliance:
#   - framework: CIS-AWS
#     control: "2.1.1"
#   - framework: SOC2
#     control: "CC6.7"
#   - framework: PCI-DSS
#     control: "3.4"
#   - framework: HIPAA
#     control: "164.312(a)(2)(iv)"
# remediation: "Enable default server-side encryption on the S3 bucket using SSE-S3 (AES-256) or SSE-KMS. Use the AWS Console, CLI, or Terraform to set the bucket encryption configuration."
# version: "1.0.0"
# tags: [s3, encryption, data-protection, storage]

package cspm.aws.s3_encryption

deny[finding] if {
    input.resource_type == "aws::s3::bucket"
    not input.raw.ServerSideEncryptionConfiguration
    finding := {
        "rule_id": "aws-s3-encryption-disabled",
        "title": "S3 bucket does not have server-side encryption enabled",
        "severity": "HIGH",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": sprintf("S3 bucket '%v' does not have default server-side encryption configured.", [input.name]),
        "remediation": "Enable default server-side encryption using SSE-S3 (AES-256) or SSE-KMS on the bucket.",
    }
}
