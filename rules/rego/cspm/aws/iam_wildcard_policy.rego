# METADATA
# title: IAM policy grants wildcard (*) on all actions
# description: IAM policy contains a statement that allows all actions (*) on all resources (*), granting excessive permissions.
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::iam::policy
# remediation: Replace wildcard permissions with least-privilege policies. Use IAM Access Analyzer to generate least-privilege policies.
# version: 1.0.0

package cloudvisor.cspm.aws_iam_wildcard_policy

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::iam::policy"
    doc := input.resource.raw.PolicyDocument
    statement := doc.Statement[_]
    statement.Effect == "Allow"
    statement.Action == "*"
    statement.Resource == "*"
    msg := sprintf("IAM policy '%v' grants wildcard (*) on all actions and resources", [input.resource.name])
}
