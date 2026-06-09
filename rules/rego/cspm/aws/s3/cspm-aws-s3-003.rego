# METADATA
# title: S3 Bucket Server-Side Encryption Not Enabled
# description: The S3 bucket does not have server-side encryption configured, leaving data at rest unencrypted
# severity: HIGH
# category: s3
# provider: aws
# resource_type: aws::s3::bucket
# remediation: Enable default server-side encryption on the bucket using AES-256 or AWS KMS
# compliance: CIS-AWS:2.1.1, SOC2:CC6.7, PCI-DSS:3.4
package cspm.aws.s3

deny[finding] if {
    input.resource_type == "aws::s3::bucket"
    not input.raw.ServerSideEncryptionConfiguration
    finding := {
        "rule_id": "cspm-aws-s3-003",
        "title": "S3 Bucket Server-Side Encryption Not Enabled",
        "severity": "HIGH",
        "description": "The S3 bucket does not have server-side encryption configured, leaving data at rest unencrypted",
        "remediation": "Enable default server-side encryption on the bucket using AES-256 or AWS KMS",
    }
}
