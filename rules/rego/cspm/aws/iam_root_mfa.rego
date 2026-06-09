# METADATA
# title: IAM root account MFA not enabled
# description: The root AWS account does not have MFA enabled, creating a critical security risk.
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::iam::user
# remediation: Enable MFA on the root account immediately. Use a hardware MFA device for root.
# version: 1.0.0

package cloudvisor.cspm.aws_iam_root_mfa

deny[msg] if {
    input.resource.resource_type == "aws::iam::user"
    input.resource.name == "root"
    not input.resource.raw.MFAActive
    msg := "IAM root account does not have MFA enabled"
}
