# METADATA
# title: EBS volume is not encrypted
# description: EBS volume does not have encryption enabled, exposing data at rest.
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::ec2::volume
# remediation: Enable EBS encryption. Use AWS KMS to manage encryption keys. Enable default EBS encryption in the account settings.
# version: 1.0.0

package cloudvisor.cspm.aws_ebs_encryption

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::ec2::volume"
    not input.resource.raw.Encrypted
    msg := sprintf("EBS volume '%v' is not encrypted", [input.resource.name])
}
