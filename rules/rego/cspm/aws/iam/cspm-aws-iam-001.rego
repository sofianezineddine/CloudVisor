# METADATA
# title: Root Account MFA Disabled
# description: The root AWS account does not have MFA enabled, leaving it vulnerable to unauthorized access
# severity: CRITICAL
# category: iam
# provider: aws
# resource_type: aws::iam::root_account
# remediation: Enable MFA on the root account via the IAM console under Security Credentials
# compliance: CIS-AWS:1.1, SOC2:CC6.1, PCI-DSS:8.3
package cspm.aws.iam

import future.keywords

deny[finding] {
    input.resource_type == "aws::iam::root_account"
    not input.raw.mfa_active
    finding := {
        "rule_id": "cspm-aws-iam-001",
        "title": "Root Account MFA Disabled",
        "severity": "CRITICAL",
        "description": "The root AWS account does not have MFA enabled, leaving it vulnerable to unauthorized access",
        "remediation": "Enable MFA on the root account via the IAM console under Security Credentials",
    }
}
