# METADATA
# title: Terraform security group allows unrestricted inbound access
# description: Terraform aws_security_group resource has an ingress rule allowing traffic from 0.0.0.0/0.
# severity: HIGH
# category: iac
# provider: aws
# resource_type: terraform::aws_security_group
# remediation: Restrict ingress rules to specific CIDR ranges. Never use 0.0.0.0/0 for sensitive ports.
# version: 1.0.0

package cloudvisor.iac.terraform_sg_unrestricted

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "terraform::aws_security_group"
    ingress := input.resource.raw.ingress[_]
    ingress.cidr_blocks[_] == "0.0.0.0/0"
    ingress.from_port == 0
    ingress.to_port == 0
    msg := sprintf("Terraform security group '%v' allows all inbound traffic from 0.0.0.0/0",
        [input.resource.name])
}
