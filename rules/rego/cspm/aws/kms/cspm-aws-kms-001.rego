# METADATA
# title: KMS Customer Managed Key Rotation Not Enabled
# description: A KMS customer managed key (CMK) does not have automatic key rotation enabled, increasing the risk of key compromise over time
# severity: MEDIUM
# category: kms
# provider: aws
# resource_type: aws::kms::key
# remediation: Enable automatic key rotation for the KMS customer managed key via the AWS console or CLI
# compliance: CIS-AWS:3.7, SOC2:CC6.7
package cspm.aws.kms

import future.keywords

deny[finding] {
    input.resource_type == "aws::kms::key"
    input.raw.KeyManager == "CUSTOMER"
    not input.raw.KeyRotationEnabled
    finding := {
        "rule_id": "cspm-aws-kms-001",
        "title": "KMS Customer Managed Key Rotation Not Enabled",
        "severity": "MEDIUM",
        "description": "A KMS customer managed key (CMK) does not have automatic key rotation enabled, increasing the risk of key compromise over time",
        "remediation": "Enable automatic key rotation for the KMS customer managed key via the AWS console or CLI",
    }
}
