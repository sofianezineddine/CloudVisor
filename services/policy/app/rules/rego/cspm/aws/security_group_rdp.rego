# METADATA
# title: "Security Group Allows Unrestricted RDP Access"
# description: "Security group allows inbound RDP access from anywhere (0.0.0.0/0)"
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::ec2::security-group
# compliance:
#   - framework: CIS-AWS
#     control: "4.2"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: PCI-DSS
#     control: "1.3"
# remediation: "Restrict RDP access: AWS Console > EC2 > Security Groups > Group > Inbound rules > Edit > Change source from 0.0.0.0/0 to specific IP ranges"

package cloudvisor.cspm.aws.security_group_rdp

import future.keywords

deny[finding] {
    input.resource_type == "aws::ec2::security-group"
    
    # Check inbound rules for unrestricted RDP access
    some rule in input.raw.IpPermissions
    
    # RDP port 3389
    rule.FromPort == 3389
    rule.ToPort == 3389
    rule.IpProtocol == "tcp"
    
    # Check for unrestricted access (0.0.0.0/0)
    some ip_range in rule.IpRanges
    ip_range.CidrIp == "0.0.0.0/0"
    
    finding := {
        "rule_id": "aws-sg-rdp-unrestricted",
        "title": "Security group allows unrestricted RDP access",
        "description": sprintf("Security group '%s' allows RDP access from anywhere (0.0.0.0/0)", [input.name]),
        "severity": "HIGH",
        "remediation": "Restrict RDP access to specific IP addresses or ranges instead of 0.0.0.0/0",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "4.2"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "PCI-DSS", "control": "1.3"}
        ]
    }
}