# METADATA
# title: EC2 instance does not enforce IMDSv2
# description: EC2 instance allows IMDSv1 which is vulnerable to SSRF attacks that can steal credentials.
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::ec2::instance
# remediation: Set HttpTokens to 'required' in the instance metadata options to enforce IMDSv2.
# version: 1.0.0

package cloudvisor.cspm.aws_ec2_imdsv2

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::ec2::instance"
    input.resource.raw.MetadataOptions.HttpTokens != "required"
    msg := sprintf("EC2 instance '%v' does not enforce IMDSv2 (HttpTokens != required)", [input.resource.name])
}
