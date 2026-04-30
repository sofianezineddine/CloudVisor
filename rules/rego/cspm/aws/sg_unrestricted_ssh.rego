# METADATA
# title: Security group allows unrestricted SSH access
# description: Security group has an inbound rule allowing SSH (port 22) from 0.0.0.0/0.
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::ec2::securitygroup
# remediation: Restrict SSH access to specific IP ranges. Use AWS Systems Manager Session Manager instead.
# version: 1.0.0

package cloudvisor.cspm.aws_sg_unrestricted_ssh

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::ec2::securitygroup"
    rule := input.resource.raw.IpPermissions[_]
    rule.FromPort <= 22
    rule.ToPort >= 22
    range := rule.IpRanges[_]
    range.CidrIp == "0.0.0.0/0"
    msg := sprintf("Security group '%v' allows unrestricted SSH from 0.0.0.0/0", [input.resource.name])
}

deny[msg] if {
    input.resource.resource_type == "aws::ec2::securitygroup"
    rule := input.resource.raw.IpPermissions[_]
    rule.FromPort <= 22
    rule.ToPort >= 22
    range := rule.Ipv6Ranges[_]
    range.CidrIpv6 == "::/0"
    msg := sprintf("Security group '%v' allows unrestricted SSH from ::/0 (IPv6)", [input.resource.name])
}
