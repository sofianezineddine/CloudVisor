# METADATA
# title: VPC Flow Logs Not Enabled
# description: A VPC does not have flow logs enabled, making it impossible to monitor network traffic for security analysis
# severity: MEDIUM
# category: vpc
# provider: aws
# resource_type: aws::vpc::vpc
# remediation: Enable VPC flow logs and configure them to publish to CloudWatch Logs or S3 for analysis
# compliance: CIS-AWS:3.9, SOC2:CC7.2
package cspm.aws.vpc

deny[finding] if {
    input.resource_type == "aws::vpc::vpc"
    not input.raw.FlowLogsEnabled
    finding := {
        "rule_id": "cspm-aws-vpc-001",
        "title": "VPC Flow Logs Not Enabled",
        "severity": "MEDIUM",
        "description": "A VPC does not have flow logs enabled, making it impossible to monitor network traffic for security analysis",
        "remediation": "Enable VPC flow logs and configure them to publish to CloudWatch Logs or S3 for analysis",
    }
}

deny[finding] if {
    input.resource_type == "aws::vpc::vpc"
    input.raw.FlowLogsEnabled == false
    finding := {
        "rule_id": "cspm-aws-vpc-001",
        "title": "VPC Flow Logs Not Enabled",
        "severity": "MEDIUM",
        "description": "A VPC does not have flow logs enabled, making it impossible to monitor network traffic for security analysis",
        "remediation": "Enable VPC flow logs and configure them to publish to CloudWatch Logs or S3 for analysis",
    }
}
