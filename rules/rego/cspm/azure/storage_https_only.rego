# METADATA
# title: Azure Storage Account does not enforce HTTPS
# description: Azure Storage Account allows HTTP traffic, which is unencrypted and vulnerable to interception.
# severity: HIGH
# category: cspm
# provider: azure
# resource_type: azure::storage::storageaccount
# remediation: Enable 'Secure transfer required' on the Storage Account to enforce HTTPS-only access.
# version: 1.0.0

package cloudvisor.cspm.azure_storage_https_only

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "azure::storage::storageaccount"
    not input.resource.raw.properties.supportsHttpsTrafficOnly
    msg := sprintf("Azure Storage Account '%v' does not enforce HTTPS-only traffic", [input.resource.name])
}
