# METADATA
# title: "S3 bucket versioning not enabled"
# description: "S3 bucket versioning is not enabled. Without versioning, accidental deletions or overwrites of objects cannot be recovered, and ransomware attacks can permanently destroy data."
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::s3::bucket
# compliance:
#   - framework: CIS-AWS
#     control: "2.1.3"
#   - framework: SOC2
#     control: "A1.2"
# remediation: "Enable versioning on the S3 bucket. Consider also enabling MFA Delete to prevent accidental or malicious deletion of versioned objects."
# version: "1.0.0"
# tags: [s3, versioning, data-protection, backup]

package cspm.aws.s3_versioning

import future.keywords.if

deny[finding] if {
    input.resource_type == "aws::s3::bucket"
    versioning := input.raw.Versioning
    versioning.Status != "Enabled"
    finding := {
        "rule_id": "aws-s3-versioning-disabled",
        "title": "S3 bucket versioning is not enabled",
        "severity": "MEDIUM",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": sprintf("S3 bucket '%v' does not have versioning enabled. Objects cannot be recovered after deletion or overwrite.", [input.name]),
        "remediation": "Enable versioning on the S3 bucket to protect against accidental deletion and ransomware.",
    }
}

deny[finding] if {
    input.resource_type == "aws::s3::bucket"
    not input.raw.Versioning
    finding := {
        "rule_id": "aws-s3-versioning-disabled",
        "title": "S3 bucket versioning is not enabled",
        "severity": "MEDIUM",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": sprintf("S3 bucket '%v' does not have versioning enabled. Objects cannot be recovered after deletion or overwrite.", [input.name]),
        "remediation": "Enable versioning on the S3 bucket to protect against accidental deletion and ransomware.",
    }
}
