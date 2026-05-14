# METADATA
# title: S3 Bucket Missing Server-Side Encryption
# description: Terraform aws_s3_bucket resource does not have server-side encryption configured.
# severity: HIGH
# category: iac
# provider: aws
# resource_type: aws_s3_bucket
# version: 1.0.0

package cloudvisor.iac.terraform.s3_encryption

import future.keywords.if
import future.keywords.in
import future.keywords.contains

violation contains finding if {
    input.resource.type == "aws_s3_bucket"
    properties := input.resource.properties
    not properties.server_side_encryption_configuration
    finding := {
        "rule_id": "iac.terraform.s3-encryption-missing",
        "severity": "HIGH",
        "title": "S3 Bucket Missing Server-Side Encryption",
        "description": sprintf("S3 bucket '%v' does not have server-side encryption configured. Data at rest is not protected.", [input.resource.identifier]),
        "remediation": "Add a server_side_encryption_configuration block with rule { apply_server_side_encryption_by_default { sse_algorithm = \"aws:kms\" } } to enable encryption at rest.",
    }
}

violation contains finding if {
    input.resource.type == "aws_s3_bucket"
    properties := input.resource.properties
    enc_config := properties.server_side_encryption_configuration
    rules := enc_config.rule
    rule := rules[_]
    default_enc := rule.apply_server_side_encryption_by_default
    default_enc.sse_algorithm == "AES256"
    finding := {
        "rule_id": "iac.terraform.s3-encryption-not-kms",
        "severity": "MEDIUM",
        "title": "S3 Bucket Using AES256 Instead of KMS Encryption",
        "description": sprintf("S3 bucket '%v' uses AES256 encryption instead of AWS KMS. KMS provides better key management and audit capabilities.", [input.resource.identifier]),
        "remediation": "Change sse_algorithm to \"aws:kms\" and specify a kms_master_key_id for better key management and CloudTrail audit logging.",
    }
}
