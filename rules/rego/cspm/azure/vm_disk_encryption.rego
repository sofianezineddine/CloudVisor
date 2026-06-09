# METADATA
# title: Azure Virtual Machine OS disk is not encrypted
# description: Azure VM OS disk does not have encryption enabled, risking data exposure.
# severity: HIGH
# category: cspm
# provider: azure
# resource_type: azure::compute::virtualmachine
# remediation: Enable Azure Disk Encryption on the VM using Azure Disk Encryption extension.
# compliance:
#   - framework: CIS-Azure
#     control: 7.2
#   - framework: SOC2
#     control: CC6.1
#   - framework: HIPAA
#     control: 164.312(a)(2)(iv)
# version: 1.0.0

package cloudvisor.cspm.azure_vm_disk_encryption

deny[msg] if {
    input.resource.resource_type == "azure::compute::virtualmachine"
    not input.resource.raw.os_disk_encryption_enabled
    msg := sprintf("Azure VM '%v' OS disk is not encrypted", [input.resource.name])
}
