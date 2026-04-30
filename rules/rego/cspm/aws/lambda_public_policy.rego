# METADATA
# title: Lambda function has resource-based policy allowing public invocation
# description: Lambda function policy allows invocation from any AWS principal (*), exposing it publicly.
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::lambda::function
# remediation: Remove the wildcard principal from the Lambda resource-based policy. Restrict invocation to specific services or accounts.
# version: 1.0.0

package cloudvisor.cspm.aws_lambda_public_policy

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::lambda::function"
    policy := input.resource.raw.Policy
    statement := policy.Statement[_]
    statement.Effect == "Allow"
    statement.Principal == "*"
    msg := sprintf("Lambda function '%v' has a resource-based policy allowing public invocation", [input.resource.name])
}
