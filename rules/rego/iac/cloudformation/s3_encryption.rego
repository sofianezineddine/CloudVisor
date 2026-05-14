# METADATA
# title: CloudFormation S3 Bucket Missing Encryption
# description: CloudFormation AWS::S3::Bucket resource does not have server-side encryption configured.
# severity: HIGH
# category: iac
# provider: aws
# resource_type: AWS::S3::Bucket
# version: 1.0.0

package cloudvisor.iac.cloudformation.s3_encryption

import future.keywords.if
import future.keywords.in
import future.keywords.contains

violation contains finding if {
    input.resource.type == "AWS::S3::Bucket"
    properties := input.resource.properties
    not properties.BucketEncryption
    finding := {
        "rule_id": "iac.cloudformation.s3-encryption-missing",
        "severity": "HIGH",
        "title": "S3 Bucket Missing Server-Side Encryption",
        "description": sprintf("CloudFormation S3 bucket '%v' does not have BucketEncryption configured. Data at rest is not protected.", [input.resource.identifier]),
        "remediation": "Add BucketEncryption property with ServerSideEncryptionConfiguration specifying SSEAlgorithm: aws:kms and a KMSMasterKeyID.",
    }
}

violation contains finding if {
    input.resource.type == "AWS::S3::Bucket"
    properties := input.resource.properties
    enc_config := properties.BucketEncryption
    rules := enc_config.ServerSideEncryptionConfiguration
    rule := rules[_]
    default_enc := rule.ServerSideEncryptionByDefault
    default_enc.SSEAlgorithm == "AES256"
    finding := {
        "rule_id": "iac.cloudformation.s3-encryption-not-kms",
        "severity": "MEDIUM",
        "title": "S3 Bucket Using AES256 Instead of KMS",
        "description": sprintf("CloudFormation S3 bucket '%v' uses AES256 encryption instead of AWS KMS. KMS provides better key management and audit capabilities.", [input.resource.identifier]),
        "remediation": "Change SSEAlgorithm to 'aws:kms' and specify a KMSMasterKeyID for better key management, rotation, and CloudTrail audit logging.",
    }
}

violation contains finding if {
    input.resource.type == "AWS::S3::Bucket"
    properties := input.resource.properties
    not properties.PublicAccessBlockConfiguration
    finding := {
        "rule_id": "iac.cloudformation.s3-no-public-access-block",
        "severity": "HIGH",
        "title": "S3 Bucket Missing Public Access Block",
        "description": sprintf("CloudFormation S3 bucket '%v' does not have PublicAccessBlockConfiguration. The bucket may be publicly accessible.", [input.resource.identifier]),
        "remediation": "Add PublicAccessBlockConfiguration with BlockPublicAcls: true, BlockPublicPolicy: true, IgnorePublicAcls: true, RestrictPublicBuckets: true.",
    }
}
