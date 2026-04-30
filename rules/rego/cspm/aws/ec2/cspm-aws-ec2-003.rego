# METADATA
# title: Security Group Allows SSH from 0.0.0.0/0
# description: A security group allows unrestricted inbound SSH access (port 22) from the internet, exposing instances to brute force attacks
# severity: CRITICAL
# category: ec2
# provider: aws
# resource_type: aws::ec2::security_group
# remediation: Restrict SSH access to specific trusted IP ranges or use AWS Systems Manager Session Manager instead
# compliance: CIS-AWS:5.2, SOC2:CC6.1, PCI-DSS:1.2.1
package cspm.aws.ec2

import future.keywords

deny[finding] {
    input.resource_type == "aws::ec2::security_group"
    some perm in input.raw.IpPermissions
    perm.FromPort <= 22
    perm.ToPort >= 22
    perm.IpProtocol == "tcp"
    some range in perm.IpRanges
    range.CidrIp == "0.0.0.0/0"
    finding := {
        "rule_id": "cspm-aws-ec2-003",
        "title": "Security Group Allows SSH from 0.0.0.0/0",
        "severity": "CRITICAL",
        "description": "A security group allows unrestricted inbound SSH access (port 22) from the internet via IPv4",
        "remediation": "Restrict SSH access to specific trusted IP ranges or use AWS Systems Manager Session Manager instead",
    }
}

deny[finding] {
    input.resource_type == "aws::ec2::security_group"
    some perm in input.raw.IpPermissions
    perm.FromPort <= 22
    perm.ToPort >= 22
    perm.IpProtocol == "tcp"
    some range in perm.Ipv6Ranges
    range.CidrIpv6 == "::/0"
    finding := {
        "rule_id": "cspm-aws-ec2-003",
        "title": "Security Group Allows SSH from ::/0",
        "severity": "CRITICAL",
        "description": "A security group allows unrestricted inbound SSH access (port 22) from the internet via IPv6",
        "remediation": "Restrict SSH access to specific trusted IP ranges or use AWS Systems Manager Session Manager instead",
    }
}
