# METADATA
# title: CloudFormation Security Group Allows Unrestricted Ingress
# description: CloudFormation AWS::EC2::SecurityGroup has overly permissive ingress rules.
# severity: HIGH
# category: iac
# provider: aws
# resource_type: AWS::EC2::SecurityGroup
# version: 1.0.0

package cloudvisor.iac.cloudformation.security_group

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# Sensitive ports that should never be open to the internet
sensitive_ports := {22, 3389, 3306, 5432, 1433, 27017, 6379, 9200}

violation contains finding if {
    input.resource.type == "AWS::EC2::SecurityGroup"
    properties := input.resource.properties
    ingress := properties.SecurityGroupIngress[_]
    ingress.CidrIp == "0.0.0.0/0"
    port := ingress.FromPort
    port in sensitive_ports
    finding := {
        "rule_id": "iac.cloudformation.sg-sensitive-port-open",
        "severity": "CRITICAL",
        "title": "Security Group Exposes Sensitive Port to Internet",
        "description": sprintf("CloudFormation security group '%v' allows inbound traffic from 0.0.0.0/0 on sensitive port %v.", [input.resource.identifier, port]),
        "remediation": sprintf("Restrict the SecurityGroupIngress rule for port %v to specific trusted CIDR ranges. Use a VPN or bastion host for administrative access.", [port]),
    }
}

violation contains finding if {
    input.resource.type == "AWS::EC2::SecurityGroup"
    properties := input.resource.properties
    ingress := properties.SecurityGroupIngress[_]
    ingress.CidrIp == "0.0.0.0/0"
    ingress.FromPort == 0
    ingress.ToPort == 65535
    finding := {
        "rule_id": "iac.cloudformation.sg-all-ports-open",
        "severity": "CRITICAL",
        "title": "Security Group Allows All Ports Open to Internet",
        "description": sprintf("CloudFormation security group '%v' allows all inbound traffic (ports 0-65535) from 0.0.0.0/0.", [input.resource.identifier]),
        "remediation": "Remove the overly permissive ingress rule. Define specific port ranges and restrict source CIDR blocks to known IP ranges.",
    }
}

violation contains finding if {
    input.resource.type == "AWS::EC2::SecurityGroup"
    properties := input.resource.properties
    ingress := properties.SecurityGroupIngress[_]
    ingress.CidrIpv6 == "::/0"
    port := ingress.FromPort
    port in sensitive_ports
    finding := {
        "rule_id": "iac.cloudformation.sg-sensitive-port-open-ipv6",
        "severity": "CRITICAL",
        "title": "Security Group Exposes Sensitive Port to Internet (IPv6)",
        "description": sprintf("CloudFormation security group '%v' allows inbound IPv6 traffic from ::/0 on sensitive port %v.", [input.resource.identifier, port]),
        "remediation": sprintf("Restrict the SecurityGroupIngress rule for port %v to specific trusted IPv6 CIDR ranges.", [port]),
    }
}
