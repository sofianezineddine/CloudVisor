# METADATA
# title: Secrets Manager secret rotation not enabled
# description: AWS Secrets Manager secret does not have automatic rotation enabled, increasing the risk of credential compromise.
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::secretsmanager::secret
# remediation: Enable automatic rotation for the secret. Configure a Lambda rotation function or use AWS-managed rotation for supported services.
# version: 1.0.0

package cloudvisor.cspm.aws_secretsmanager_rotation

deny[msg] if {
    input.resource.resource_type == "aws::secretsmanager::secret"
    not input.resource.raw.RotationEnabled
    msg := sprintf("Secrets Manager secret '%v' does not have automatic rotation enabled", [input.resource.name])
}
