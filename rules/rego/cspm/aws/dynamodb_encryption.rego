# METADATA
# title: DynamoDB table encryption not enabled
# description: DynamoDB table is not encrypted with a customer-managed KMS key.
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::dynamodb::table
# remediation: Enable server-side encryption on the DynamoDB table using AWS KMS. Use a customer-managed key for additional control.
# version: 1.0.0

package cloudvisor.cspm.aws_dynamodb_encryption

deny[msg] if {
    input.resource.resource_type == "aws::dynamodb::table"
    sse := input.resource.raw.SSEDescription
    sse.Status != "ENABLED"
    msg := sprintf("DynamoDB table '%v' does not have server-side encryption enabled", [input.resource.name])
}

deny[msg] if {
    input.resource.resource_type == "aws::dynamodb::table"
    not input.resource.raw.SSEDescription
    msg := sprintf("DynamoDB table '%v' does not have server-side encryption configured", [input.resource.name])
}
