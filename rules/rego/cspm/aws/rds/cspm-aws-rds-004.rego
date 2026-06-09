# METADATA
# title: RDS Instance Deletion Protection Not Enabled
# description: An RDS database instance does not have deletion protection enabled, allowing accidental or unauthorized deletion
# severity: MEDIUM
# category: rds
# provider: aws
# resource_type: aws::rds::instance
# remediation: Enable deletion protection on the RDS instance via the AWS console or CLI
# compliance: SOC2:A1.2, CIS-AWS:2.3.4
package cspm.aws.rds

deny[finding] if {
    input.resource_type == "aws::rds::instance"
    not input.raw.DeletionProtection
    finding := {
        "rule_id": "cspm-aws-rds-004",
        "title": "RDS Instance Deletion Protection Not Enabled",
        "severity": "MEDIUM",
        "description": "An RDS database instance does not have deletion protection enabled, allowing accidental or unauthorized deletion",
        "remediation": "Enable deletion protection on the RDS instance via the AWS console or CLI",
    }
}
