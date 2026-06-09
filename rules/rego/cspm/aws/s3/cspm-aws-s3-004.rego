# METADATA
# title: S3 Bucket Versioning Not Enabled
# description: The S3 bucket does not have versioning enabled, preventing recovery from accidental deletion or overwrites
# severity: MEDIUM
# category: s3
# provider: aws
# resource_type: aws::s3::bucket
# remediation: Enable versioning on the S3 bucket via the S3 console or AWS CLI
# compliance: CIS-AWS:2.1.3, SOC2:A1.2
package cspm.aws.s3

deny[finding] if {
    input.resource_type == "aws::s3::bucket"
    not input.raw.VersioningConfiguration
    finding := {
        "rule_id": "cspm-aws-s3-004",
        "title": "S3 Bucket Versioning Not Enabled",
        "severity": "MEDIUM",
        "description": "The S3 bucket does not have versioning configured, preventing recovery from accidental deletion or overwrites",
        "remediation": "Enable versioning on the S3 bucket via the S3 console or AWS CLI",
    }
}

deny[finding] if {
    input.resource_type == "aws::s3::bucket"
    input.raw.VersioningConfiguration.Status != "Enabled"
    finding := {
        "rule_id": "cspm-aws-s3-004",
        "title": "S3 Bucket Versioning Not Enabled",
        "severity": "MEDIUM",
        "description": "The S3 bucket versioning is not in Enabled state, preventing recovery from accidental deletion or overwrites",
        "remediation": "Enable versioning on the S3 bucket via the S3 console or AWS CLI",
    }
}
