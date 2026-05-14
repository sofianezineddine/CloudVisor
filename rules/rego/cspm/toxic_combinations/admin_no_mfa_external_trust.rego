# METADATA
# title: Admin Account Without MFA Trusted by External Account
# description: >
#   Detects the toxic combination of an IAM identity with admin privileges that
#   does not have MFA enabled and is trusted by an external (cross-account) entity.
#   This creates a critical risk where a compromised external account could gain
#   unrestricted admin access without a second authentication factor.
# custom:
#   pattern_id: admin-no-mfa-external-trust
#   components:
#     - admin_privileges
#     - no_mfa
#     - external_trust
#   elevated_severity: CRITICAL
#   description: Admin account without MFA trusted by external account

package cspm.toxic_combinations.admin_no_mfa_external_trust

import rego.v1

# violation is true when an identity has all three toxic components:
# 1. Admin-level privileges
# 2. MFA is not enabled
# 3. Trusted by an external account
violation contains result if {
    resource := input.resource

    # Component 1: Identity has admin privileges
    _has_admin_privileges(resource)

    # Component 2: MFA is not enabled
    not _has_mfa_enabled(resource)

    # Component 3: Trusted by an external account
    _has_external_trust(resource)

    result := {
        "pattern_id": "admin-no-mfa-external-trust",
        "resource_id": resource.id,
        "resource_type": resource.resource_type,
        "elevated_severity": "CRITICAL",
        "components": [
            {"check": "admin_privileges", "status": "failed", "detail": "Identity has admin-level privileges"},
            {"check": "no_mfa", "status": "failed", "detail": "MFA is not enabled"},
            {"check": "external_trust", "status": "failed", "detail": "Identity is trusted by external account"},
        ],
        "description": "Admin account without MFA trusted by external account",
    }
}

# Check if the identity has admin privileges
_has_admin_privileges(resource) if {
    resource.config.is_admin == true
}

_has_admin_privileges(resource) if {
    some permission in resource.config.permissions
    permission == "*:*"
}

_has_admin_privileges(resource) if {
    some permission in resource.config.permissions
    permission == "AdministratorAccess"
}

_has_admin_privileges(resource) if {
    some policy in resource.config.attached_policies
    policy.policy_name == "AdministratorAccess"
}

# Check if MFA is enabled
_has_mfa_enabled(resource) if {
    resource.config.mfa_enabled == true
}

_has_mfa_enabled(resource) if {
    resource.config.has_mfa == true
}

# Check if the identity is trusted by an external account
_has_external_trust(resource) if {
    some trust in resource.config.trust_relationships
    trust.is_external == true
}

_has_external_trust(resource) if {
    some trust in resource.config.trust_relationships
    trust.trusted_account_id != resource.config.account_id
}

_has_external_trust(resource) if {
    resource.config.cross_account_trust_count > 0
}
