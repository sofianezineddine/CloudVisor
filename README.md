# CloudVisor CNAPP Platform

**Version:** 2.0  
**Status:** Under Development

## Architecture Overview

CloudVisor is a modular, API-first Cloud-Native Application Protection Platform (CNAPP) providing unified security from code to runtime across AWS, Azure, GCP, and OCI.

## Build Order

### Foundational Services (Must be built first)
1. **Cloud Connector** (`services/connector/`) - Cloud asset ingestion
2. **Asset Graph** (`services/graph/`) - Neo4j asset relationships
3. **Auth Service** (`services/auth/`) - Multi-tenant RBAC
4. **Policy Engine** (`services/policy/`) - OPA/Rego rules
5. **Alert Pipeline** (`services/alert/`) - Unified findings
6. **API & Dashboard** (`services/api/` + `apps/web/`) - Public API + UI

### Security Modules
7. CSPM - Cloud Security Posture Management
8. CWPP - Cloud Workload Protection Platform
9. CI/CD Security
10. CIEM - Cloud Infrastructure Entitlements
11. KSPM - Kubernetes Security Posture
12. DSPM - Data Security Posture
13. CDR - Cloud Detection & Response
14. AIOps + Copilot

## Quick Start

See individual service README files for setup instructions.

## Tech Stack
- Backend: Python 3.12 (FastAPI, Faust)
- Frontend: React 18 + TypeScript + Next.js 14
- Databases: PostgreSQL 15 (RLS), Neo4j 5.x
- Cache: Redis 7
- Message Broker: Apache Kafka 3.x
- Policy: Open Policy Agent (OPA) 0.60+
- Infrastructure: Kubernetes 1.28+, Terraform 1.6+
