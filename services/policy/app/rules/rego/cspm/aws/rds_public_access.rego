# METADATA
# title: "RDS Instance Publicly Accessible"
# description: "RDS database instance is configured to be publicly accessible"
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::rds::db-instance
# compliance:
#   - framework: CIS-AWS
#     control: "2.3.1"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: PCI-DSS
#     control: "1.3"
# remediation: "Disable public accessibility: AWS Console > RDS > Databases > Instance > Modify > Connectivity > Public access > No"

package cloudvisor.cspm.aws.rds_public_access

import future.keywords

deny[finding] {
    input.resource_type == "aws::rds::db-instance"
    
    # Check if RDS instance is publicly accessible
    publicly_accessible := input.raw.PubliclyAccessible
    publicly_accessible == true
    
    finding := {
        "rule_id": "aws-rds-publicly-accessible",
        "title": "RDS instance is publicly accessible",
        "description": sprintf("RDS instance '%s' is configured to be publicly accessible from the internet", [input.name]),
        "severity": "CRITICAL",
        "remediation": "Disable public accessibility for this RDS instance and access it through private subnets only",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.3.1"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "PCI-DSS", "control": "1.3"}
        ]
    }
}