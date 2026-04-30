# METADATA
# title: Security group allows unrestricted RDP access
# description: Security group has an inbound rule allowing RDP (port 3389) from 0.0.0.0/0.
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::ec2::securitygroup
# remediation: Restrict RDP access to specific IP ranges or use a VPN/bastion host.
# version: 1.0.0

package cloudvisor.cspm.aws_sg_unrestricted_rdp

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::ec2::securitygroup"
    rule := input.resource.raw.IpPermissions[_]
    rule.FromPort <= 3389
    rule.ToPort >= 3389
    range := rule.IpRanges[_]
    range.CidrIp == "0.0.0.0/0"
    msg := sprintf("Security group '%v' allows unrestricted RDP from 0.0.0.0/0", [input.resource.name])
}
