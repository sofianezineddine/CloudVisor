# METADATA
# title: GCP Storage Bucket is publicly accessible
# description: GCP Cloud Storage bucket grants access to allUsers or allAuthenticatedUsers.
# severity: CRITICAL
# category: cspm
# provider: gcp
# resource_type: gcp::storage::bucket
# remediation: Remove allUsers and allAuthenticatedUsers from bucket IAM bindings. Enable uniform bucket-level access.
# version: 1.0.0

package cloudvisor.cspm.gcp_bucket_public_access

deny[msg] if {
    input.resource.resource_type == "gcp::storage::bucket"
    input.resource.is_public == true
    msg := sprintf("GCP Storage bucket '%v' is publicly accessible", [input.resource.name])
}
