# METADATA
# title: Public Bucket with Sensitive Data and No Encryption
# description: >
#   Detects the toxic combination of a storage bucket that is publicly accessible,
#   contains sensitive data (tagged), and has no encryption enabled. Each issue alone
#   is concerning, but together they represent a critical data exposure risk.
# custom:
#   pattern_id: public-sensitive-unencrypted
#   components:
#     - public_access
#     - sensitive_data_tag
#     - no_encryption
#   elevated_severity: CRITICAL
#   description: Public bucket with sensitive data and no encryption

package cspm.toxic_combinations.public_sensitive_unencrypted

import rego.v1

# violation is true when a resource has all three toxic components:
# 1. Public access enabled
# 2. Tagged as containing sensitive data
# 3. No encryption configured
violation contains result if {
    resource := input.resource

    # Component 1: Public access is enabled
    _is_publicly_accessible(resource)

    # Component 2: Resource is tagged as containing sensitive data
    _has_sensitive_data_tag(resource)

    # Component 3: Encryption is not enabled
    not _has_encryption(resource)

    result := {
        "pattern_id": "public-sensitive-unencrypted",
        "resource_id": resource.id,
        "resource_type": resource.resource_type,
        "elevated_severity": "CRITICAL",
        "components": [
            {"check": "public_access", "status": "failed", "detail": "Resource is publicly accessible"},
            {"check": "sensitive_data_tag", "status": "present", "detail": "Resource contains sensitive data"},
            {"check": "no_encryption", "status": "failed", "detail": "Encryption is not enabled"},
        ],
        "description": "Public bucket with sensitive data and no encryption",
    }
}

# Check if the resource is publicly accessible
_is_publicly_accessible(resource) if {
    resource.config.public_access == true
}

_is_publicly_accessible(resource) if {
    resource.config.acl == "public-read"
}

_is_publicly_accessible(resource) if {
    resource.config.acl == "public-read-write"
}

# Check if the resource has a sensitive data tag
_has_sensitive_data_tag(resource) if {
    some tag in resource.tags
    lower(tag.key) == "sensitivity"
    lower(tag.value) == "high"
}

_has_sensitive_data_tag(resource) if {
    some tag in resource.tags
    lower(tag.key) == "data-classification"
    lower(tag.value) == "sensitive"
}

_has_sensitive_data_tag(resource) if {
    resource.config.contains_sensitive_data == true
}

# Check if encryption is enabled
_has_encryption(resource) if {
    resource.config.encryption.enabled == true
}

_has_encryption(resource) if {
    resource.config.server_side_encryption != null
    resource.config.server_side_encryption != ""
    resource.config.server_side_encryption != "none"
}
