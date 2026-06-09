# METADATA
# title: Default VPC In Use
# description: The default VPC is being used, which may have overly permissive settings and lacks proper network segmentation
# severity: LOW
# category: vpc
# provider: aws
# resource_type: aws::vpc::vpc
# remediation: Create a custom VPC with appropriate subnets, route tables, and security groups, then migrate resources out of the default VPC
# compliance: CIS-AWS:5.1, SOC2:CC6.1
package cspm.aws.vpc

deny[finding] if {
    input.resource_type == "aws::vpc::vpc"
    input.raw.IsDefault == true
    finding := {
        "rule_id": "cspm-aws-vpc-002",
        "title": "Default VPC In Use",
        "severity": "LOW",
        "description": "The default VPC is being used, which may have overly permissive settings and lacks proper network segmentation",
        "remediation": "Create a custom VPC with appropriate subnets, route tables, and security groups, then migrate resources out of the default VPC",
    }
}
