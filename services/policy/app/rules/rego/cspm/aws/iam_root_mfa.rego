# METADATA
# title: "Root Account MFA Not Enabled"
# description: "AWS root account does not have multi-factor authentication enabled"
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::iam::account-summary
# compliance:
#   - framework: CIS-AWS
#     control: "1.5"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: NIST-800-53
#     control: "IA-2(1)"
# remediation: "Enable MFA for root account: AWS Console > IAM > Dashboard > Security recommendations > Add MFA"

package cloudvisor.cspm.aws.iam_root_mfa

import future.keywords

deny[finding] {
    input.resource_type == "aws::iam::account-summary"
    
    # Check if root account has MFA enabled
    account_mfa_enabled := input.raw.AccountMFAEnabled
    account_mfa_enabled == 0
    
    finding := {
        "rule_id": "aws-iam-root-mfa-disabled",
        "title": "Root account MFA is not enabled",
        "description": "AWS root account does not have multi-factor authentication enabled, creating a significant security risk",
        "severity": "CRITICAL",
        "remediation": "Enable MFA for the AWS root account immediately. Use a hardware MFA device or virtual MFA application",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "1.5"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "NIST-800-53", "control": "IA-2(1)"}
        ]
    }
}