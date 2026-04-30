# CloudVisor Connector Service

Cloud asset ingestion and discovery service - Foundation 1 of the CloudVisor CNAPP platform.

## Overview

The Connector service is responsible for:
- Establishing and maintaining read-only connections to customer cloud accounts
- Discovering cloud resources across AWS, Azure, GCP, and OCI
- Normalizing resources to the Common Data Model (CDM)
- Publishing resource events to Kafka for downstream processing

## Supported Resources

### AWS
EC2, VPC, Subnets, Security Groups, S3, IAM Users/Roles/Policies, RDS, Lambda, EKS, CloudFront, Route53, KMS, CloudTrail, SNS, SQS, DynamoDB, ElastiCache, ELB, API Gateway, Secrets Manager, ECR, EFS, Elastic IPs

### Azure
Virtual Machines, NSGs, Virtual Networks, Storage Accounts, SQL Servers, Azure Functions, AKS, App Services, Key Vaults, Azure AD, Role Assignments, Firewall, Load Balancers, Cosmos DB, Container Registry, Event Hubs

### GCP
Compute Instances, Firewall Rules, VPC Networks, Cloud Storage, Cloud SQL, Cloud Functions, GKE, Cloud Run, IAM Service Accounts, KMS Keys, BigQuery, Pub/Sub, DNS, Artifact Registry, Secret Manager

### OCI
Compute Instances, Security Lists, VCNs, Object Storage, Autonomous Databases, Functions, OKE Clusters, IAM Users/Groups/Policies, Vault Secrets, Load Balancers

## Configuration

Environment variables:
- `DB_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string  
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka broker address
- `OTEL_ENABLED` - Enable OpenTelemetry tracing
- `VAULT_ENABLED` - Enable HashiCorp Vault for credential storage

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /internal/accounts | Register new cloud account |
| GET | /internal/accounts | List all accounts |
| GET | /internal/accounts/{id} | Get account details |
| PATCH | /internal/accounts/{id} | Update account config |
| DELETE | /internal/accounts/{id} | Remove account |
| POST | /internal/accounts/{id}/sync | Trigger manual sync |
| GET | /internal/accounts/{id}/health | Get account health |
| GET | /internal/onboarding/{provider}/instructions | Get onboarding guide |

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python -m connector.main
```

## Docker

```bash
docker build -t cloudvisor-connector .
docker run -p 8000:8000 cloudvisor-connector
```