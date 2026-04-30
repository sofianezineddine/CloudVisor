# METADATA
# title: "S3 Bucket Public Access Block Disabled"
# description: "S3 bucket does not have public access block enabled, allowing potential public access"
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::s3::bucket
# compliance:
#   - framework: CIS-AWS
#     control: "2.1.5"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: PCI-DSS
#     control: "1.3"
# remediation: "Enable S3 bucket public access block: AWS Console > S3 > Bucket > Permissions > Block public access > Edit > Block all public access"

package cloudvisor.cspm.aws.s3_public_access

import future.keywords

deny[finding] {
    input.resource_type == "aws::s3::bucket"
    
    # Check if public access block is disabled or missing
    public_access_block := input.raw.PublicAccessBlockConfiguration
    
    # If no public access block configuration exists, it's a violation
    not public_access_block
    
    finding := {
        "rule_id": "aws-s3-public-access-block-disabled",
        "title": "S3 bucket public access block is disabled",
        "description": sprintf("S3 bucket '%s' does not have public access block enabled, making it potentially accessible to the public", [input.name]),
        "severity": "CRITICAL",
        "remediation": "Enable public access block for this S3 bucket to prevent public access",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.1.5"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "PCI-DSS", "control": "1.3"}
        ]
    }
}

deny[finding] {
    input.resource_type == "aws::s3::bucket"
    
    # Check if any public access block setting is disabled
    public_access_block := input.raw.PublicAccessBlockConfiguration
    public_access_block
    
    # Any of these being false is a violation
    settings := [
        public_access_block.BlockPublicAcls,
        public_access_block.IgnorePublicAcls,
        public_access_block.BlockPublicPolicy,
        public_access_block.RestrictPublicBuckets
    ]
    
    some setting in settings
    setting == false
    
    finding := {
        "rule_id": "aws-s3-public-access-block-partial",
        "title": "S3 bucket public access block is partially disabled",
        "description": sprintf("S3 bucket '%s' has some public access block settings disabled", [input.name]),
        "severity": "HIGH",
        "remediation": "Enable all public access block settings for this S3 bucket",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "2.1.5"},
            {"framework": "SOC2", "control": "CC6.1"}
        ]
    }
}