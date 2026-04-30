# METADATA
# title: "EC2 Instance Uses IMDSv1"
# description: "EC2 instance uses Instance Metadata Service version 1, which is vulnerable to SSRF attacks"
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::ec2::instance
# compliance:
#   - framework: CIS-AWS
#     control: "2.2.1"
#   - framework: SOC2
#     control: "CC6.1"
# remediation: "Configure EC2 instance to require IMDSv2: AWS Console > EC2 > Instance > Actions > Instance settings > Modify instance metadata options > IMDSv2 required"

package cloudvisor.cspm.aws.ec2_imdsv1

import future.keywords

deny[finding] {
    input.resource_type == "aws::ec2::instance"
    
    # Check if instance metadata options exist
    metadata_options := input.raw.MetadataOptions
    
    # If no metadata options, defaults to IMDSv1 (vulnerable)
    not metadata_options
    
    finding := {
        "rule_id": "aws-ec2-imdsv1-default",
        "title": "EC2 instance uses default IMDSv1",
        "description": sprintf("EC2 instance '%s' uses default Instance Metadata Service v1, which is vulnerable to SSRF attacks", [input.name]),
        "severity": "HIGH",
        "remediation": "Configure the instance to require IMDSv2 for enhanced security",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.2.1"},
            {"framework": "SOC2", "control": "CC6.1"}
        ]
    }
}

deny[finding] {
    input.resource_type == "aws::ec2::instance"
    
    # Check if IMDSv1 is explicitly enabled
    metadata_options := input.raw.MetadataOptions
    metadata_options
    
    # HttpTokens "optional" means IMDSv1 is allowed
    metadata_options.HttpTokens == "optional"
    
    finding := {
        "rule_id": "aws-ec2-imdsv1-enabled",
        "title": "EC2 instance allows IMDSv1",
        "description": sprintf("EC2 instance '%s' is configured to allow IMDSv1, which is vulnerable to SSRF attacks", [input.name]),
        "severity": "HIGH",
        "remediation": "Set HttpTokens to 'required' to enforce IMDSv2 only",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.2.1"},
            {"framework": "SOC2", "control": "CC6.1"}
        ]
    }
}