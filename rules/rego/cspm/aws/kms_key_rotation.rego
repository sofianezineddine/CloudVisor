# METADATA
# title: "KMS key automatic rotation not enabled"
# description: "AWS KMS customer-managed key does not have automatic rotation enabled. Keys should be rotated annually to limit the blast radius of a compromised key."
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::kms::key
# compliance:
#   - framework: CIS-AWS
#     control: "3.8"
#   - framework: PCI-DSS
#     control: "3.6"
#   - framework: NIST-800-53
#     control: "SC-12"
# remediation: "Enable automatic key rotation for all customer-managed KMS keys. AWS rotates the key material annually."
# version: "1.0.0"
# tags: [kms, encryption, key-rotation, cryptography]

package cspm.aws.kms_key_rotation

deny[finding] if {
    input.resource_type == "aws::kms::key"
    input.raw.KeyManager == "CUSTOMER"
    not input.raw.KeyRotationEnabled
    finding := {
        "rule_id": "aws-kms-key-rotation",
        "title": "KMS customer-managed key rotation not enabled",
        "severity": "MEDIUM",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": "KMS key does not have automatic rotation enabled. Stale keys increase risk.",
        "remediation": "Enable automatic key rotation in the KMS console or via AWS CLI.",
    }
}
