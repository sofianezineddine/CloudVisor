# METADATA
# title: CloudTrail Trail Not Configured as Multi-Region
# description: The CloudTrail trail is not configured as multi-region, leaving some regions without API activity logging
# severity: MEDIUM
# category: cloudtrail
# provider: aws
# resource_type: aws::cloudtrail::trail
# remediation: Update the CloudTrail trail to enable multi-region logging to capture API activity across all regions
# compliance: CIS-AWS:3.1, SOC2:CC7.2
package cspm.aws.cloudtrail

deny[finding] if {
    input.resource_type == "aws::cloudtrail::trail"
    not input.raw.IsMultiRegionTrail
    finding := {
        "rule_id": "cspm-aws-ct-003",
        "title": "CloudTrail Trail Not Configured as Multi-Region",
        "severity": "MEDIUM",
        "description": "The CloudTrail trail is not configured as multi-region, leaving some regions without API activity logging",
        "remediation": "Update the CloudTrail trail to enable multi-region logging to capture API activity across all regions",
    }
}
