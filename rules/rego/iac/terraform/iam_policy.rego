# METADATA
# title: IAM Policy Grants Overly Permissive Access
# description: Terraform IAM policy uses wildcard actions or resources, violating least privilege.
# severity: HIGH
# category: iac
# provider: aws
# resource_type: aws_iam_policy
# version: 1.0.0

package cloudvisor.iac.terraform.iam_policy

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# Dangerous actions that should never use wildcards
dangerous_action_prefixes := {"iam:*", "s3:*", "ec2:*", "sts:*", "kms:*", "lambda:*", "rds:*"}

violation contains finding if {
    input.resource.type == "aws_iam_policy"
    properties := input.resource.properties
    policy_doc := properties.policy
    statement := policy_doc.Statement[_]
    statement.Effect == "Allow"
    statement.Action[_] == "*"
    statement.Resource[_] == "*"
    finding := {
        "rule_id": "iac.terraform.iam-admin-access",
        "severity": "CRITICAL",
        "title": "IAM Policy Grants Full Administrator Access",
        "description": sprintf("IAM policy '%v' grants Action:* on Resource:*. This is equivalent to full administrator access and violates the principle of least privilege.", [input.resource.identifier]),
        "remediation": "Replace the wildcard action and resource with specific actions and resource ARNs required for the workload. Use AWS Access Analyzer to determine minimum required permissions.",
    }
}

violation contains finding if {
    input.resource.type == "aws_iam_policy"
    properties := input.resource.properties
    policy_doc := properties.policy
    statement := policy_doc.Statement[_]
    statement.Effect == "Allow"
    action := statement.Action[_]
    action in dangerous_action_prefixes
    finding := {
        "rule_id": "iac.terraform.iam-wildcard-service",
        "severity": "HIGH",
        "title": "IAM Policy Uses Wildcard Service Actions",
        "description": sprintf("IAM policy '%v' grants wildcard actions '%v'. This provides more permissions than typically needed.", [input.resource.identifier, action]),
        "remediation": sprintf("Replace '%v' with specific actions required for the workload (e.g., 's3:GetObject', 's3:PutObject' instead of 's3:*').", [action]),
    }
}

violation contains finding if {
    input.resource.type == "aws_iam_policy"
    properties := input.resource.properties
    policy_doc := properties.policy
    statement := policy_doc.Statement[_]
    statement.Effect == "Allow"
    statement.Resource[_] == "*"
    not statement.Action[_] == "*"
    finding := {
        "rule_id": "iac.terraform.iam-wildcard-resource",
        "severity": "MEDIUM",
        "title": "IAM Policy Uses Wildcard Resource",
        "description": sprintf("IAM policy '%v' grants permissions on all resources (Resource: *). Scope permissions to specific resource ARNs where possible.", [input.resource.identifier]),
        "remediation": "Replace Resource: * with specific resource ARNs. Use conditions to further restrict access scope (e.g., aws:RequestedRegion, aws:ResourceTag).",
    }
}

violation contains finding if {
    input.resource.type == "aws_iam_role"
    properties := input.resource.properties
    assume_role_policy := properties.assume_role_policy
    statement := assume_role_policy.Statement[_]
    statement.Effect == "Allow"
    principal := statement.Principal
    principal.AWS == "*"
    finding := {
        "rule_id": "iac.terraform.iam-trust-any-principal",
        "severity": "CRITICAL",
        "title": "IAM Role Trusts Any AWS Principal",
        "description": sprintf("IAM role '%v' has a trust policy that allows any AWS principal (Principal: *) to assume it. This is extremely dangerous.", [input.resource.identifier]),
        "remediation": "Restrict the trust policy Principal to specific AWS account IDs or IAM role/user ARNs. Add conditions like aws:PrincipalOrgID or sts:ExternalId.",
    }
}
