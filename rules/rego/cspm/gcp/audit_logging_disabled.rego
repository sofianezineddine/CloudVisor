# METADATA
# title: GCP Cloud Audit Logging not configured
# description: GCP project does not have Cloud Audit Logging enabled for all services, missing critical audit trail.
# severity: HIGH
# category: cspm
# provider: gcp
# resource_type: gcp::iam::policy
# remediation: Enable Cloud Audit Logging for all services in the GCP project IAM policy. Configure DATA_READ and DATA_WRITE audit log types.
# version: 1.0.0

package cloudvisor.cspm.gcp_audit_logging_disabled

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "gcp::iam::policy"
    not input.resource.raw.auditConfigs
    msg := sprintf("GCP project '%v' does not have Cloud Audit Logging configured", [input.resource.name])
}
