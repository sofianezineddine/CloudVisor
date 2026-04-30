# METADATA
# title: SNS topic has public access policy
# description: SNS topic policy allows subscriptions or publications from any AWS principal (*).
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::sns::topic
# remediation: Update the SNS topic policy to restrict access to specific AWS accounts or services.
# version: 1.0.0

package cloudvisor.cspm.aws_sns_public_policy

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::sns::topic"
    policy := input.resource.raw.Policy
    statement := policy.Statement[_]
    statement.Effect == "Allow"
    statement.Principal == "*"
    msg := sprintf("SNS topic '%v' has a policy allowing public access", [input.resource.name])
}
