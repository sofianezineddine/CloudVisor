# METADATA
# title: GCP Compute instance has serial port access enabled
# description: GCP Compute instance has serial port access enabled, which can be used to gain unauthorized access.
# severity: MEDIUM
# category: cspm
# provider: gcp
# resource_type: gcp::compute::instance
# remediation: Disable serial port access on the Compute instance by setting the 'serial-port-enable' metadata key to false.
# version: 1.0.0

package cloudvisor.cspm.gcp_compute_serial_port

deny[msg] if {
    input.resource.resource_type == "gcp::compute::instance"
    metadata := input.resource.raw.metadata.items[_]
    metadata.key == "serial-port-enable"
    metadata.value == "true"
    msg := sprintf("GCP Compute instance '%v' has serial port access enabled", [input.resource.name])
}
