package cloudvisor.cspm.aws.sg_unrestricted_all

import future.keywords.if
import future.keywords.in

deny[msg] if {
    input.resource.resource_type == "aws::ec2::security-group"
    some rule in input.resource.raw.IpPermissions
    rule.IpProtocol == "-1"
    some ip_range in rule.IpRanges
    ip_range.CidrIp == "0.0.0.0/0"
    msg := sprintf("Security group '%v' allows all traffic from anywhere (0.0.0.0/0)", [input.resource.name])
}
