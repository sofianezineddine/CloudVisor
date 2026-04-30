# METADATA
# title: IAM password policy is weak
# description: AWS account IAM password policy does not meet minimum security requirements.
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::iam::passwordpolicy
# remediation: Configure a strong IAM password policy with minimum length 14, complexity requirements, and rotation.
# version: 1.0.0

package cloudvisor.cspm.aws_iam_password_policy

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::iam::passwordpolicy"
    input.resource.raw.MinimumPasswordLength < 14
    msg := sprintf("IAM password policy minimum length is %v (should be >= 14)", [input.resource.raw.MinimumPasswordLength])
}

deny[msg] if {
    input.resource.resource_type == "aws::iam::passwordpolicy"
    not input.resource.raw.RequireUppercaseCharacters
    msg := "IAM password policy does not require uppercase characters"
}

deny[msg] if {
    input.resource.resource_type == "aws::iam::passwordpolicy"
    not input.resource.raw.RequireLowercaseCharacters
    msg := "IAM password policy does not require lowercase characters"
}

deny[msg] if {
    input.resource.resource_type == "aws::iam::passwordpolicy"
    not input.resource.raw.RequireNumbers
    msg := "IAM password policy does not require numbers"
}

deny[msg] if {
    input.resource.resource_type == "aws::iam::passwordpolicy"
    not input.resource.raw.RequireSymbols
    msg := "IAM password policy does not require symbols"
}
