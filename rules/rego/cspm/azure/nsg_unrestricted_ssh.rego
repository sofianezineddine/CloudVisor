# METADATA
# title: Azure NSG allows unrestricted SSH access
# description: Azure Network Security Group has an inbound rule allowing SSH (port 22) from any source.
# severity: HIGH
# category: cspm
# provider: azure
# resource_type: azure::network::networksecuritygroup
# remediation: Restrict SSH access to specific IP ranges. Use Azure Bastion for secure remote access.
# version: 1.0.0

package cloudvisor.cspm.azure_nsg_unrestricted_ssh

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "azure::network::networksecuritygroup"
    input.resource.is_public == true
    msg := sprintf("Azure NSG '%v' allows unrestricted inbound access from the internet", [input.resource.name])
}
