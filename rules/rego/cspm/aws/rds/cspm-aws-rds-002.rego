# METADATA
# title: RDS Instance Storage Not Encrypted
# description: An RDS database instance does not have storage encryption enabled, leaving data at rest unprotected
# severity: HIGH
# category: rds
# provider: aws
# resource_type: aws::rds::instance
# remediation: Create an encrypted snapshot of the RDS instance and restore it as a new encrypted instance
# compliance: CIS-AWS:2.3.1, SOC2:CC6.7, PCI-DSS:3.4
package cspm.aws.rds

import future.keywords

deny[finding] {
    input.resource_type == "aws::rds::instance"
    not input.raw.StorageEncrypted
    finding := {
        "rule_id": "cspm-aws-rds-002",
        "title": "RDS Instance Storage Not Encrypted",
        "severity": "HIGH",
        "description": "An RDS database instance does not have storage encryption enabled, leaving data at rest unprotected",
        "remediation": "Create an encrypted snapshot of the RDS instance and restore it as a new encrypted instance",
    }
}
