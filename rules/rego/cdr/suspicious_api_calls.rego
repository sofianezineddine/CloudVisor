# METADATA
# title: Suspicious IAM privilege escalation detected
# description: CloudTrail event indicates potential IAM privilege escalation attempt.
# severity: CRITICAL
# category: cdr
# provider: aws
# resource_type: aws::cloudtrail::event
# remediation: Investigate the IAM user/role that performed this action. Revoke if unauthorized.
# version: 1.0.0

package cloudvisor.cdr.suspicious_api_calls

import future.keywords.if

# Privilege escalation via IAM policy attachment
deny[msg] if {
    input.resource.resource_type == "aws::cloudtrail::event"
    input.resource.raw.eventName == "AttachUserPolicy"
    input.resource.raw.requestParameters.policyArn == "arn:aws:iam::aws:policy/AdministratorAccess"
    msg := sprintf("Potential privilege escalation: AdministratorAccess policy attached by '%v'",
        [input.resource.raw.userIdentity.arn])
}

# Root account usage
deny[msg] if {
    input.resource.resource_type == "aws::cloudtrail::event"
    input.resource.raw.userIdentity.type == "Root"
    input.resource.raw.eventName != "ConsoleLogin"
    msg := sprintf("Root account used for API call: %v", [input.resource.raw.eventName])
}
