# METADATA
# title: Access Key Not Rotated in 90 Days
# description: An IAM access key has not been rotated in over 90 days, increasing the risk of credential compromise
# severity: HIGH
# category: iam
# provider: aws
# resource_type: aws::iam::access_key
# remediation: Rotate the access key by creating a new key, updating applications, and deleting the old key
# compliance: CIS-AWS:1.14, SOC2:CC6.1
package cspm.aws.iam

import future.keywords

deny[finding] {
    input.resource_type == "aws::iam::access_key"
    input.raw.status == "Active"
    input.raw.key_age_days > 90
    finding := {
        "rule_id": "cspm-aws-iam-002",
        "title": "Access Key Not Rotated in 90 Days",
        "severity": "HIGH",
        "description": "An IAM access key has not been rotated in over 90 days, increasing the risk of credential compromise",
        "remediation": "Rotate the access key by creating a new key, updating applications, and deleting the old key",
    }
}

deny[finding] {
    input.resource_type == "aws::iam::access_key"
    input.raw.status == "Active"
    not input.raw.last_rotated
    finding := {
        "rule_id": "cspm-aws-iam-002",
        "title": "Access Key Not Rotated in 90 Days",
        "severity": "HIGH",
        "description": "An IAM access key has not been rotated in over 90 days, increasing the risk of credential compromise",
        "remediation": "Rotate the access key by creating a new key, updating applications, and deleting the old key",
    }
}
