# METADATA
# title: GCP KMS key rotation is not enabled
# description: GCP Cloud KMS key does not have automatic rotation enabled.
# severity: MEDIUM
# category: cspm
# provider: gcp
# resource_type: gcp::cloudkms::cryptokey
# remediation: Enable automatic key rotation on the KMS key with a rotation period of 90 days or less.
# compliance:
#   - framework: CIS-GCP
#     control: 1.10
#   - framework: SOC2
#     control: CC6.1
#   - framework: PCI-DSS
#     control: 3.7.1
# version: 1.0.0

package cloudvisor.cspm.gcp_kms_key_rotation

deny[msg] if {
    input.resource.resource_type == "gcp::cloudkms::cryptokey"
    not input.resource.raw.rotation_period
    msg := sprintf("GCP KMS key '%v' does not have automatic rotation enabled", [input.resource.name])
}
