# METADATA
# title: GCP service account key not rotated in 90+ days
# description: GCP service account has a user-managed key that has not been rotated in over 90 days.
# severity: HIGH
# category: cspm
# provider: gcp
# resource_type: gcp::iam::serviceaccount
# remediation: Rotate service account keys regularly. Delete old keys and create new ones.
# compliance:
#   - framework: CIS-GCP
#     control: 1.7
#   - framework: SOC2
#     control: CC6.1
# version: 1.0.0

package cloudvisor.cspm.gcp_iam_service_account_key_rotation

deny[msg] if {
    input.resource.resource_type == "gcp::iam::serviceaccount"
    input.resource.raw.key_age_days > 90
    msg := sprintf("GCP service account '%v' has a key older than 90 days", [input.resource.name])
}
