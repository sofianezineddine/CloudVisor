# METADATA
# title: Over-Permissive IAM Policy with Wildcard Actions
# description: An IAM policy contains a statement that allows all actions or all resources, granting excessive permissions
# severity: HIGH
# category: iam
# provider: aws
# resource_type: aws::iam::policy
# remediation: Replace wildcard actions and resources with specific permissions following the principle of least privilege
# compliance: CIS-AWS:1.16, SOC2:CC6.3
package cspm.aws.iam

import future.keywords

deny[finding] {
    input.resource_type == "aws::iam::policy"
    some stmt in input.raw.PolicyDocument.Statement
    stmt.Effect == "Allow"
    stmt.Action == "*"
    finding := {
        "rule_id": "cspm-aws-iam-003",
        "title": "Over-Permissive IAM Policy with Wildcard Actions",
        "severity": "HIGH",
        "description": "An IAM policy contains a statement that allows all actions, granting excessive permissions",
        "remediation": "Replace wildcard actions with specific permissions following the principle of least privilege",
    }
}

deny[finding] {
    input.resource_type == "aws::iam::policy"
    some stmt in input.raw.PolicyDocument.Statement
    stmt.Effect == "Allow"
    stmt.Resource == "*"
    stmt.Action == "*"
    finding := {
        "rule_id": "cspm-aws-iam-003",
        "title": "Over-Permissive IAM Policy with Wildcard Actions",
        "severity": "HIGH",
        "description": "An IAM policy contains a statement that allows all actions on all resources, granting excessive permissions",
        "remediation": "Replace wildcard actions and resources with specific permissions following the principle of least privilege",
    }
}
