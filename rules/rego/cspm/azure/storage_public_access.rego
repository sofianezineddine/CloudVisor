# METADATA
# title: Azure Storage Account allows public blob access
# description: Azure Storage Account has public blob access enabled, potentially exposing data.
# severity: HIGH
# category: cspm
# provider: azure
# resource_type: azure::storage::storageaccount
# remediation: Set allowBlobPublicAccess to false on the storage account.
# version: 1.0.0

package cloudvisor.cspm.azure_storage_public_access

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "azure::storage::storageaccount"
    input.resource.raw.allow_blob_public_access == true
    msg := sprintf("Azure Storage Account '%v' allows public blob access", [input.resource.name])
}
