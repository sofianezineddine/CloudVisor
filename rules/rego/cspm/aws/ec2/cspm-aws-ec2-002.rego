# METADATA
# title: EC2 Instance IMDSv2 Not Enforced
# description: The EC2 instance does not enforce IMDSv2 (Instance Metadata Service v2), leaving it vulnerable to SSRF attacks
# severity: HIGH
# category: ec2
# provider: aws
# resource_type: aws::ec2::instance
# remediation: Modify the instance metadata options to require HttpTokens to be set to required to enforce IMDSv2
# compliance: CIS-AWS:5.6, SOC2:CC6.1
package cspm.aws.ec2

deny[finding] if {
    input.resource_type == "aws::ec2::instance"
    input.raw.MetadataOptions.HttpTokens != "required"
    finding := {
        "rule_id": "cspm-aws-ec2-002",
        "title": "EC2 Instance IMDSv2 Not Enforced",
        "severity": "HIGH",
        "description": "The EC2 instance does not enforce IMDSv2, leaving it vulnerable to SSRF attacks that could expose instance metadata",
        "remediation": "Modify the instance metadata options to require HttpTokens to be set to required to enforce IMDSv2",
    }
}
