package cloudvisor.cspm.aws.iam_no_mfa

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::iam::user"
    input.resource.name != "root"
    not input.resource.raw.MFAActive
    msg := sprintf("IAM user '%v' does not have MFA enabled", [input.resource.name])
}
