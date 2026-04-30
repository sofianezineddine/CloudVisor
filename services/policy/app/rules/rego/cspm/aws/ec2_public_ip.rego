package cloudvisor.cspm.aws.ec2_public_ip

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::ec2::instance"
    input.resource.raw.PublicIpAddress != null
    input.resource.raw.PublicIpAddress != ""
    msg := sprintf("EC2 instance '%v' has a public IP address (%v)", [input.resource.name, input.resource.raw.PublicIpAddress])
}
