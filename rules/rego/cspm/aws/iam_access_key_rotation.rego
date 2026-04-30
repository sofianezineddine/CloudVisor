# METADATA
# title: "IAM access keys not rotated in 90 days"
# description: "IAM user access keys that have not been rotated in the last 90 days pose a security risk. Stale credentials increase the window of exposure if they are compromised."
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::iam::user
# compliance:
#   - framework: CIS-AWS
#     control: "1.14"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: PCI-DSS
#     control: "8.2.4"
# remediation: "Rotate IAM access keys every 90 days. Disable or delete access keys that are no longer needed. Use AWS IAM Access Analyzer to identify stale credentials."
# version: "1.0.0"
# tags: [iam, access-keys, rotation, credentials]

package cspm.aws.iam_access_key_rotation

import future.keywords.if

deny[finding] if {
    input.resource_type == "aws::iam::user"
    key := input.raw.AccessKeys[_]
    key.Status == "Active"
    create_date := key.CreateDate
    # Check if key is older than 90 days (7776000 seconds)
    now := time.now_ns() / 1000000000
    key_age_seconds := now - time.parse_rfc3339_ns(create_date) / 1000000000
    key_age_seconds > 7776000
    finding := {
        "rule_id": "aws-iam-access-key-rotation",
        "title": "IAM access key not rotated in 90 days",
        "severity": "CRITICAL",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": sprintf("IAM user '%v' has an active access key that has not been rotated in over 90 days.", [input.name]),
        "remediation": "Rotate IAM access keys every 90 days. Disable or delete access keys that are no longer needed.",
    }
}
