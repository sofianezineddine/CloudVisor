# METADATA
# title: Terraform S3 bucket missing server-side encryption
# description: Terraform aws_s3_bucket resource does not have server-side encryption configured.
# severity: HIGH
# category: iac
# resource_type: terraform::aws_s3_bucket
# remediation: Add server_side_encryption_configuration block with AES256 or aws:kms encryption.
# version: 1.0.0

package cloudvisor.iac.terraform_s3_encryption

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "terraform::aws_s3_bucket"
    not input.resource.raw.server_side_encryption_configuration
    msg := sprintf("Terraform S3 bucket '%v' does not have server-side encryption configured", [input.resource.name])
}
