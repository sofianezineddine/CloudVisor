# METADATA
# title: CloudTrail logging not enabled
# description: AWS CloudTrail is not enabled, meaning API activity is not being logged.
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::cloudtrail::trail
# remediation: Enable CloudTrail in all regions with log file validation and S3 encryption.
# version: 1.0.0

package cloudvisor.cspm.aws_cloudtrail_disabled

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::cloudtrail::trail"
    not input.resource.raw.IsLogging
    msg := sprintf("CloudTrail trail '%v' is not logging", [input.resource.name])
}

deny[msg] if {
    input.resource.resource_type == "aws::cloudtrail::trail"
    not input.resource.raw.LogFileValidationEnabled
    msg := sprintf("CloudTrail trail '%v' does not have log file validation enabled", [input.resource.name])
}
