# METADATA
# title: Azure VM does not use managed identity
# description: Azure Virtual Machine does not have a managed identity assigned, requiring credential management.
# severity: LOW
# category: cspm
# provider: azure
# resource_type: azure::compute::virtualmachine
# remediation: Assign a system-assigned or user-assigned managed identity to the VM.
# version: 1.0.0

package cloudvisor.cspm.azure_vm_no_managed_identity

deny[msg] if {
    input.resource.resource_type == "azure::compute::virtualmachine"
    not input.resource.raw.identity
    msg := sprintf("Azure VM '%v' does not have a managed identity assigned", [input.resource.name])
}
