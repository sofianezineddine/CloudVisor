# METADATA
# title: "RDS instance is publicly accessible"
# description: "RDS database instance is configured to be publicly accessible from the internet, exposing it to potential attacks."
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::rds::dbinstance
# compliance:
#   - framework: CIS-AWS
#     control: "2.3.2"
#   - framework: PCI-DSS
#     control: "1.3"
#   - framework: HIPAA
#     control: "164.312"
# remediation: "Set PubliclyAccessible to false on the RDS instance. Restrict security group access to only necessary CIDR ranges."
# version: "1.0.0"
# tags: [rds, database, public-access, network]

package cspm.aws.rds_publicly_accessible

import future.keywords.if

deny[finding] if {
    input.resource_type == "aws::rds::dbinstance"
    input.raw.PubliclyAccessible == true
    finding := {
        "rule_id": "aws-rds-publicly-accessible",
        "title": "RDS instance is publicly accessible",
        "severity": "HIGH",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": "RDS database is accessible from the internet. This exposes it to brute force and exploitation attacks.",
        "remediation": "Set PubliclyAccessible=false and restrict security group inbound rules.",
    }
}
