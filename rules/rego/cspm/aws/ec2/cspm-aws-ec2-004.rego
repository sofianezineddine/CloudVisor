# METADATA
# title: Security Group Allows RDP from 0.0.0.0/0
# description: A security group allows unrestricted inbound RDP access (port 3389) from the internet, exposing Windows instances to attacks
# severity: CRITICAL
# category: ec2
# provider: aws
# resource_type: aws::ec2::security_group
# remediation: Restrict RDP access to specific trusted IP ranges or use AWS Systems Manager Session Manager instead
# compliance: CIS-AWS:5.3, SOC2:CC6.1, PCI-DSS:1.2.1
package cspm.aws.ec2

import future.keywords

deny[finding] {
    input.resource_type == "aws::ec2::security_group"
    some perm in input.raw.IpPermissions
    perm.FromPort <= 3389
    perm.ToPort >= 3389
    perm.IpProtocol == "tcp"
    some range in perm.IpRanges
    range.CidrIp == "0.0.0.0/0"
    finding := {
        "rule_id": "cspm-aws-ec2-004",
        "title": "Security Group Allows RDP from 0.0.0.0/0",
        "severity": "CRITICAL",
        "description": "A security group allows unrestricted inbound RDP access (port 3389) from the internet via IPv4",
        "remediation": "Restrict RDP access to specific trusted IP ranges or use AWS Systems Manager Session Manager instead",
    }
}

deny[finding] {
    input.resource_type == "aws::ec2::security_group"
    some perm in input.raw.IpPermissions
    perm.FromPort <= 3389
    perm.ToPort >= 3389
    perm.IpProtocol == "tcp"
    some range in perm.Ipv6Ranges
    range.CidrIpv6 == "::/0"
    finding := {
        "rule_id": "cspm-aws-ec2-004",
        "title": "Security Group Allows RDP from ::/0",
        "severity": "CRITICAL",
        "description": "A security group allows unrestricted inbound RDP access (port 3389) from the internet via IPv6",
        "remediation": "Restrict RDP access to specific trusted IP ranges or use AWS Systems Manager Session Manager instead",
    }
}
