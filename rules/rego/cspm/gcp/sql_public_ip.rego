# METADATA
# title: GCP Cloud SQL instance has public IP
# description: GCP Cloud SQL instance is configured with a public IP address, exposing the database to the internet.
# severity: HIGH
# category: cspm
# provider: gcp
# resource_type: gcp::sql::instance
# remediation: Disable the public IP on the Cloud SQL instance and use Cloud SQL Auth Proxy or private IP.
# version: 1.0.0

package cloudvisor.cspm.gcp_sql_public_ip

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "gcp::sql::instance"
    input.resource.is_public == true
    msg := sprintf("GCP Cloud SQL instance '%v' has a public IP address", [input.resource.name])
}
