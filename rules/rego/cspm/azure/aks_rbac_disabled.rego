# METADATA
# title: Azure AKS cluster does not have RBAC enabled
# description: Azure Kubernetes Service cluster does not have Role-Based Access Control enabled.
# severity: HIGH
# category: cspm
# provider: azure
# resource_type: azure::containerservice::managedcluster
# remediation: Enable RBAC when creating the AKS cluster. Existing clusters require recreation.
# compliance:
#   - framework: CIS-Azure
#     control: 8.5
#   - framework: NIST-800-53
#     control: AC-6
# version: 1.0.0

package cloudvisor.cspm.azure_aks_rbac_disabled

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "azure::containerservice::managedcluster"
    not input.resource.raw.enable_rbac
    msg := sprintf("AKS cluster '%v' does not have RBAC enabled", [input.resource.name])
}
