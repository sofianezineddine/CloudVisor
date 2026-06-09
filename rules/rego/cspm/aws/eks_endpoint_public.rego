# METADATA
# title: EKS cluster API endpoint is publicly accessible
# description: EKS cluster has public endpoint access enabled without IP restrictions, allowing anyone to reach the Kubernetes API.
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::eks::cluster
# remediation: Disable public endpoint access or restrict it to specific CIDR ranges. Enable private endpoint access.
# version: 1.0.0

package cloudvisor.cspm.aws_eks_endpoint_public

deny[msg] if {
    input.resource.resource_type == "aws::eks::cluster"
    input.resource.raw.ResourcesVpcConfig.EndpointPublicAccess == true
    public_cidrs := input.resource.raw.ResourcesVpcConfig.PublicAccessCidrs
    count(public_cidrs) == 1
    public_cidrs[0] == "0.0.0.0/0"
    msg := sprintf("EKS cluster '%v' API endpoint is publicly accessible from 0.0.0.0/0", [input.resource.name])
}
