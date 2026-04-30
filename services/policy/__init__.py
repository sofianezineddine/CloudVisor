"""CloudVisor Policy Service.

Foundation 4 of the CloudVisor CNAPP platform - Policy & Rules Engine
using Open Policy Agent (OPA).

## Overview

The Policy Engine is the security brain of CloudVisor. All security
evaluation logic is expressed as Rego policies and evaluated by OPA.

## Key Features

- **Rego-based rules**: All security checks are Rego policies
- **Hot-reload**: Rules can be updated without service restart
- **Custom rules**: Organizations can write their own rules
- **Compliance mapping**: Rules mapped to CIS, SOC2, PCI-DSS, HIPAA, etc.
- **Batch evaluation**: Evaluate 10,000 resources in 30 seconds

## Rule Organization

```
rules/rego/
├── cspm/aws/         # AWS CSPM rules
├── cspm/azure/      # Azure CSPM rules
├── cspm/gcp/        # GCP CSPM rules
├── cspm/oci/        # OCI CSPM rules
├── kspm/            # Kubernetes security
├── iac/terraform/   # Terraform scanning
├── iac/helm/        # Helm chart scanning
├── cicd/            # CI/CD pipeline rules
├── cdr/             # Detection rules
└── custom/{org}/    # Custom rules per org
```

## Supported Frameworks

- CIS AWS/Azure/GCP/OCI
- SOC 2
- PCI-DSS
- HIPAA
- ISO 27001
- NIST 800-53
- GDPR
- FedRAMP

## API Endpoints

### Rules
- GET /internal/policy/rules - List rules
- GET /internal/policy/rules/{id} - Get rule
- POST /internal/policy/rules/custom - Create custom rule
- PUT /internal/policy/rules/custom/{id} - Update custom rule
- DELETE /internal/policy/rules/custom/{id} - Delete custom rule
- POST /internal/policy/rules/{id}/disable - Disable rule
- POST /internal/policy/rules/{id}/enable - Enable rule

### Evaluation
- POST /internal/policy/evaluate - Evaluate rules
- POST /internal/policy/evaluate/dry-run - Test custom rule

### Compliance
- GET /internal/policy/compliance - All frameworks
- GET /internal/policy/compliance/{framework} - Framework posture
"""

from .main import app

__version__ = "1.0.0"
__all__ = ["app"]
