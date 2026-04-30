"""CloudVisor Cloud Connector Service.

This service is responsible for:
- Establishing and maintaining connections to cloud accounts (AWS, Azure, GCP, OCI)
- Discovering cloud resources and ingesting them into the platform
- Normalizing resources to the Common Data Model (CDM)
- Publishing resource events to Kafka for downstream processing

## Architecture

The connector follows an event-driven architecture:
1. Cloud accounts are registered via REST API
2. Initial full sync discovers all resources
3. Periodic incremental sync detects changes
4. All resource events are published to Kafka
5. Real-time updates can be received via cloud provider webhooks

## Supported Cloud Providers

- AWS: EC2, VPC, S3, IAM, RDS, Lambda, EKS, etc.
- Azure: VMs, VNETs, Storage, SQL, AKS, etc.
- GCP: Compute, Storage, GKE, Cloud Functions, etc.
- OCI: Compute, Object Storage, Autonomous DB, OKE, etc.

## Setup

Required environment variables:
- DATABASE_URL: PostgreSQL connection string
- REDIS_URL: Redis connection string
- KAFKA_BOOTSTRAP_SERVERS: Kafka broker address
- VAULT_URL: HashiCorp Vault address (optional)

## API Endpoints

- POST /internal/accounts - Register new cloud account
- GET /internal/accounts - List all accounts
- GET /internal/accounts/{id} - Get account details
- PATCH /internal/accounts/{id} - Update account config
- DELETE /internal/accounts/{id} - Remove account
- POST /internal/accounts/{id}/sync - Trigger manual sync
- GET /internal/accounts/{id}/health - Get account health
- GET /internal/onboarding/{provider}/instructions - Get onboarding guide
"""

from .main import app

__version__ = "1.0.0"
__all__ = ["app"]
