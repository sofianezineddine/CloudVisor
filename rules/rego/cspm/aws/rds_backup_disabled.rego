# METADATA
# title: "RDS automated backups disabled"
# description: "The RDS database instance has automated backups disabled (backup retention period set to 0). Without backups, data cannot be recovered after accidental deletion, corruption, or ransomware attacks."
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::rds::dbinstance
# compliance:
#   - framework: CIS-AWS
#     control: "2.3.2"
#   - framework: SOC2
#     control: "A1.2"
#   - framework: PCI-DSS
#     control: "12.3.4"
# remediation: "Enable automated backups by setting the backup retention period to at least 7 days. Consider setting it to 35 days (the maximum) for production databases."
# version: "1.0.0"
# tags: [rds, backup, database, availability]

package cspm.aws.rds_backup_disabled

deny[finding] if {
    input.resource_type == "aws::rds::dbinstance"
    input.raw.BackupRetentionPeriod == 0
    finding := {
        "rule_id": "aws-rds-backup-disabled",
        "title": "RDS automated backups are disabled",
        "severity": "MEDIUM",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": sprintf("RDS instance '%v' has automated backups disabled (retention period = 0). Data cannot be recovered after loss.", [input.name]),
        "remediation": "Set the backup retention period to at least 7 days. For production databases, consider 35 days.",
    }
}
