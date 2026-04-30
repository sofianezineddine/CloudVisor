# METADATA
# title: S3 Bucket Access Logging Not Enabled
# description: The S3 bucket does not have access logging enabled, making it difficult to audit access and detect unauthorized activity
# severity: LOW
# category: s3
# provider: aws
# resource_type: aws::s3::bucket
# remediation: Enable server access logging on the S3 bucket and configure a target bucket for log storage
# compliance: CIS-AWS:2.1.2, SOC2:CC7.2
package cspm.aws.s3

import future.keywords

deny[finding] {
    input.resource_type == "aws::s3::bucket"
    not input.raw.LoggingEnabled
    finding := {
        "rule_id": "cspm-aws-s3-005",
        "title": "S3 Bucket Access Logging Not Enabled",
        "severity": "LOW",
        "description": "The S3 bucket does not have access logging enabled, making it difficult to audit access and detect unauthorized activity",
        "remediation": "Enable server access logging on the S3 bucket and configure a target bucket for log storage",
    }
}
