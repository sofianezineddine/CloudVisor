# METADATA
# title: "EBS Volume Not Encrypted"
# description: "EBS volume is not encrypted at rest"
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::ec2::volume
# compliance:
#   - framework: CIS-AWS
#     control: "2.2.1"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: HIPAA
#     control: "164.312(a)(2)(iv)"
# remediation: "Enable EBS volume encryption: AWS Console > EC2 > Volumes > Create Volume > Encryption > Enabled"

package cloudvisor.cspm.aws.ebs_encryption

import future.keywords

deny[finding] {
    input.resource_type == "aws::ec2::volume"
    
    # Check if volume is encrypted
    encrypted := input.raw.Encrypted
    encrypted == false
    
    finding := {
        "rule_id": "aws-ebs-volume-not-encrypted",
        "title": "EBS volume is not encrypted",
        "description": sprintf("EBS volume '%s' is not encrypted at rest", [input.name]),
        "severity": "HIGH",
        "remediation": "Enable encryption for this EBS volume. Note: Existing volumes cannot be encrypted in-place, create encrypted snapshot and new volume",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.2.1"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "HIPAA", "control": "164.312(a)(2)(iv)"}
        ]
    }
}