# METADATA
# title: GCP Firewall rule allows unrestricted SSH
# description: GCP firewall rule allows SSH (port 22) from 0.0.0.0/0 or ::/0.
# severity: HIGH
# category: cspm
# provider: gcp
# resource_type: gcp::compute::firewall
# remediation: Restrict SSH access to specific IP ranges. Use Identity-Aware Proxy (IAP) for SSH access.
# version: 1.0.0

package cloudvisor.cspm.gcp_firewall_unrestricted_ssh

deny[msg] if {
    input.resource.resource_type == "gcp::compute::firewall"
    input.resource.raw.direction == "INGRESS"
    "0.0.0.0/0" in input.resource.raw.source_ranges
    msg := sprintf("GCP Firewall rule '%v' allows unrestricted SSH from 0.0.0.0/0", [input.resource.name])
}
