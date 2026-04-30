# CloudVisor Policy Service

Policy Engine - OPA/Rego Rules Evaluation - Foundation 4 of the CloudVisor CNAPP platform.

## Overview

The Policy Engine is the sole location where security evaluation logic lives.
Every security check is expressed as a Rego policy and evaluated by this service.

## Features

- **Rego-based policies**: All security rules in Rego
- **Hot-reload**: Rules updated from Git without restart
- **Custom rules**: Enterprise customers can write their own
- **Compliance mapping**: CIS, SOC2, PCI-DSS, HIPAA, ISO27001
- **Batch evaluation**: 10,000 resources in 30 seconds

## Rule Metadata Format

```rego
# METADATA
# title: "S3 bucket must not have public access"
# description: "Public S3 buckets expose data..."
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::s3::bucket
# remediation: "1. Go to S3 console..."
# version: "1.0.0"
# tags: [storage, public-access]

package cspm.aws.s3

deny[finding] {
    input.resource_type == "aws::s3::bucket"
    not input.raw.PublicAccessBlockConfiguration.BlockPublicAcls
    finding := {"rule_id": "s3-public-access-block"}
}
```

## Configuration

```bash
POLICY_OPA_URL=http://localhost:8181
POLICY_RULES_REPO_URL=https://github.com/cloudvisor/rules
POLICY_RULES_REPO_PATH=./rules/rego
POLICY_OPA_CHECK_INTERVAL_SECONDS=60
```

## Running

```bash
pip install -r requirements.txt
python -m policy.main
```

## Docker

```bash
docker build -t cloudvisor-policy .
docker run -p 8003:8003 cloudvisor-policy
```