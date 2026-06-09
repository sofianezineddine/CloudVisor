# METADATA
# title: CloudTrail Log File Validation Not Enabled
# description: CloudTrail log file validation is not enabled, making it impossible to detect if log files have been tampered with
# severity: MEDIUM
# category: cloudtrail
# provider: aws
# resource_type: aws::cloudtrail::trail
# remediation: Enable log file validation on the CloudTrail trail via the AWS console or CLI
# compliance: CIS-AWS:3.2, SOC2:CC7.2
package cspm.aws.cloudtrail

deny[finding] if {
    input.resource_type == "aws::cloudtrail::trail"
    not input.raw.LogFileValidationEnabled
    finding := {
        "rule_id": "cspm-aws-ct-002",
        "title": "CloudTrail Log File Validation Not Enabled",
        "severity": "MEDIUM",
        "description": "CloudTrail log file validation is not enabled, making it impossible to detect if log files have been tampered with",
        "remediation": "Enable log file validation on the CloudTrail trail via the AWS console or CLI",
    }
}
