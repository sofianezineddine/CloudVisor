# METADATA
# title: "Security Group Allows Unrestricted SSH Access"
# description: "Security group allows inbound SSH access from anywhere (0.0.0.0/0)"
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::ec2::security-group
# compliance:
#   - framework: CIS-AWS
#     control: "4.1"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: PCI-DSS
#     control: "1.3"
# remediation: "Restrict SSH access: AWS Console > EC2 > Security Groups > Group > Inbound rules > Edit > Change source from 0.0.0.0/0 to specific IP ranges"

package cloudvisor.cspm.aws.security_group_ssh

import future.keywords

deny[finding] {
    input.resource_type == "aws::ec2::security-group"
    
    # Check inbound rules for unrestricted SSH access
    some rule in input.raw.IpPermissions
    
    # SSH port 22
    rule.FromPort == 22
    rule.ToPort == 22
    rule.IpProtocol == "tcp"
    
    # Check for unrestricted access (0.0.0.0/0)
    some ip_range in rule.IpRanges
    ip_range.CidrIp == "0.0.0.0/0"
    
    finding := {
        "rule_id": "aws-sg-ssh-unrestricted",
        "title": "Security group allows unrestricted SSH access",
        "description": sprintf("Security group '%s' allows SSH access from anywhere (0.0.0.0/0)", [input.name]),
        "severity": "HIGH",
        "remediation": "Restrict SSH access to specific IP addresses or ranges instead of 0.0.0.0/0",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "4.1"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "PCI-DSS", "control": "1.3"}
        ]
    }
}

deny[finding] {
    input.resource_type == "aws::ec2::security-group"
    
    # Check inbound rules for unrestricted SSH access via IPv6
    some rule in input.raw.IpPermissions
    
    # SSH port 22
    rule.FromPort == 22
    rule.ToPort == 22
    rule.IpProtocol == "tcp"
    
    # Check for unrestricted IPv6 access (::/0)
    some ipv6_range in rule.Ipv6Ranges
    ipv6_range.CidrIpv6 == "::/0"
    
    finding := {
        "rule_id": "aws-sg-ssh-unrestricted-ipv6",
        "title": "Security group allows unrestricted SSH access via IPv6",
        "description": sprintf("Security group '%s' allows SSH access from anywhere via IPv6 (::/0)", [input.name]),
        "severity": "HIGH",
        "remediation": "Restrict SSH access to specific IPv6 addresses or ranges instead of ::/0",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "4.1"},
            {"framework": "SOC2", "control": "CC6.1"}
        ]
    }
}