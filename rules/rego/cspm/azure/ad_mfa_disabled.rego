# METADATA
# title: Azure AD user does not have MFA enabled
# description: Azure Active Directory user account does not have multi-factor authentication enabled.
# severity: HIGH
# category: cspm
# provider: azure
# resource_type: azure::aad::user
# remediation: Enable MFA for the user in Azure AD > Users > Multi-Factor Authentication.
# compliance:
#   - framework: CIS-Azure
#     control: 1.1
#   - framework: SOC2
#     control: CC6.1
#   - framework: PCI-DSS
#     control: 8.4.2
# version: 1.0.0

package cloudvisor.cspm.azure_ad_mfa_disabled

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "azure::aad::user"
    not input.resource.raw.mfa_enabled
    msg := sprintf("Azure AD user '%v' does not have MFA enabled", [input.resource.name])
}
