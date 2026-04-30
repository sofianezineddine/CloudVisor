# METADATA
# title: RDS Instance Publicly Accessible
# description: An RDS database instance is configured to be publicly accessible, exposing it to the internet
# severity: CRITICAL
# category: rds
# provider: aws
# resource_type: aws::rds::instance
# remediation: Modify the RDS instance to disable public accessibility and place it in a private subnet
# compliance: CIS-AWS:2.3.2, SOC2:CC6.1, PCI-DSS:1.3.2
package cspm.aws.rds

import future.keywords

deny[finding] {
    input.resource_type == "aws::rds::instance"
    input.raw.PubliclyAccessible == true
    finding := {
        "rule_id": "cspm-aws-rds-001",
        "title": "RDS Instance Publicly Accessible",
        "severity": "CRITICAL",
        "description": "An RDS database instance is configured to be publicly accessible, exposing it to the internet",
        "remediation": "Modify the RDS instance to disable public accessibility and place it in a private subnet",
    }
}
