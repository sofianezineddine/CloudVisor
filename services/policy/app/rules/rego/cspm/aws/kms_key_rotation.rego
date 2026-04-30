# METADATA
# title: "KMS Key Rotation Not Enabled"
# description: "KMS customer-managed key does not have automatic rotation enabled"
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::kms::key
# compliance:
#   - framework: CIS-AWS
#     control: "3.8"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: NIST-800-53
#     control: "SC-12"
# remediation: "Enable KMS key rotation: AWS Console > KMS > Customer managed keys > Key > Key rotation > Enable"

package cloudvisor.cspm.aws.kms_key_rotation

import future.keywords

deny[finding] {
    input.resource_type == "aws::kms::key"
    
    # Only check customer-managed keys (not AWS managed)
    key_manager := input.raw.KeyManager
    key_manager == "CUSTOMER"
    
    # Check if key rotation is disabled
    key_rotation_enabled := input.raw.KeyRotationEnabled
    key_rotation_enabled == false
    
    finding := {
        "rule_id": "aws-kms-key-rotation-disabled",
        "title": "KMS key rotation is not enabled",
        "description": sprintf("KMS customer-managed key '%s' does not have automatic rotation enabled", [input.name]),
        "severity": "MEDIUM",
        "remediation": "Enable automatic key rotation for this KMS customer-managed key",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "3.8"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "NIST-800-53", "control": "SC-12"}
        ]
    }
}