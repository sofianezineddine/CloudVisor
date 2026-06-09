# METADATA
# title: CloudTrail log file validation disabled
# description: CloudTrail log file validation is not enabled, making it impossible to detect if log files have been tampered with.
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::cloudtrail::trail
# remediation: Enable log file validation on the CloudTrail trail using the AWS Console or CLI: aws cloudtrail update-trail --name <trail-name> --enable-log-file-validation
# version: 1.0.0

package cloudvisor.cspm.aws_cloudtrail_log_validation

deny[msg] if {
    input.resource.resource_type == "aws::cloudtrail::trail"
    not input.resource.raw.LogFileValidationEnabled
    msg := sprintf("CloudTrail trail '%v' does not have log file validation enabled", [input.resource.name])
}
