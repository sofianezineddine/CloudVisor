# METADATA
# title: OCI Object Storage bucket has public access
# description: OCI Object Storage bucket is configured with public access, exposing data to the internet.
# severity: CRITICAL
# category: cspm
# provider: oci
# resource_type: oci::objectstorage::bucket
# remediation: Set the bucket's publicAccessType to NoPublicAccess in the OCI console.
# version: 1.0.0

package cloudvisor.cspm.oci_bucket_public_access

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "oci::objectstorage::bucket"
    input.resource.raw.public_access_type != "NoPublicAccess"
    msg := sprintf("OCI bucket '%v' has public access type: %v",
        [input.resource.name, input.resource.raw.public_access_type])
}
