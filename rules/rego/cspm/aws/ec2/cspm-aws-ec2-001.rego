# METADATA
# title: EC2 AMI Is Publicly Accessible
# description: An EC2 Amazon Machine Image (AMI) is marked as public, potentially exposing sensitive data or configurations
# severity: HIGH
# category: ec2
# provider: aws
# resource_type: aws::ec2::image
# remediation: Make the AMI private by modifying its launch permissions to remove public access
# compliance: CIS-AWS:2.3.1, SOC2:CC6.1
package cspm.aws.ec2

deny[finding] if {
    input.resource_type == "aws::ec2::image"
    input.raw.Public == true
    finding := {
        "rule_id": "cspm-aws-ec2-001",
        "title": "EC2 AMI Is Publicly Accessible",
        "severity": "HIGH",
        "description": "An EC2 Amazon Machine Image (AMI) is marked as public, potentially exposing sensitive data or configurations",
        "remediation": "Make the AMI private by modifying its launch permissions to remove public access",
    }
}
