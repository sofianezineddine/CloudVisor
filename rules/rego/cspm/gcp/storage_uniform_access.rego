# METADATA
# title: GCP Cloud Storage bucket does not use uniform bucket-level access
# description: GCP Cloud Storage bucket uses legacy ACLs instead of uniform bucket-level access, making permissions harder to manage.
# severity: MEDIUM
# category: cspm
# provider: gcp
# resource_type: gcp::storage::bucket
# remediation: Enable uniform bucket-level access on the Cloud Storage bucket to use IAM exclusively for access control.
# version: 1.0.0

package cloudvisor.cspm.gcp_storage_uniform_access

deny[msg] if {
    input.resource.resource_type == "gcp::storage::bucket"
    not input.resource.raw.iamConfiguration.uniformBucketLevelAccess.enabled
    msg := sprintf("GCP Cloud Storage bucket '%v' does not use uniform bucket-level access", [input.resource.name])
}
