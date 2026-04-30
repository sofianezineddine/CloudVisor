# METADATA
# title: S3 Bucket ACL Allows Public Read or Write
# description: The S3 bucket ACL is set to allow public read or write access, exposing bucket contents to the internet
# severity: CRITICAL
# category: s3
# provider: aws
# resource_type: aws::s3::bucket
# remediation: Change the bucket ACL to private and use bucket policies for controlled access
# compliance: CIS-AWS:2.1.5, SOC2:CC6.1, PCI-DSS:1.3.2
package cspm.aws.s3

import future.keywords

deny[finding] {
    input.resource_type == "aws::s3::bucket"
    input.raw.ACL == "public-read"
    finding := {
        "rule_id": "cspm-aws-s3-002",
        "title": "S3 Bucket ACL Allows Public Read",
        "severity": "CRITICAL",
        "description": "The S3 bucket ACL is set to public-read, exposing all bucket objects to the internet",
        "remediation": "Change the bucket ACL to private and use bucket policies for controlled access",
    }
}

deny[finding] {
    input.resource_type == "aws::s3::bucket"
    input.raw.ACL == "public-read-write"
    finding := {
        "rule_id": "cspm-aws-s3-002",
        "title": "S3 Bucket ACL Allows Public Read and Write",
        "severity": "CRITICAL",
        "description": "The S3 bucket ACL is set to public-read-write, allowing anyone to read and write bucket objects",
        "remediation": "Change the bucket ACL to private and use bucket policies for controlled access",
    }
}

deny[finding] {
    input.resource_type == "aws::s3::bucket"
    input.raw.ACL == "authenticated-read"
    finding := {
        "rule_id": "cspm-aws-s3-002",
        "title": "S3 Bucket ACL Allows Authenticated Read",
        "severity": "CRITICAL",
        "description": "The S3 bucket ACL is set to authenticated-read, allowing any authenticated AWS user to read bucket objects",
        "remediation": "Change the bucket ACL to private and use bucket policies for controlled access",
    }
}
