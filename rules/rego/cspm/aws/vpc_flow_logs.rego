# METADATA
# title: VPC flow logs not enabled
# description: VPC does not have flow logs enabled, limiting network traffic visibility for security investigations.
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::ec2::vpc
# remediation: Enable VPC flow logs and send them to CloudWatch Logs or S3 for analysis.
# version: 1.0.0

package cloudvisor.cspm.aws_vpc_flow_logs

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::ec2::vpc"
    not input.resource.raw.FlowLogsEnabled
    msg := sprintf("VPC '%v' does not have flow logs enabled", [input.resource.name])
}
