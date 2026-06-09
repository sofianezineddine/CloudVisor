# METADATA
# title: KMS key rotation not enabled
# description: AWS KMS customer-managed key does not have automatic rotation enabled.
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::kms::key
# remediation: Enable automatic key rotation for all customer-managed KMS keys.
# version: 1.0.0

package cloudvisor.cspm.aws_kms_rotation

deny[msg] if {
    input.resource.resource_type == "aws::kms::key"
    not input.resource.raw.KeyRotationEnabled
    msg := sprintf("KMS key '%v' does not have automatic rotation enabled", [input.resource.name])
}
