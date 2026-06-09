# METADATA
# title: "Security group allows all inbound traffic (0.0.0.0/0)"
# description: "Security group has an inbound rule allowing all traffic (-1) from 0.0.0.0/0. This completely removes network-level protection and exposes all ports and protocols to the internet."
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::ec2::securitygroup
# compliance:
#   - framework: CIS-AWS
#     control: "5.1"
#   - framework: SOC2
#     control: "CC6.6"
#   - framework: PCI-DSS
#     control: "1.2.1"
#   - framework: NIST-800-53
#     control: "SC-7"
# remediation: "Remove the allow-all inbound rule. Apply the principle of least privilege: only allow traffic on specific ports from specific IP ranges that are required for the application to function."
# version: "1.0.0"
# tags: [security-group, network, unrestricted, critical, all-traffic]

package cspm.aws.sg_unrestricted_all

deny[finding] if {
    input.resource_type == "aws::ec2::securitygroup"
    rule := input.raw.IpPermissions[_]
    rule.IpProtocol == "-1"
    range := rule.IpRanges[_]
    range.CidrIp == "0.0.0.0/0"
    finding := {
        "rule_id": "aws-sg-unrestricted-all-traffic",
        "title": "Security group allows all inbound traffic from 0.0.0.0/0",
        "severity": "CRITICAL",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": "Security group allows all inbound traffic from the internet (0.0.0.0/0). All ports and protocols are exposed.",
        "remediation": "Remove the allow-all rule and restrict inbound traffic to only required ports and IP ranges.",
    }
}

deny[finding] if {
    input.resource_type == "aws::ec2::securitygroup"
    rule := input.raw.IpPermissions[_]
    rule.IpProtocol == "-1"
    range := rule.Ipv6Ranges[_]
    range.CidrIpv6 == "::/0"
    finding := {
        "rule_id": "aws-sg-unrestricted-all-traffic-ipv6",
        "title": "Security group allows all inbound traffic from ::/0 (IPv6)",
        "severity": "CRITICAL",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": "Security group allows all inbound traffic from the internet via IPv6 (::/0). All ports and protocols are exposed.",
        "remediation": "Remove the allow-all IPv6 rule and restrict inbound traffic to only required ports and IP ranges.",
    }
}
