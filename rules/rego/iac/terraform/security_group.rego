# METADATA
# title: Security Group Allows Unrestricted Ingress
# description: Terraform aws_security_group has overly permissive ingress rules allowing traffic from 0.0.0.0/0.
# severity: HIGH
# category: iac
# provider: aws
# resource_type: aws_security_group
# version: 1.0.0

package cloudvisor.iac.terraform.security_group

# Sensitive ports that should never be open to the internet
sensitive_ports := {22, 3389, 3306, 5432, 1433, 27017, 6379, 9200, 8080, 8443}

violation contains finding if {
    input.resource.type == "aws_security_group"
    properties := input.resource.properties
    ingress := properties.ingress[_]
    ingress.cidr_blocks[_] == "0.0.0.0/0"
    port := ingress.from_port
    port in sensitive_ports
    finding := {
        "rule_id": "iac.terraform.sg-sensitive-port-open",
        "severity": "CRITICAL",
        "title": "Security Group Exposes Sensitive Port to Internet",
        "description": sprintf("Security group '%v' allows inbound traffic from 0.0.0.0/0 on sensitive port %v. This exposes the service to the entire internet.", [input.resource.identifier, port]),
        "remediation": sprintf("Restrict the ingress rule for port %v to specific trusted CIDR ranges instead of 0.0.0.0/0. Use a VPN or bastion host for administrative access.", [port]),
    }
}

violation contains finding if {
    input.resource.type == "aws_security_group"
    properties := input.resource.properties
    ingress := properties.ingress[_]
    ingress.cidr_blocks[_] == "0.0.0.0/0"
    ingress.from_port == 0
    ingress.to_port == 65535
    finding := {
        "rule_id": "iac.terraform.sg-all-ports-open",
        "severity": "CRITICAL",
        "title": "Security Group Allows All Ports Open to Internet",
        "description": sprintf("Security group '%v' allows all inbound traffic (ports 0-65535) from 0.0.0.0/0. This is extremely dangerous and exposes all services.", [input.resource.identifier]),
        "remediation": "Remove the overly permissive ingress rule. Define specific port ranges needed for your application and restrict source CIDR blocks to known IP ranges.",
    }
}

violation contains finding if {
    input.resource.type == "aws_security_group"
    properties := input.resource.properties
    ingress := properties.ingress[_]
    ingress.cidr_blocks[_] == "::/0"
    port := ingress.from_port
    port in sensitive_ports
    finding := {
        "rule_id": "iac.terraform.sg-sensitive-port-open-ipv6",
        "severity": "CRITICAL",
        "title": "Security Group Exposes Sensitive Port to Internet (IPv6)",
        "description": sprintf("Security group '%v' allows inbound IPv6 traffic from ::/0 on sensitive port %v.", [input.resource.identifier, port]),
        "remediation": sprintf("Restrict the ingress rule for port %v to specific trusted IPv6 CIDR ranges instead of ::/0.", [port]),
    }
}

violation contains finding if {
    input.resource.type == "aws_security_group"
    properties := input.resource.properties
    egress := properties.egress[_]
    egress.cidr_blocks[_] == "0.0.0.0/0"
    egress.from_port == 0
    egress.to_port == 65535
    finding := {
        "rule_id": "iac.terraform.sg-unrestricted-egress",
        "severity": "MEDIUM",
        "title": "Security Group Allows Unrestricted Egress",
        "description": sprintf("Security group '%v' allows all outbound traffic to 0.0.0.0/0. Consider restricting egress to required destinations.", [input.resource.identifier]),
        "remediation": "Define specific egress rules that limit outbound traffic to only the required destinations and ports for your application.",
    }
}
