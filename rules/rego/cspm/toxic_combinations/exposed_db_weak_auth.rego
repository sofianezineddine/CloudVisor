# METADATA
# title: Exposed Database with Weak Authentication
# description: >
#   Detects the toxic combination of a database instance that is publicly exposed
#   (accessible from the internet), uses weak authentication (default credentials,
#   short passwords, or no password), and lacks network-level restrictions.
#   This combination creates a critical risk of unauthorized data access.
# custom:
#   pattern_id: exposed-db-weak-auth
#   components:
#     - public_exposure
#     - weak_authentication
#     - no_network_restriction
#   elevated_severity: CRITICAL
#   description: Exposed database with weak authentication and no network restriction

package cspm.toxic_combinations.exposed_db_weak_auth

import rego.v1

# violation is true when a database resource has all three toxic components:
# 1. Publicly exposed (internet-accessible)
# 2. Weak authentication configured
# 3. No network-level access restrictions
violation contains result if {
    resource := input.resource

    # Component 1: Database is publicly exposed
    _is_publicly_exposed(resource)

    # Component 2: Weak authentication
    _has_weak_auth(resource)

    # Component 3: No network restriction
    not _has_network_restriction(resource)

    result := {
        "pattern_id": "exposed-db-weak-auth",
        "resource_id": resource.id,
        "resource_type": resource.resource_type,
        "elevated_severity": "CRITICAL",
        "components": [
            {"check": "public_exposure", "status": "failed", "detail": "Database is publicly accessible"},
            {"check": "weak_authentication", "status": "failed", "detail": "Weak authentication configured"},
            {"check": "no_network_restriction", "status": "failed", "detail": "No network-level access restriction"},
        ],
        "description": "Exposed database with weak authentication and no network restriction",
    }
}

# Check if the database is publicly exposed
_is_publicly_exposed(resource) if {
    resource.config.publicly_accessible == true
}

_is_publicly_exposed(resource) if {
    resource.config.is_internet_exposed == true
}

_is_publicly_exposed(resource) if {
    some sg in resource.config.security_groups
    some rule in sg.ingress_rules
    rule.cidr == "0.0.0.0/0"
}

# Check if authentication is weak
_has_weak_auth(resource) if {
    resource.config.authentication.password_length < 12
}

_has_weak_auth(resource) if {
    resource.config.authentication.uses_default_credentials == true
}

_has_weak_auth(resource) if {
    resource.config.authentication.password_policy_enforced == false
}

_has_weak_auth(resource) if {
    resource.config.authentication.auth_method == "password"
    not resource.config.authentication.ssl_required
}

# Check if network restrictions are in place
_has_network_restriction(resource) if {
    count(resource.config.allowed_ip_ranges) > 0
    not _allows_all_ips(resource)
}

_has_network_restriction(resource) if {
    resource.config.vpc_only == true
}

_has_network_restriction(resource) if {
    resource.config.private_endpoint_enabled == true
}

# Helper: check if allowed IPs include 0.0.0.0/0
_allows_all_ips(resource) if {
    some cidr in resource.config.allowed_ip_ranges
    cidr == "0.0.0.0/0"
}
