# METADATA
# title: Unused IAM Credentials (No Login in 90 Days)
# description: An IAM user has not logged in for over 90 days, indicating unused credentials that should be removed
# severity: MEDIUM
# category: iam
# provider: aws
# resource_type: aws::iam::user
# remediation: Disable or remove IAM users that have not logged in for 90 or more days
# compliance: CIS-AWS:1.12, SOC2:CC6.2
package cspm.aws.iam

deny[finding] if {
    input.resource_type == "aws::iam::user"
    input.raw.password_last_used_days > 90
    finding := {
        "rule_id": "cspm-aws-iam-004",
        "title": "Unused IAM Credentials (No Login in 90 Days)",
        "severity": "MEDIUM",
        "description": "An IAM user has not logged in for over 90 days, indicating unused credentials that should be removed",
        "remediation": "Disable or remove IAM users that have not logged in for 90 or more days",
    }
}

deny[finding] if {
    input.resource_type == "aws::iam::user"
    not input.raw.password_last_used
    finding := {
        "rule_id": "cspm-aws-iam-004",
        "title": "Unused IAM Credentials (No Login in 90 Days)",
        "severity": "MEDIUM",
        "description": "An IAM user has never logged in, indicating unused credentials that should be removed",
        "remediation": "Disable or remove IAM users that have never logged in or have not logged in for 90 or more days",
    }
}
