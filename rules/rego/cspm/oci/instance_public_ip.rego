# METADATA
# title: OCI Compute instance has public IP address
# description: OCI Compute instance is assigned a public IP address, making it directly accessible from the internet.
# severity: MEDIUM
# category: cspm
# provider: oci
# resource_type: oci::compute::instance
# remediation: Remove the public IP from the instance and use a load balancer or bastion host for access.
# version: 1.0.0

package cloudvisor.cspm.oci_instance_public_ip

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "oci::compute::instance"
    input.resource.is_public == true
    msg := sprintf("OCI instance '%v' has a public IP address", [input.resource.name])
}
