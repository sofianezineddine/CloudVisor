# METADATA
# title: "RDS Instance Automated Backups Disabled"
# description: "RDS database instance does not have automated backups enabled"
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::rds::db-instance
# compliance:
#   - framework: CIS-AWS
#     control: "2.3.2"
#   - framework: SOC2
#     control: "CC5.2"
# remediation: "Enable automated backups: AWS Console > RDS > Databases > Instance > Modify > Backup > Backup retention period > 7 days or more"

package cloudvisor.cspm.aws.rds_backup

import future.keywords

deny[finding] {
    input.resource_type == "aws::rds::db-instance"
    
    # Check if automated backups are disabled
    backup_retention_period := input.raw.BackupRetentionPeriod
    backup_retention_period == 0
    
    finding := {
        "rule_id": "aws-rds-backup-disabled",
        "title": "RDS instance automated backups are disabled",
        "description": sprintf("RDS instance '%s' does not have automated backups enabled", [input.name]),
        "severity": "MEDIUM",
        "remediation": "Enable automated backups with a retention period of at least 7 days",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.3.2"},
            {"framework": "SOC2", "control": "CC5.2"}
        ]
    }
}

deny[finding] {
    input.resource_type == "aws::rds::db-instance"
    
    # Check if backup retention period is too short
    backup_retention_period := input.raw.BackupRetentionPeriod
    backup_retention_period > 0
    backup_retention_period < 7
    
    finding := {
        "rule_id": "aws-rds-backup-retention-short",
        "title": "RDS instance backup retention period is too short",
        "description": sprintf("RDS instance '%s' has backup retention period of %d days, which is less than recommended 7 days", [input.name, backup_retention_period]),
        "severity": "LOW",
        "remediation": "Increase backup retention period to at least 7 days",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.3.2"},
            {"framework": "SOC2", "control": "CC5.2"}
        ]
    }
}