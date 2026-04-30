# METADATA
# title: EBS Volume Not Encrypted
# description: An EBS volume is not encrypted, leaving data at rest unprotected
# severity: HIGH
# category: ec2
# provider: aws
# resource_type: aws::ec2::volume
# remediation: Create an encrypted snapshot of the volume and restore it as an encrypted volume, or enable EBS encryption by default in the region
# compliance: CIS-AWS:2.2.1, SOC2:CC6.7, PCI-DSS:3.4
package cspm.aws.ec2

import future.keywords

deny[finding] {
    input.resource_type == "aws::ec2::volume"
    not input.raw.Encrypted
    finding := {
        "rule_id": "cspm-aws-ec2-005",
        "title": "EBS Volume Not Encrypted",
        "severity": "HIGH",
        "description": "An EBS volume is not encrypted, leaving data at rest unprotected",
        "remediation": "Create an encrypted snapshot of the volume and restore it as an encrypted volume, or enable EBS encryption by default in the region",
    }
}
