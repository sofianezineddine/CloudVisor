# METADATA
# title: GKE cluster has legacy authorization enabled
# description: GKE cluster has legacy ABAC authorization enabled, which is less secure than RBAC.
# severity: HIGH
# category: cspm
# provider: gcp
# resource_type: gcp::container::cluster
# remediation: Disable legacy authorization in GKE cluster settings and use RBAC instead.
# compliance:
#   - framework: CIS-GCP
#     control: 7.3
#   - framework: NIST-800-53
#     control: AC-6
# version: 1.0.0

package cloudvisor.cspm.gcp_gke_legacy_auth

deny[msg] if {
    input.resource.resource_type == "gcp::container::cluster"
    input.resource.raw.legacy_abac_enabled == true
    msg := sprintf("GKE cluster '%v' has legacy authorization enabled", [input.resource.name])
}
