package cloudvisor.cspm.aws.rds_encryption

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::rds::db-instance"
    not input.resource.raw.StorageEncrypted
    msg := sprintf("RDS instance '%v' storage is not encrypted", [input.resource.name])
}
