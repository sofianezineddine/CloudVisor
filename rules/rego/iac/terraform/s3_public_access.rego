# METADATA
# title: Terraform S3 bucket allows public access
# description: Terraform aws_s3_bucket resource does not have public access block configured.
# severity: CRITICAL
# category: iac
# provider: aws
# resource_type: terraform::aws_s3_bucket
# remediation: Add aws_s3_bucket_public_access_block resource with all block settings set to true.
# version: 1.0.0

package cloudvisor.iac.terraform_s3_public_access

deny[msg] if {
    input.resource.resource_type == "terraform::aws_s3_bucket"
    not input.resource.raw.block_public_acls
    msg := sprintf("Terraform S3 bucket '%v' does not block public ACLs", [input.resource.name])
}

deny[msg] if {
    input.resource.resource_type == "terraform::aws_s3_bucket"
    not input.resource.raw.block_public_policy
    msg := sprintf("Terraform S3 bucket '%v' does not block public bucket policies", [input.resource.name])
}
