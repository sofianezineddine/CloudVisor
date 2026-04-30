# METADATA
# title: GCP Compute instance has serial port access enabled
# description: GCP Compute instance has interactive serial port access enabled, which can be used for unauthorized access.
# severity: MEDIUM
# category: cspm
# provider: gcp
# resource_type: gcp::compute::instance
# remediation: Disable serial port access in the instance metadata by setting serial-port-enable to false.
# compliance:
#   - framework: CIS-GCP
#     control: 4.5
#   - framework: NIST-800-53
#     control: AC-17
# version: 1.0.0

package cloudvisor.cspm.gcp_compute_serial_port_enabled

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "gcp::compute::instance"
    input.resource.raw.metadata["serial-port-enable"] == "true"
    msg := sprintf("GCP Compute instance '%v' has serial port access enabled", [input.resource.name])
}
