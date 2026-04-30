# METADATA
# title: RDS instance is publicly accessible
# description: RDS database instance is configured to be publicly accessible from the internet.
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::rds::dbinstance
# remediation: Set PubliclyAccessible to false on the RDS instance and restrict security group access.
# version: 1.0.0

package cloudvisor.cspm.aws_rds_public

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::rds::dbinstance"
    input.resource.raw.PubliclyAccessible == true
    msg := sprintf("RDS instance '%v' is publicly accessible", [input.resource.name])
}
