# METADATA
# title: RDS Instance Backup Retention Period Less Than 7 Days
# description: An RDS database instance has a backup retention period of less than 7 days, risking data loss in case of failure
# severity: MEDIUM
# category: rds
# provider: aws
# resource_type: aws::rds::instance
# remediation: Modify the RDS instance to set the backup retention period to at least 7 days
# compliance: CIS-AWS:2.3.3, SOC2:A1.2
package cspm.aws.rds

import future.keywords

deny[finding] {
    input.resource_type == "aws::rds::instance"
    input.raw.BackupRetentionPeriod < 7
    finding := {
        "rule_id": "cspm-aws-rds-003",
        "title": "RDS Instance Backup Retention Period Less Than 7 Days",
        "severity": "MEDIUM",
        "description": "An RDS database instance has a backup retention period of less than 7 days, risking data loss in case of failure",
        "remediation": "Modify the RDS instance to set the backup retention period to at least 7 days",
    }
}
