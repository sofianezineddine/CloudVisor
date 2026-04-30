# METADATA
# title: GCP BigQuery dataset is publicly accessible
# description: BigQuery dataset has allUsers or allAuthenticatedUsers in its IAM policy.
# severity: CRITICAL
# category: cspm
# provider: gcp
# resource_type: gcp::bigquery::dataset
# remediation: Remove allUsers and allAuthenticatedUsers from the dataset IAM policy.
# compliance:
#   - framework: CIS-GCP
#     control: 7.1
#   - framework: SOC2
#     control: CC6.6
#   - framework: GDPR
#     control: Art.32
# version: 1.0.0

package cloudvisor.cspm.gcp_bigquery_public_dataset

import future.keywords.if
import future.keywords.some

deny[msg] if {
    input.resource.resource_type == "gcp::bigquery::dataset"
    some binding in input.resource.raw.iam_bindings
    binding.member == "allUsers"
    msg := sprintf("BigQuery dataset '%v' is publicly accessible (allUsers)", [input.resource.name])
}

deny[msg] if {
    input.resource.resource_type == "gcp::bigquery::dataset"
    some binding in input.resource.raw.iam_bindings
    binding.member == "allAuthenticatedUsers"
    msg := sprintf("BigQuery dataset '%v' is accessible to all authenticated users", [input.resource.name])
}
