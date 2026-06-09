# METADATA
# title: "IAM user does not have MFA enabled"
# description: "An IAM user with console access does not have multi-factor authentication (MFA) enabled. Without MFA, a compromised password is sufficient to gain full access to the account."
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::iam::user
# compliance:
#   - framework: CIS-AWS
#     control: "1.10"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: PCI-DSS
#     control: "8.4.2"
#   - framework: NIST-800-53
#     control: "IA-2"
# remediation: "Enable MFA for all IAM users with console access. Use virtual MFA devices, hardware MFA tokens, or FIDO security keys. Consider enforcing MFA via an IAM policy that denies all actions unless MFA is present."
# version: "1.0.0"
# tags: [iam, mfa, authentication, account-security]

package cspm.aws.iam_mfa_all_users

deny[finding] if {
    input.resource_type == "aws::iam::user"
    input.raw.PasswordLastUsed
    not input.raw.MFAEnabled
    finding := {
        "rule_id": "aws-iam-user-no-mfa",
        "title": "IAM user with console access does not have MFA enabled",
        "severity": "HIGH",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": sprintf("IAM user '%v' has console access but MFA is not enabled. A compromised password grants full account access.", [input.name]),
        "remediation": "Enable MFA for this IAM user. Enforce MFA via an IAM policy that denies actions without MFA.",
    }
}
