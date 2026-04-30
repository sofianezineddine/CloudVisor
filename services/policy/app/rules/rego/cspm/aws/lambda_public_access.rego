# METADATA
# title: "Lambda Function Allows Public Invocation"
# description: "Lambda function has resource-based policy allowing public invocation"
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::lambda::function
# compliance:
#   - framework: CIS-AWS
#     control: "2.4.1"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: PCI-DSS
#     control: "1.3"
# remediation: "Remove public access: AWS Console > Lambda > Function > Configuration > Permissions > Resource-based policy > Remove public statements"

package cloudvisor.cspm.aws.lambda_public_access

import future.keywords

deny[finding] {
    input.resource_type == "aws::lambda::function"
    
    # Check if function has a resource-based policy
    policy := input.raw.Policy
    policy
    
    # Parse the policy document
    policy_doc := json.unmarshal(policy)
    
    # Check each statement for public access
    some statement in policy_doc.Statement
    statement.Effect == "Allow"
    
    # Check for wildcard principal (public access)
    principal := statement.Principal
    principal == "*"
    
    finding := {
        "rule_id": "aws-lambda-public-access-wildcard",
        "title": "Lambda function allows public invocation",
        "description": sprintf("Lambda function '%s' has resource-based policy allowing public invocation", [input.name]),
        "severity": "HIGH",
        "remediation": "Remove or restrict the resource-based policy to prevent public access to the Lambda function",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.4.1"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "PCI-DSS", "control": "1.3"}
        ]
    }
}

deny[finding] {
    input.resource_type == "aws::lambda::function"
    
    # Check if function has a resource-based policy
    policy := input.raw.Policy
    policy
    
    # Parse the policy document
    policy_doc := json.unmarshal(policy)
    
    # Check each statement for AWS account wildcard
    some statement in policy_doc.Statement
    statement.Effect == "Allow"
    
    # Check for AWS account wildcard
    principal := statement.Principal.AWS
    principal == "*"
    
    finding := {
        "rule_id": "aws-lambda-public-access-aws-wildcard",
        "title": "Lambda function allows access from any AWS account",
        "description": sprintf("Lambda function '%s' allows invocation from any AWS account", [input.name]),
        "severity": "MEDIUM",
        "remediation": "Restrict the resource-based policy to specific AWS accounts or principals",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.4.1"},
            {"framework": "SOC2", "control": "CC6.1"}
        ]
    }
}