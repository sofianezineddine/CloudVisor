# METADATA
# title: "CloudTrail Not Enabled"
# description: "CloudTrail is not enabled for API logging and monitoring"
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::cloudtrail::trail
# compliance:
#   - framework: CIS-AWS
#     control: "3.1"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: NIST-800-53
#     control: "AU-2"
# remediation: "Enable CloudTrail: AWS Console > CloudTrail > Trails > Create trail > Enable logging"

package cloudvisor.cspm.aws.cloudtrail_enabled

import future.keywords

deny[finding] {
    input.resource_type == "aws::cloudtrail::trail"
    
    # Check if CloudTrail is enabled
    is_logging := input.raw.IsLogging
    is_logging == false
    
    finding := {
        "rule_id": "aws-cloudtrail-not-enabled",
        "title": "CloudTrail is not enabled",
        "description": sprintf("CloudTrail '%s' is not enabled for API logging", [input.name]),
        "severity": "HIGH",
        "remediation": "Enable CloudTrail logging to monitor API calls and maintain audit trail",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "3.1"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "NIST-800-53", "control": "AU-2"}
        ]
    }
}

deny[finding] {
    input.resource_type == "aws::cloudtrail::trail"
    
    # Check if CloudTrail log file validation is disabled
    log_file_validation := input.raw.LogFileValidationEnabled
    log_file_validation == false
    
    finding := {
        "rule_id": "aws-cloudtrail-log-validation-disabled",
        "title": "CloudTrail log file validation is disabled",
        "description": sprintf("CloudTrail '%s' does not have log file validation enabled", [input.name]),
        "severity": "MEDIUM",
        "remediation": "Enable log file validation to ensure CloudTrail logs have not been tampered with",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "3.2"},
            {"framework": "SOC2", "control": "CC6.1"}
        ]
    }
}