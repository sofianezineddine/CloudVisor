# METADATA
# title: "S3 Bucket Server-Side Encryption Disabled"
# description: "S3 bucket does not have server-side encryption enabled"
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::s3::bucket
# compliance:
#   - framework: CIS-AWS
#     control: "2.1.1"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: HIPAA
#     control: "164.312(a)(2)(iv)"
# remediation: "Enable S3 bucket encryption: AWS Console > S3 > Bucket > Properties > Default encryption > Edit > Enable"

package cloudvisor.cspm.aws.s3_encryption

import future.keywords

deny[finding] {
    input.resource_type == "aws::s3::bucket"
    
    # Check if server-side encryption is missing or disabled
    encryption := input.raw.ServerSideEncryptionConfiguration
    
    # No encryption configuration
    not encryption
    
    finding := {
        "rule_id": "aws-s3-encryption-disabled",
        "title": "S3 bucket server-side encryption is disabled",
        "description": sprintf("S3 bucket '%s' does not have server-side encryption enabled", [input.name]),
        "severity": "HIGH",
        "remediation": "Enable server-side encryption for this S3 bucket using AES-256 or KMS",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.1.1"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "HIPAA", "control": "164.312(a)(2)(iv)"}
        ]
    }
}

deny[finding] {
    input.resource_type == "aws::s3::bucket"
    
    # Check if encryption configuration exists but has no rules
    encryption := input.raw.ServerSideEncryptionConfiguration
    encryption
    
    rules := encryption.Rules
    count(rules) == 0
    
    finding := {
        "rule_id": "aws-s3-encryption-no-rules",
        "title": "S3 bucket has no encryption rules configured",
        "description": sprintf("S3 bucket '%s' has encryption configuration but no encryption rules", [input.name]),
        "severity": "HIGH",
        "remediation": "Configure encryption rules for this S3 bucket",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.1.1"},
            {"framework": "SOC2", "control": "CC6.1"}
        ]
    }
}