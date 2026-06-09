# METADATA
# title: S3 Bucket has public access enabled
# description: S3 bucket allows public read or write access, exposing data to the internet.
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::s3::bucket
# remediation: Enable S3 Block Public Access settings on the bucket and bucket policy.
# version: 1.0.0

package cloudvisor.cspm.aws_s3_public_access

deny[msg] if {
    input.resource.resource_type == "aws::s3::bucket"
    input.resource.is_public == true
    msg := sprintf("S3 bucket '%v' has public access enabled", [input.resource.name])
}
