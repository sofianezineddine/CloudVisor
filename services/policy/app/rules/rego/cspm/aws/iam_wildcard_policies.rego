# METADATA
# title: "IAM Policy Grants Wildcard Permissions"
# description: "IAM policy grants wildcard (*) permissions on all actions or resources"
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::iam::policy
# compliance:
#   - framework: CIS-AWS
#     control: "1.16"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: NIST-800-53
#     control: "AC-6(1)"
# remediation: "Replace wildcard permissions with specific, least-privilege permissions"

package cloudvisor.cspm.aws.iam_wildcard_policies

import future.keywords

deny[finding] {
    input.resource_type == "aws::iam::policy"
    
    # Parse the policy document
    policy_doc := json.unmarshal(input.raw.PolicyVersionList[0].Document)
    
    # Check each statement for wildcard actions
    some statement in policy_doc.Statement
    statement.Effect == "Allow"
    
    # Check if Action contains wildcard
    actions := statement.Action
    some action in actions
    action == "*"
    
    finding := {
        "rule_id": "aws-iam-wildcard-actions",
        "title": "IAM policy grants wildcard actions",
        "description": sprintf("IAM policy '%s' grants wildcard (*) permissions on all actions", [input.name]),
        "severity": "HIGH",
        "remediation": "Replace wildcard actions with specific actions following the principle of least privilege",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "1.16"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "NIST-800-53", "control": "AC-6(1)"}
        ]
    }
}

deny[finding] {
    input.resource_type == "aws::iam::policy"
    
    # Parse the policy document
    policy_doc := json.unmarshal(input.raw.PolicyVersionList[0].Document)
    
    # Check each statement for wildcard resources
    some statement in policy_doc.Statement
    statement.Effect == "Allow"
    
    # Check if Resource contains wildcard
    resources := statement.Resource
    some resource in resources
    resource == "*"
    
    finding := {
        "rule_id": "aws-iam-wildcard-resources",
        "title": "IAM policy grants wildcard resources",
        "description": sprintf("IAM policy '%s' grants permissions on all resources (*)", [input.name]),
        "severity": "MEDIUM",
        "remediation": "Replace wildcard resources with specific resource ARNs",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "1.16"},
            {"framework": "SOC2", "control": "CC6.1"}
        ]
    }
}