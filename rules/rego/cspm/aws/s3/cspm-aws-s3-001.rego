# METADATA
# title: S3 Bucket Public Access Block Not Enabled
# description: The S3 bucket does not have all public access block settings enabled, potentially exposing data publicly
# severity: HIGH
# category: s3
# provider: aws
# resource_type: aws::s3::bucket
# remediation: Enable all four public access block settings on the bucket via the S3 console or AWS CLI
# compliance: CIS-AWS:2.1.5, SOC2:CC6.1, PCI-DSS:1.3.2
package cspm.aws.s3

deny[finding] if {
    input.resource_type == "aws::s3::bucket"
    not input.raw.PublicAccessBlockConfiguration.BlockPublicAcls
    finding := {
        "rule_id": "cspm-aws-s3-001",
        "title": "S3 Bucket Public Access Block Not Enabled",
        "severity": "HIGH",
        "description": "The S3 bucket does not have BlockPublicAcls enabled, potentially exposing data publicly",
        "remediation": "Enable BlockPublicAcls on the bucket via the S3 console or AWS CLI",
    }
}

deny[finding] if {
    input.resource_type == "aws::s3::bucket"
    not input.raw.PublicAccessBlockConfiguration.BlockPublicPolicy
    finding := {
        "rule_id": "cspm-aws-s3-001",
        "title": "S3 Bucket Public Access Block Not Enabled",
        "severity": "HIGH",
        "description": "The S3 bucket does not have BlockPublicPolicy enabled, potentially exposing data publicly",
        "remediation": "Enable BlockPublicPolicy on the bucket via the S3 console or AWS CLI",
    }
}

deny[finding] if {
    input.resource_type == "aws::s3::bucket"
    not input.raw.PublicAccessBlockConfiguration.IgnorePublicAcls
    finding := {
        "rule_id": "cspm-aws-s3-001",
        "title": "S3 Bucket Public Access Block Not Enabled",
        "severity": "HIGH",
        "description": "The S3 bucket does not have IgnorePublicAcls enabled, potentially exposing data publicly",
        "remediation": "Enable IgnorePublicAcls on the bucket via the S3 console or AWS CLI",
    }
}

deny[finding] if {
    input.resource_type == "aws::s3::bucket"
    not input.raw.PublicAccessBlockConfiguration.RestrictPublicBuckets
    finding := {
        "rule_id": "cspm-aws-s3-001",
        "title": "S3 Bucket Public Access Block Not Enabled",
        "severity": "HIGH",
        "description": "The S3 bucket does not have RestrictPublicBuckets enabled, potentially exposing data publicly",
        "remediation": "Enable RestrictPublicBuckets on the bucket via the S3 console or AWS CLI",
    }
}
