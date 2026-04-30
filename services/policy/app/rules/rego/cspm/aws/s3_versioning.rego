package cloudvisor.cspm.aws.s3_versioning

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::s3::bucket"
    versioning := input.resource.raw.VersioningConfiguration
    versioning.Status != "Enabled"
    msg := sprintf("S3 bucket '%v' does not have versioning enabled", [input.resource.name])
}
