# METADATA
# title: "S3 bucket access logging not enabled"
# description: "S3 bucket access logging is not enabled. Without access logs, it is impossible to audit who accessed or modified objects in the bucket, hindering incident response and compliance audits."
# severity: LOW
# category: cspm
# provider: aws
# resource_type: aws::s3::bucket
# compliance:
#   - framework: CIS-AWS
#     control: "2.1.2"
#   - framework: SOC2
#     control: "CC7.2"
#   - framework: PCI-DSS
#     control: "10.2"
# remediation: "Enable S3 server access logging on the bucket. Specify a target bucket and prefix for the log files. Ensure the target bucket has appropriate retention policies."
# version: "1.0.0"
# tags: [s3, logging, audit, access-logs]

package cspm.aws.s3_logging

deny[finding] if {
    input.resource_type == "aws::s3::bucket"
    not input.raw.LoggingEnabled
    finding := {
        "rule_id": "aws-s3-logging-disabled",
        "title": "S3 bucket access logging is not enabled",
        "severity": "LOW",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": sprintf("S3 bucket '%v' does not have access logging enabled. Object access and modification events are not being recorded.", [input.name]),
        "remediation": "Enable server access logging on the S3 bucket and configure a target bucket for log storage.",
    }
}
