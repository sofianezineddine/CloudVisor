# METADATA
# title: CloudTrail Not Enabled in Region
# description: AWS CloudTrail is not actively logging in this region, leaving API activity unaudited
# severity: HIGH
# category: cloudtrail
# provider: aws
# resource_type: aws::cloudtrail::trail
# remediation: Enable CloudTrail logging for the trail via the AWS console or CLI
# compliance: CIS-AWS:3.1, SOC2:CC7.2, PCI-DSS:10.1
package cspm.aws.cloudtrail

deny[finding] if {
    input.resource_type == "aws::cloudtrail::trail"
    not input.raw.IsLogging
    finding := {
        "rule_id": "cspm-aws-ct-001",
        "title": "CloudTrail Not Enabled in Region",
        "severity": "HIGH",
        "description": "AWS CloudTrail is not actively logging in this region, leaving API activity unaudited",
        "remediation": "Enable CloudTrail logging for the trail via the AWS console or CLI",
    }
}
