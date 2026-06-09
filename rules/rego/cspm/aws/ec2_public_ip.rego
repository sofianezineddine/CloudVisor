# METADATA
# title: "EC2 instance has a public IP address"
# description: "The EC2 instance has a public IP address assigned, making it directly reachable from the internet. Instances should be placed in private subnets and accessed through load balancers or bastion hosts."
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::ec2::instance
# compliance:
#   - framework: CIS-AWS
#     control: "5.6"
#   - framework: SOC2
#     control: "CC6.6"
# remediation: "Move the EC2 instance to a private subnet. Use an Application Load Balancer or NAT Gateway for internet-facing traffic. Use AWS Systems Manager Session Manager for administrative access instead of direct SSH/RDP."
# version: "1.0.0"
# tags: [ec2, public-ip, network, exposure]

package cspm.aws.ec2_public_ip

deny[finding] if {
    input.resource_type == "aws::ec2::instance"
    input.raw.PublicIpAddress
    input.raw.PublicIpAddress != ""
    input.raw.State.Name == "running"
    finding := {
        "rule_id": "aws-ec2-public-ip",
        "title": "EC2 instance has a public IP address",
        "severity": "MEDIUM",
        "resource_id": input.cloud_resource_id,
        "resource_name": input.name,
        "description": sprintf("EC2 instance '%v' has public IP '%v' and is directly reachable from the internet.", [input.name, input.raw.PublicIpAddress]),
        "remediation": "Move the instance to a private subnet and use a load balancer or NAT gateway for internet-facing traffic.",
    }
}
