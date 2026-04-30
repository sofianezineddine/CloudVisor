# METADATA
# title: Azure Key Vault soft delete is not enabled
# description: Azure Key Vault does not have soft delete enabled, risking permanent data loss.
# severity: HIGH
# category: cspm
# provider: azure
# resource_type: azure::keyvault::vault
# remediation: Enable soft delete on the Key Vault. This cannot be disabled once enabled.
# compliance:
#   - framework: SOC2
#     control: A1.2
#   - framework: HIPAA
#     control: 164.308(a)(7)
# version: 1.0.0

package cloudvisor.cspm.azure_keyvault_soft_delete

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "azure::keyvault::vault"
    not input.resource.raw.enable_soft_delete
    msg := sprintf("Azure Key Vault '%v' does not have soft delete enabled", [input.resource.name])
}
