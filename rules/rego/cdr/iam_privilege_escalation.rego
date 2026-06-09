# METADATA
# title: IAM privilege escalation attempt detected
# description: CloudTrail event indicates a potential IAM privilege escalation attempt.
# severity: CRITICAL
# category: cdr
# provider: aws
# resource_type: aws::cloudtrail::event
# remediation: Investigate the IAM principal that performed this action. Revoke if unauthorized.
# version: 1.0.0

package cloudvisor.cdr.iam_privilege_escalation

# Attaching AdministratorAccess policy
deny[msg] if {
    input.resource.resource_type == "aws::cloudtrail::event"
    input.resource.raw.eventName == "AttachUserPolicy"
    input.resource.raw.requestParameters.policyArn == "arn:aws:iam::aws:policy/AdministratorAccess"
    msg := sprintf("AdministratorAccess policy attached to user by '%v'",
        [input.resource.raw.userIdentity.arn])
}

# Creating new IAM user with admin access
deny[msg] if {
    input.resource.resource_type == "aws::cloudtrail::event"
    input.resource.raw.eventName == "CreateUser"
    msg := sprintf("New IAM user created by '%v': %v",
        [input.resource.raw.userIdentity.arn, input.resource.raw.requestParameters.userName])
}

# Assuming a role with admin access
deny[msg] if {
    input.resource.resource_type == "aws::cloudtrail::event"
    input.resource.raw.eventName == "AssumeRole"
    contains(input.resource.raw.requestParameters.roleArn, "Admin")
    msg := sprintf("Admin role assumed by '%v': %v",
        [input.resource.raw.userIdentity.arn, input.resource.raw.requestParameters.roleArn])
}
