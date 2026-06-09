# METADATA
# title: "RDS instance not encrypted at rest"
# description: "The RDS database instance does not have encryption at rest enabled. Unencrypted databases are at risk if the underlying storage media is accessed directly or if backups are exposed."
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::rds::dbinstance
# compliance:
#   - framework: CIS-AWS
#     control: "2.3.1"
#   - framework: SOC2
#     control: "CC6.7"
#   - framework: PCI-DSS
#     control: "3.4"
#   - framework: HIPAA
#     control: "164.312(a)(2)(iv)"
# remediation: "Enable encryption at rest for the RDS instance. Note: encryption cannot be enabled on an existing unencrypted instance. Create a new encrypted instance and migrate data, or restore from a snapshot with encryption enabled."
# version: "1.0.0"
# tags: [rds, encryption, database, data-protection]

package cspm.aws.rds_encryption

deny[finding] if {
    input.resource_type == "aws::rds::dbinstance"
    not input.raw.StorageEncrypted
    finding := {
        "rule_id": "aws-rds-encryption-disabled",
        "title": "RDS instance is not encrypted at rest",
        "severity": "HIGH",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": sprintf("RDS instance '%v' does not have storage encryption enabled. Data at rest is unprotected.", [input.name]),
        "remediation": "Create a new encrypted RDS instance and migrate data. Encryption cannot be enabled on an existing unencrypted instance.",
    }
}
