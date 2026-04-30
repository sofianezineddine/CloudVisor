# METADATA
# title: Azure AD user does not have MFA enabled
# description: Azure Active Directory user account does not have multi-factor authentication enabled.
# severity: HIGH
# category: cspm
# provider: azure
# resource_type: azure::aad::user
# remediation: Enable MFA for the user via Azure AD Conditional Access policies or per-user MFA settings.
# version: 1.0.0

package cloudvisor.cspm.azure_mfa_not_enabled

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "azure::aad::user"
    not input.resource.raw.strongAuthenticationDetail.methods
    msg := sprintf("Azure AD user '%v' does not have MFA enabled", [input.resource.name])
}
