# METADATA
# title: "CloudTrail trail is not multi-region"
# description: "The CloudTrail trail is not configured to capture events from all AWS regions. Single-region trails miss API activity in other regions, creating blind spots for security monitoring and incident response."
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::cloudtrail::trail
# compliance:
#   - framework: CIS-AWS
#     control: "3.1"
#   - framework: SOC2
#     control: "CC7.2"
#   - framework: PCI-DSS
#     control: "10.1"
#   - framework: NIST-800-53
#     control: "AU-2"
# remediation: "Update the CloudTrail trail to enable multi-region logging. Ensure the trail also captures global service events (IAM, STS, CloudFront) by enabling IncludeGlobalServiceEvents."
# version: "1.0.0"
# tags: [cloudtrail, logging, multi-region, audit]

package cspm.aws.cloudtrail_multiregion

import future.keywords.if

deny[finding] if {
    input.resource_type == "aws::cloudtrail::trail"
    not input.raw.IsMultiRegionTrail
    finding := {
        "rule_id": "aws-cloudtrail-not-multiregion",
        "title": "CloudTrail trail is not multi-region",
        "severity": "HIGH",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": sprintf("CloudTrail trail '%v' only captures events in a single region. API activity in other regions is not logged.", [input.name]),
        "remediation": "Enable multi-region logging on the CloudTrail trail and enable IncludeGlobalServiceEvents.",
    }
}

deny[finding] if {
    input.resource_type == "aws::cloudtrail::trail"
    input.raw.IsMultiRegionTrail
    not input.raw.IncludeGlobalServiceEvents
    finding := {
        "rule_id": "aws-cloudtrail-no-global-events",
        "title": "CloudTrail trail does not capture global service events",
        "severity": "HIGH",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": sprintf("CloudTrail trail '%v' does not capture global service events (IAM, STS, CloudFront). Critical API calls may be missed.", [input.name]),
        "remediation": "Enable IncludeGlobalServiceEvents on the CloudTrail trail.",
    }
}
