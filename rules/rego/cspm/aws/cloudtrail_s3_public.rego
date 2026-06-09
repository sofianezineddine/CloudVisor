# METADATA
# title: CloudTrail S3 bucket is publicly accessible
# description: The S3 bucket storing CloudTrail logs is publicly accessible, exposing audit logs.
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::cloudtrail::trail
# remediation: Remove public access from the S3 bucket used by CloudTrail. Enable S3 Block Public Access.
# version: 1.0.0

package cloudvisor.cspm.aws_cloudtrail_s3_public

deny[msg] if {
    input.resource.resource_type == "aws::cloudtrail::trail"
    input.resource.raw.S3BucketIsPublic == true
    msg := sprintf("CloudTrail trail '%v' logs to a publicly accessible S3 bucket", [input.resource.name])
}
