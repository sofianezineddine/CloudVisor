# METADATA
# title: SQS queue has public access policy
# description: SQS queue policy allows access from any AWS principal (*), making it publicly accessible.
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::sqs::queue
# remediation: Update the SQS queue policy to restrict access to specific AWS accounts, roles, or services.
# version: 1.0.0

package cloudvisor.cspm.aws_sqs_public_policy

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::sqs::queue"
    policy := input.resource.raw.Policy
    statement := policy.Statement[_]
    statement.Effect == "Allow"
    statement.Principal == "*"
    msg := sprintf("SQS queue '%v' has a policy allowing public access", [input.resource.name])
}
