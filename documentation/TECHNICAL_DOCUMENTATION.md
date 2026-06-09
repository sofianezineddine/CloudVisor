# CloudVisor CNAPP Platform — Complete Technical Documentation

**Version:** 2.0  
**Status:** Under Development  
**Last Updated:** 2025  
**Scope:** Full-stack architecture, microservices, infrastructure, and security analysis

---

## Table of Contents

1. [Platform Overview](#platform-overview)
2. [Project Structure](#project-structure)
3. [Architecture & Design](#architecture--design)
4. [Frontend Documentation](#frontend-documentation)
5. [Backend Documentation](#backend-documentation)
6. [Database Documentation](#database-documentation)
7. [DevOps & Infrastructure](#devops--infrastructure)
8. [Security Analysis](#security-analysis)
9. [API Documentation](#api-documentation)
10. [AI/ML Components](#aiml-components)
11. [Code Quality & Engineering Practices](#code-quality--engineering-practices)
12. [Setup & Development Guide](#setup--development-guide)
13. [Testing & QA](#testing--qa)
14. [Improvement Recommendations](#improvement-recommendations)

---

## Platform Overview

### Purpose & Scope

CloudVisor is an **enterprise-grade Cloud-Native Application Protection Platform (CNAPP)** designed to provide unified security governance across cloud environments. It combines cloud security best practices with real-time threat detection and automated remediation.

**Core Mission:** Enable security teams to identify, prioritize, and remediate cloud risks before they become breaches.

### Business Goals

1. **Unified Security Posture** — Single pane of glass for multi-cloud security
2. **Risk Prioritization** — AI-driven risk scoring to focus on high-impact findings
3. **Compliance Automation** — Automated compliance checking (CIS, SOC2, PCI-DSS, HIPAA, ISO27001)
4. **Incident Response** — Rapid detection and remediation of security threats
5. **Developer Enablement** — Shift-left security with CI/CD integration
6. **Cost Optimization** — Identify wasteful and misconfigured resources

### Key Features

| Feature | Module | Status |
|---------|--------|--------|
| Multi-cloud asset discovery | Connector + Graph | ✅ Foundation |
| Security posture management | CSPM | ✅ Foundation |
| Workload protection | CWPP | ✅ Foundation |
| CI/CD security scanning | CI/CD Security | ⚠️ In Progress |
| Cloud infrastructure entitlements | CIEM | ⚠️ In Progress |
| Kubernetes security | KSPM | ⚠️ In Progress |
| Data security posture | DSPM | ⚠️ In Progress |
| Detection & response | CDR | ⚠️ In Progress |
| AIOps + AI Copilot | Copilot + Keep | ✅ MVP Ready |

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CloudVisor CNAPP Platform                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                       Presentation Layer                         │  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │  Next.js Frontend (React 18 + TypeScript)              │   │  │
│  │  │  • Dashboard (Risk Score, Metrics)                     │   │  │
│  │  │  • Findings (Orca-style cards)                         │   │  │
│  │  │  • Compliance (Prisma-style donut charts)              │   │  │
│  │  │  • AI Copilot (Claude-powered Q&A)                     │   │  │
│  │  └─────────────────────────────────────────────────────────┘   │  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │  WebSocket Layer (Soketi + Pusher)                     │   │  │
│  │  │  • Real-time updates (findings, incidents)             │   │  │
│  │  │  • Multi-user presence                                  │   │  │
│  │  └─────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      API Gateway Layer                           │  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │  Nginx (Reverse Proxy)                                  │   │  │
│  │  │  • Route aggregation (/auth, /v1, /app, /graphql)      │   │  │
│  │  │  • SSL termination                                      │   │  │
│  │  │  • Security headers                                     │   │  │
│  │  │  • Gzip compression                                     │   │  │
│  │  │  • Same-origin cookie proxy (HttpOnly)                  │   │  │
│  │  └─────────────────────────────────────────────────────────┘   │  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │  Public API Gateway (FastAPI, port 8005)               │   │  │
│  │  │  • REST endpoints (/v1/assets, /v1/findings, etc.)     │   │  │
│  │  │  • GraphQL endpoint (/graphql)                          │   │  │
│  │  │  • Rate limiting (Redis-backed)                         │   │  │
│  │  │  • JWT + API Key authentication                         │   │  │
│  │  └─────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   Microservices Layer                            │  │
│  │                                                                    │  │
│  │  Foundation Services (Build Order):                              │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                      │  │
│  │  │ Connector        │  │ Graph Service    │                      │  │
│  │  │ (Port 8000)      │  │ (Port 8001)      │                      │  │
│  │  │ • Cloud account  │  │ • Asset indexing │                      │  │
│  │  │   discovery      │  │ • Relationships  │                      │  │
│  │  │ • Multi-cloud    │  │ • Risk scoring   │                      │  │
│  │  │   support        │  │ • Attack paths   │                      │  │
│  │  └──────────────────┘  └──────────────────┘                      │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                      │  │
│  │  │ Auth Service     │  │ Policy Service   │                      │  │
│  │  │ (Port 8002)      │  │ (Port 8003)      │                      │  │
│  │  │ • Multi-tenant   │  │ • OPA/Rego rules │                      │  │
│  │  │   RBAC           │  │ • Rule engine    │                      │  │
│  │  │ • JWT + API keys │  │ • Compliance     │                      │  │
│  │  │ • MFA support    │  │   mapping        │                      │  │
│  │  └──────────────────┘  └──────────────────┘                      │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                      │  │
│  │  │ Alert Service    │  │ CSPM Service     │                      │  │
│  │  │ (Port 8004)      │  │ (Port 8006)      │                      │  │
│  │  │ • Finding        │  │ • Cloud posture  │                      │  │
│  │  │   ingestion      │  │   checking       │                      │  │
│  │  │ • Deduplication  │  │ • Provider-      │                      │  │
│  │  │ • Notifications  │  │   specific logic │                      │  │
│  │  │ • SLA tracking   │  │ • Remediation    │                      │  │
│  │  └──────────────────┘  └──────────────────┘                      │  │
│  │                                                                    │  │
│  │  AI & Operations Services:                                       │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                      │  │
│  │  │ Copilot (Q)      │  │ AI Router        │                      │  │
│  │  │ (Port 8010)      │  │ (Port 8015)      │                      │  │
│  │  │ • RAG pipeline   │  │ • LLM gateway    │                      │  │
│  │  │ • Claude/API     │  │ • Multi-provider │                      │  │
│  │  │ • Query audit    │  │   support        │                      │  │
│  │  │ • Intent routing │  │ • Streaming      │                      │  │
│  │  └──────────────────┘  └──────────────────┘                      │  │
│  │  ┌──────────────────┐                                            │  │
│  │  │ Keep (AIOps)     │                                            │  │
│  │  │ (Port 8007)      │                                            │  │
│  │  │ • Alert ingestion│                                            │  │
│  │  │ • Correlations   │                                            │  │
│  │  │ • Incident groups│                                            │  │
│  │  │ • Runbooks       │                                            │  │
│  │  └──────────────────┘                                            │  │
│  │                                                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Infrastructure Layer                          │  │
│  │                                                                    │  │
│  │  Databases:                                                      │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                      │  │
│  │  │ PostgreSQL 15    │  │ Neo4j 5.15       │                      │  │
│  │  │ • Multi-tenant   │  │ • Asset graph    │                      │  │
│  │  │   data store     │  │ • Relationships  │                      │  │
│  │  │ • RLS policies   │  │ • Attack paths   │                      │  │
│  │  │ • JSONB columns  │  │ • Index: 2-5M    │                      │  │
│  │  └──────────────────┘  └──────────────────┘                      │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                      │  │
│  │  │ Elasticsearch 8  │  │ Redis 7          │                      │  │
│  │  │ • Finding search │  │ • Session cache  │                      │  │
│  │  │ • Full-text FTS  │  │ • Rate limiting  │                      │  │
│  │  │ • Aggregations   │  │ • Pub/sub        │                      │  │
│  │  └──────────────────┘  └──────────────────┘                      │  │
│  │                                                                    │  │
│  │  Message Broker:                                                 │  │
│  │  ┌──────────────────────────────────────────────────────┐       │  │
│  │  │ Apache Kafka 3.x + Schema Registry                   │       │  │
│  │  │ • Topics: assets, findings, events, audit-events    │       │  │
│  │  │ • Consumer groups per service                        │       │  │
│  │  │ • 7-day retention                                    │       │  │
│  │  │ • Avro schema validation                             │       │  │
│  │  └──────────────────────────────────────────────────────┘       │  │
│  │                                                                    │  │
│  │  Secrets Management:                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐       │  │
│  │  │ HashiCorp Vault 1.15                                 │       │  │
│  │  │ • Cloud provider credentials (encrypted)             │       │  │
│  │  │ • Shared volume with services                        │       │  │
│  │  │ • Automatic token rotation                           │       │  │
│  │  │ • Audit logging                                      │       │  │
│  │  └──────────────────────────────────────────────────────┘       │  │
│  │                                                                    │  │
│  │  Policy Engine:                                                  │  │
│  │  ┌──────────────────────────────────────────────────────┐       │  │
│  │  │ Open Policy Agent (OPA) 0.60+                         │       │  │
│  │  │ • Rego policy evaluation                              │       │  │
│  │  │ • Hot-reload rules                                   │       │  │
│  │  │ • Compliance framework mappings                      │       │  │
│  │  └──────────────────────────────────────────────────────┘       │  │
│  │                                                                    │  │
│  │  Real-time Communication:                                        │  │
│  │  ┌──────────────────────────────────────────────────────┐       │  │
│  │  │ Soketi (WebSocket Server)                             │       │  │
│  │  │ • Pusher-compatible API                              │       │  │
│  │  │ • Real-time finding updates                          │       │  │
│  │  │ • Incident notifications                             │       │  │
│  │  │ • Max 100 connections per app                        │       │  │
│  │  └──────────────────────────────────────────────────────┘       │  │
│  │                                                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              External Cloud Integrations                         │  │
│  │                                                                    │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                          │  │
│  │  │ AWS  │  │Azure │  │ GCP  │  │ OCI  │                          │  │
│  │  │      │  │      │  │      │  │      │                          │  │
│  │  │ IAM  │  │ AAD  │  │ IAM  │  │ IAM  │                          │  │
│  │  │ EC2  │  │ VMs  │  │ GKE  │  │ OKE  │                          │  │
│  │  │ VPC  │  │ NSG  │  │ GCE  │  │ VCN  │                          │  │
│  │  │ S3   │  │AzSA  │  │ GCS  │  │ OBS  │                          │  │
│  │  │ RDS  │  │ SQL  │  │ SQL  │  │ ADB  │                          │  │
│  │  │ ...  │  │ ...  │  │ ...  │  │ ...  │                          │  │
│  │  └──────┘  └──────┘  └──────┘  └──────┘                          │  │
│  │                                                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Workflows

#### Workflow 1: Cloud Asset Discovery & Ingestion

```
External Cloud (AWS/Azure/GCP/OCI)
         ↓ (API calls)
    Connector Service
         ↓ (normalized resources)
    Kafka (assets.created topic)
         ↓
    Graph Service
         ↓ (create nodes + relationships)
    Neo4j + Elasticsearch
         ↓ (index assets)
    Search & Risk Scoring
         ↓
    API Gateway → Frontend Dashboard
```

**Key Steps:**
1. User adds cloud account to Connector
2. Connector reads from Vault for credentials
3. Connector discovers resources (EC2, S3, IAM, RDS, etc.)
4. Normalizes to Common Data Model (CDM)
5. Publishes to Kafka `assets.created` topic
6. Graph Service consumes and builds Neo4j graph
7. Elasticsearch indexes for full-text search
8. Dashboard displays asset count and trends

---

#### Workflow 2: Security Policy Evaluation & Alert Generation

```
Asset Discovered (Neo4j)
         ↓
    Policy Service (pulls latest Rego rules)
         ↓
    OPA Engine (evaluates rules against asset)
         ↓
    Policy Service publishes to Kafka (finding.raw)
         ↓
    Alert Service (ingestion)
         ↓
    SHA-256 fingerprint deduplication
         ↓
    Graph Service enrichment (attack paths, risk context)
         ↓
    Finding stored in PostgreSQL + Elasticsearch
         ↓
    Notification channels triggered (Slack, Jira, Email)
         ↓
    Frontend updates via WebSocket (Soketi)
```

**Key Steps:**
1. New asset or asset changed event
2. Policy Service pulls Rego rules from disk
3. Evaluates against asset JSON
4. Returns violations as findings
5. Alert Service deduplicates on SHA-256
6. Enriches with graph context
7. Stores in PostgreSQL (multi-tenant RLS)
8. Notifies configured channels
9. Real-time dashboard update

---

#### Workflow 3: AI Copilot Query (RAG Pipeline)

```
User Query ("Which prod workloads are internet-facing?")
         ↓
    Copilot Service
         ↓
    [1] Intent Classification
         ↓ (POSTURE / FINDING / COMPLIANCE / REMEDIATION / THREAT / DRIFT)
    [2] Embedding (text-embedding-3-small)
         ↓
    [3] Multi-Source Retrieval (6 sources):
         ├─ Neo4j (asset graph query)
         ├─ Elasticsearch (finding search)
         ├─ PostgreSQL (compliance / audit)
         ├─ CIEM Service (permission data)
         ├─ CWPP Service (vuln data)
         └─ CDR Service (threat log)
         ↓
    [4] Prompt Construction (with citations)
         ↓
    [5] Claude API Call (via AI Router)
         ↓
    [6] Response Parsing + Audit Log
         ↓
    Streaming response to frontend (SSE)
```

**Key Steps:**
1. User submits natural language query
2. Intent classification determines capability domain
3. Query embedding generated
4. Multi-source context retrieval
5. Citations preserved for transparency
6. Claude generates grounded response
7. Every query logged for audit
8. Response streamed to UI in real-time

---

### Supported Cloud Providers

| Provider | Status | Resource Types |
|----------|--------|-----------------|
| AWS | ✅ Full | EC2, VPC, S3, IAM, RDS, Lambda, EKS, CloudFront, KMS, CloudTrail, SNS, SQS, DynamoDB, ElastiCache, ELB, API Gateway, Secrets Manager, ECR, EFS |
| Microsoft Azure | ✅ Full | VMs, NSGs, VNets, Storage, SQL, Functions, AKS, App Services, Key Vaults, AD, Load Balancers, Cosmos DB, Container Registry, Event Hubs |
| Google Cloud Platform | ✅ Full | Compute, Firewall, VPC, Cloud Storage, Cloud SQL, Cloud Functions, GKE, Cloud Run, IAM, KMS, BigQuery, Pub/Sub, DNS, Artifact Registry |
| Oracle Cloud | ✅ Full | Compute, Security Lists, VCNs, Object Storage, Autonomous DB, Functions, OKE, IAM, Vault, Load Balancers |

---

## Project Structure

### Directory Hierarchy

```
CloudVisor/
├── apps/                              # Frontend and admin applications
│   ├── web/                           # Main Next.js frontend (port 3000)
│   │   ├── src/
│   │   │   ├── app/                   # Next.js App Router pages
│   │   │   │   ├── dashboard/         # Risk score, metrics, trends
│   │   │   │   ├── findings/          # Findings list + detail
│   │   │   │   ├── assets/            # Asset inventory
│   │   │   │   ├── compliance/        # Compliance dashboard
│   │   │   │   ├── cspm/              # Cloud posture
│   │   │   │   ├── cwpp/              # Workload protection
│   │   │   │   ├── cicd/              # CI/CD security
│   │   │   │   ├── cdr/               # Detection & response
│   │   │   │   ├── copilot/           # AI copilot interface
│   │   │   │   └── settings/          # Cloud account management
│   │   │   ├── components/
│   │   │   │   ├── layout/            # Sidebar, Header, AppLayout
│   │   │   │   └── ui/                # Reusable components (Badge, Card, etc.)
│   │   │   └── lib/                   # Utilities
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── next.config.js
│   ├── admin-web/                     # Admin dashboard (future)
│   └── landing/                       # Marketing landing page (future)
│
├── services/                          # Backend microservices (Python 3.12 + FastAPI)
│   ├── api/                           # Public API Gateway (port 8005)
│   │   ├── app/
│   │   │   ├── api/v1/                # Route handlers
│   │   │   ├── core/                  # Config, dependencies, proxying
│   │   │   ├── middleware/            # Security headers, CSRF, rate-limit
│   │   │   └── schemas/               # Pydantic schemas (request/response)
│   │   ├── main.py
│   │   └── requirements.txt
│   │
│   ├── auth/                          # Auth Service (port 8002)
│   │   ├── app/
│   │   │   ├── api/routes/            # Auth, MFA, sessions, admin, org, SSO
│   │   │   ├── core/                  # Config, dependencies, RBAC
│   │   │   ├── models/                # SQLAlchemy ORM models
│   │   │   ├── repositories/          # Data access layer
│   │   │   └── schemas/               # Request/response schemas
│   │   ├── main.py
│   │   └── requirements.txt
│   │
│   ├── connector/                     # Cloud Connector (port 8000)
│   │   ├── app/
│   │   │   ├── api/                   # Account management endpoints
│   │   │   ├── clients/               # AWS/Azure/GCP/OCI clients
│   │   │   ├── consumers/             # Kafka consumers
│   │   │   ├── core/                  # Config, dependencies, CDM
│   │   │   ├── models/                # SQLAlchemy models
│   │   │   ├── producers/             # Kafka producers
│   │   │   ├── repositories/          # DB access
│   │   │   ├── scheduler/             # Sync scheduling
│   │   │   └── services/              # Cloud discovery logic
│   │   ├── main.py
│   │   └── requirements.txt
│   │
│   ├── graph/                         # Graph Service (port 8001)
│   │   ├── app/
│   │   │   ├── api/                   # Graph query endpoints
│   │   │   ├── clients/               # Neo4j, Elasticsearch clients
│   │   │   ├── consumers/             # Kafka consumers (asset events)
│   │   │   ├── core/                  # Config, dependencies
│   │   │   ├── models/                # SQLAlchemy models, graph schemas
│   │   │   ├── producers/             # Kafka producers
│   │   │   ├── repositories/          # Neo4j + ES access
│   │   │   └── services/              # Risk scoring, path analysis
│   │   ├── main.py
│   │   └── requirements.txt
│   │
│   ├── policy/                        # Policy Service (port 8003)
│   │   ├── app/
│   │   │   ├── api/                   # Rule management endpoints
│   │   │   ├── consumers/             # Kafka consumers (asset events)
│   │   │   ├── core/                  # Config, OPA client
│   │   │   ├── models/                # SQLAlchemy models
│   │   │   ├── opa/                   # OPA rule management
│   │   │   ├── producers/             # Kafka producers (findings)
│   │   │   ├── repositories/          # DB access
│   │   │   ├── rules/                 # Rego rule files
│   │   │   └── services/              # Rule evaluation logic
│   │   ├── main.py
│   │   └── requirements.txt
│   │
│   ├── alert/                         # Alert Service (port 8004)
│   │   ├── app/
│   │   │   ├── api/                   # Finding/incident/notification endpoints
│   │   │   ├── consumers/             # Kafka consumers
│   │   │   ├── core/                  # Config, dependencies
│   │   │   ├── models/                # SQLAlchemy models
│   │   │   ├── notifiers/             # Slack, Jira, Email, PagerDuty, Teams
│   │   │   ├── producers/             # Kafka producers
│   │   │   ├── repositories/          # DB access
│   │   │   ├── schemas/               # Request/response schemas
│   │   │   └── services/              # Dedup, enrichment, SLA tracking
│   │   ├── main.py
│   │   └── requirements.txt
│   │
│   ├── copilot/                       # AI Copilot Service (port 8010)
│   │   ├── app/
│   │   │   ├── api/                   # /v1/copilot/query endpoint
│   │   │   ├── core/                  # Config, dependencies
│   │   │   ├── models/                # SQLAlchemy models (query audit log)
│   │   │   ├── repositories/          # DB access
│   │   │   ├── schemas/               # Request/response schemas
│   │   │   ├── services/
│   │   │   │   ├── intent_classifier.py
│   │   │   │   ├── retriever.py       # Multi-source context retrieval
│   │   │   │   ├── prompt_builder.py
│   │   │   │   ├── rag_pipeline.py    # Main orchestration
│   │   │   │   ├── llm_client.py      # Claude API wrapper
│   │   │   │   └── rate_limiter.py
│   │   │   └── alembic/               # DB migrations
│   │   ├── main.py
│   │   └── requirements.txt
│   │
│   ├── security/                      # Security modules (CSPM, CWPP, etc.)
│   │   ├── cspm/                      # Cloud Security Posture (port 8006)
│   │   ├── cwpp/                      # Cloud Workload Protection (future)
│   │   ├── ciem/                      # Cloud Infrastructure Entitlements (future)
│   │   ├── kspm/                      # Kubernetes Security (future)
│   │   └── dspm/                      # Data Security Posture (future)
│   │
│   ├── ai-router/                     # AI Router (port 8015)
│   │   ├── app/
│   │   │   ├── api/                   # /v1/chat/completions, /v1/providers
│   │   │   ├── core/                  # Config
│   │   │   ├── providers/             # OpenAI, OpenRouter, NVIDIA clients
│   │   │   └── services/              # Health check, routing logic
│   │   ├── main.py
│   │   └── requirements.txt
│   │
│   └── keep/                          # AIOps Service (port 8007)
│       ├── app/                       # Keep installation (external)
│       └── config/                    # Keep config integration
│
├── packages/                          # Shared libraries
│   ├── types/
│   │   └── src/                       # TypeScript type definitions
│   ├── utils/
│   │   ├── cloudvisor_utils/
│   │   │   ├── config.py              # Settings management
│   │   │   ├── logging_utils.py       # Structured logging
│   │   │   ├── tracing.py             # OpenTelemetry setup
│   │   │   ├── metrics.py             # Prometheus metrics
│   │   │   └── auth.py                # JWT/API key helpers
│   │   └── pyproject.toml
│   └── kafka-schemas/
│       ├── avro/                      # Avro schemas for Kafka topics
│       └── models/                    # Schema-generated models
│
├── infra/                             # Infrastructure code & configs
│   ├── db/
│   │   ├── postgres/                  # PostgreSQL data directory
│   │   ├── postgres-init/             # Init scripts (schema, migrations)
│   │   ├── neo4j/                     # Neo4j data directory
│   │   └── migrations/                # Alembic migrations
│   ├── nginx/
│   │   └── nginx.conf                 # Reverse proxy config
│   ├── vault/
│   │   ├── config/
│   │   │   └── vault.hcl              # Vault server config
│   │   ├── init/
│   │   │   └── init.py                # Vault initialization script
│   │   └── data/                      # Vault encrypted data
│   └── kafka/
│       ├── topics/                    # Topic definitions
│       └── configs/                   # Kafka broker configs
│
├── scripts/
│   ├── health-check.ps1               # Health check script
│   ├── verify-optimizations.ps1       # Verification script
│   └── startup/                       # Startup scripts
│
├── docker-compose.yml                 # Single-node local development
├── Dockerfile                         # Multi-stage builds for all services
├── .env.example                       # Environment template
├── .gitignore
├── README.md
└── CLAUDE.md                          # AI assistant instructions

```

### Key Files & Their Roles

| File/Directory | Purpose | Owner Service |
|---|---|---|
| `docker-compose.yml` | Orchestrates all 15+ services locally | DevOps |
| `services/*/main.py` | FastAPI app entrypoint | Each service |
| `services/*/app/api/` | REST endpoint definitions | Each service |
| `services/*/app/models/` | SQLAlchemy ORM models | Each service |
| `services/*/app/core/` | Configuration, dependency injection | Each service |
| `services/auth/app/models/auth.py` | Auth domain models (User, Organization, Session, ApiKey) | Auth |
| `services/alert/app/models/alert.py` | Finding, Incident, Suppression models | Alert |
| `services/connector/app/clients/` | AWS/Azure/GCP/OCI SDK wrappers | Connector |
| `services/policy/app/rules/rego/` | Rego policy files (security checks) | Policy |
| `services/copilot/app/services/rag_pipeline.py` | RAG orchestration | Copilot |
| `apps/web/src/app/` | Next.js page components | Frontend |
| `apps/web/src/components/` | Reusable UI components | Frontend |
| `infra/nginx/nginx.conf` | Reverse proxy routing | Infra |
| `.env.example` | Environment template (secrets management) | DevOps |

---

## Architecture & Design

### Design Patterns

#### 1. **Microservices Architecture**

Each service is independently deployable with:
- **Own database** (PostgreSQL) with tenant isolation via RLS
- **Own Redis instance** (different db number)
- **Own Kafka consumer groups**
- **Async communication** via Kafka topics
- **Health check endpoints** for orchestration
- **OpenTelemetry tracing** for observability

**Benefits:**
- Fault isolation (service failure doesn't cascade)
- Independent scaling (CSPM load ≠ Alert load)
- Technology flexibility (future services can use different stacks)
- Team autonomy (parallel development)

#### 2. **Event-Driven Architecture**

Critical events flow through Kafka topics:

```
┌─────────────────────────────────┐
│ Kafka Topics (Event Bus)        │
├─────────────────────────────────┤
│ assets.discovered               │ ← Connector publishes
│ assets.updated                  │
│ finding.raw                     │ ← Policy Service publishes
│ finding.created                 │ ← Alert Service publishes
│ finding.updated                 │
│ finding.resolved                │
│ incident.created                │
│ incident.updated                │
│ notification.sent               │
│ audit.events                    │ ← Multi-service audit trail
│ copilot.query_logged            │ ← Copilot queries for analytics
└─────────────────────────────────┘
```

**Benefits:**
- Loose coupling (services don't call each other directly)
- Audit trail (all events immutable)
- Replay capability (re-process events)
- Scale independently (add Kafka partitions)

#### 3. **Repository Pattern (Data Access Abstraction)**

```
Service Layer
    ↓
Repository Layer (abstract DB queries)
    ↓
SQLAlchemy ORM / Neo4j Driver
    ↓
PostgreSQL / Neo4j / Elasticsearch
```

Each service has `repositories/` directory:
- Hides DB implementation from business logic
- Enables easy mocking for tests
- Centralizes query optimization
- Example: `services/alert/app/repositories/finding_repository.py`

#### 4. **Dependency Injection (FastAPI + Pydantic)**

```python
from fastapi import Depends, FastAPI

app = FastAPI()

async def get_db() -> AsyncSession:
    async with session_factory() as session:
        yield session

@app.get("/findings")
async def list_findings(db: AsyncSession = Depends(get_db)):
    repo = FindingRepository(db)
    return await repo.find_all()
```

**Benefits:**
- Testability (swap DB with mock)
- Centralized config (one place to change DB URL)
- Request-scoped resources (connection pooling)

#### 5. **Multi-Tenancy with PostgreSQL RLS**

Every table has `organization_id`:

```sql
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation ON findings
  USING (organization_id = current_setting('app.current_org_id'))
  WITH CHECK (organization_id = current_setting('app.current_org_id'));
```

**Benefits:**
- Database enforces tenant isolation
- No risk of leaking data across orgs
- Single schema (simpler ops)
- Query parameters become simpler (no WHERE org_id = ...)

#### 6. **Common Data Model (CDM)**

All cloud resources normalized to:

```python
class CommonDataModel:
    resource_id: str                    # "i-1234567890abcdef0" (AWS) or "vm-123" (Azure)
    resource_type: str                  # "aws::ec2::instance" or "azure::vm"
    provider: str                       # "aws", "azure", "gcp", "oci"
    account_id: str                     # Cloud account ID
    region: str                         # "us-east-1" (AWS) or "eastus" (Azure)
    tags: Dict[str, str]                # {"Environment": "prod", "Owner": "team-a"}
    raw: Dict[str, Any]                 # Full cloud API response
    created_at: datetime                # When resource was created in cloud
    discovered_at: datetime             # When CloudVisor discovered it
    risk_score: float                   # 0.0-100.0 (computed)
```

**Benefits:**
- Unified queries across clouds ("find internet-facing resources")
- Consistent compliance checks
- Simplified frontend (no provider-specific UI logic)

#### 7. **RAG (Retrieval-Augmented Generation) Pipeline**

AI Copilot uses structured RAG:

```
User Query
    ↓
[Intent Classification]
    ↓ Determines which capability domain
[Query Embedding]
    ↓ text-embedding-3-small
[Multi-Source Retrieval]
    ├─ Neo4j MATCH queries (asset graph)
    ├─ Elasticsearch full-text search (findings)
    ├─ PostgreSQL compliance queries
    ├─ CIEM permission queries
    ├─ CWPP vulnerability queries
    └─ CDR threat log queries
    ↓
[Prompt Construction]
    ↓ Citations preserved
[Claude API]
    ↓ Streamed to frontend
[Audit Logging]
    ↓ Every query recorded
```

**Benefits:**
- Grounded responses (no hallucinations about your environment)
- Transparent sourcing (citations)
- Auditable (every query logged)

---

### Application Layers

#### Layer 1: Presentation (Frontend)

**Technology:** React 18, TypeScript, Next.js 14, Tailwind CSS

**Responsibilities:**
- Render UI components
- Client-side form validation
- WebSocket real-time updates
- API client calls

**Key Files:**
- `apps/web/src/app/dashboard/` — Dashboard page component
- `apps/web/src/components/ui/Badge.tsx` — Severity badge component
- `apps/web/src/components/layout/Sidebar.tsx` — Navigation

**Data Flow:**
```
User Action (click, scroll)
    ↓
React State Update
    ↓
API Call (fetch/axios)
    ↓
Nginx proxy → API Gateway
    ↓
Response → React state
    ↓
Component re-render
```

#### Layer 2: API Gateway & Routing

**Technology:** Nginx (reverse proxy), FastAPI (Python)

**Responsibilities:**
- Route requests to appropriate service
- Enforce same-origin HttpOnly cookie policy
- Add security headers
- Rate limiting
- CORS handling

**Key Files:**
- `infra/nginx/nginx.conf` — Nginx routing rules
- `services/api/app/middleware/` — API security middleware
- `services/api/main.py` — FastAPI app setup

**Routing Rules (Nginx):**
```
/auth/* → cv-auth:8002 (Auth service)
/v1/* → cv-api:8005 (Public API)
/app/* → cv-soketi:6001 (WebSocket)
/v1/copilot/* → cv-copilot:8010 (Copilot)
/* → cv-web:3000 (Frontend)
```

#### Layer 3: Business Logic (Microservices)

**Technology:** FastAPI, SQLAlchemy, Pydantic

**Services & Responsibilities:**

| Service | Port | Responsibility |
|---------|------|-----------------|
| Connector | 8000 | Cloud asset discovery & sync |
| Graph | 8001 | Asset graph indexing & analysis |
| Auth | 8002 | Multi-tenant RBAC & JWT |
| Policy | 8003 | Rego rule evaluation |
| Alert | 8004 | Finding ingestion & notifications |
| API | 8005 | Public REST/GraphQL gateway |
| CSPM | 8006 | Cloud posture checks |
| Keep (AIOps) | 8007 | Alert correlation & incidents |
| Copilot | 8010 | RAG + Claude |
| AI Router | 8015 | LLM provider gateway |

**Key Files:**
- `services/*/app/services/` — Business logic
- `services/*/app/api/` — HTTP endpoints
- `services/*/app/core/` — Configuration

#### Layer 4: Data Access (Repositories)

**Technology:** SQLAlchemy ORM, Neo4j driver, Elasticsearch Python client

**Responsibilities:**
- Query abstraction
- Connection pooling
- Query optimization
- Transaction management

**Key Files:**
- `services/*/app/repositories/` — Data access layer
- Example: `services/alert/app/repositories/finding_repository.py`

**Pattern:**
```python
class FindingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def find_by_id(self, org_id: str, finding_id: str) -> Finding:
        # Automatically applies RLS via app.current_org_id
        stmt = select(FindingModel).where(FindingModel.id == finding_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()
```

#### Layer 5: Data Store (Databases)

**Technology:** PostgreSQL (primary), Neo4j (graph), Elasticsearch (search), Redis (cache)

**Responsibilities:**
- Persistent data storage
- Indexing
- Query optimization
- Data consistency

**Key Files:**
- `infra/db/postgres-init/` — Schema initialization
- `infra/db/migrations/` — Alembic migrations

---

### Dependency Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                    Dependency Graph                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Frontend (3000)                                                │
│    ↓                                                             │
│  Nginx (8080)                                                   │
│    ├─→ Auth (8002)                                              │
│    ├─→ API Gateway (8005)                                       │
│    ├─→ Copilot (8010)                                           │
│    └─→ WebSocket (6001)                                         │
│                                                                  │
│  API Gateway (8005)                                             │
│    ├─→ Auth (8002)                                              │
│    ├─→ Connector (8000)                                         │
│    ├─→ Graph (8001)                                             │
│    ├─→ Policy (8003)                                            │
│    ├─→ Alert (8004)                                             │
│    ├─→ CSPM (8006)                                              │
│    ├─→ Copilot (8010)                                           │
│    ├─→ Keep (8007)                                              │
│    └─→ AI Router (8015)                                         │
│                                                                  │
│  Connector (8000)                                               │
│    ├─→ PostgreSQL (5432)                                        │
│    ├─→ Redis (6379)                                             │
│    ├─→ Kafka (9092)                                             │
│    ├─→ Vault (8200)                                             │
│    └─→ External Clouds (AWS, Azure, GCP, OCI APIs)             │
│                                                                  │
│  Graph (8001)                                                   │
│    ├─→ PostgreSQL (5432)                                        │
│    ├─→ Redis (6379)                                             │
│    ├─→ Kafka (9092)                                             │
│    ├─→ Neo4j (7687)                                             │
│    └─→ Elasticsearch (9200)                                     │
│                                                                  │
│  Auth (8002)                                                    │
│    ├─→ PostgreSQL (5432)                                        │
│    ├─→ Redis (6379)                                             │
│    └─→ Kafka (9092)                                             │
│                                                                  │
│  Policy (8003)                                                  │
│    ├─→ PostgreSQL (5432)                                        │
│    ├─→ Redis (6379)                                             │
│    ├─→ Kafka (9092)                                             │
│    └─→ OPA (8181)                                               │
│                                                                  │
│  Alert (8004)                                                   │
│    ├─→ PostgreSQL (5432)                                        │
│    ├─→ Redis (6379)                                             │
│    ├─→ Kafka (9092)                                             │
│    ├─→ Elasticsearch (9200)                                     │
│    ├─→ External: Slack, Jira, Email, PagerDuty, Teams         │
│    └─→ WebSocket (6001)                                         │
│                                                                  │
│  CSPM (8006)                                                    │
│    ├─→ PostgreSQL (5432)                                        │
│    ├─→ Redis (6379)                                             │
│    ├─→ Kafka (9092)                                             │
│    ├─→ Policy (8003)                                            │
│    └─→ Alert (8004)                                             │
│                                                                  │
│  Copilot (8010)                                                 │
│    ├─→ PostgreSQL (5432)                                        │
│    ├─→ Redis (6379)                                             │
│    ├─→ Kafka (9092)                                             │
│    ├─→ Elasticsearch (9200)                                     │
│    ├─→ Graph (8001)                                             │
│    ├─→ Policy (8003)                                            │
│    ├─→ Claude API (anthropic.com)                               │
│    └─→ AI Router (8015)                                         │
│                                                                  │
│  Keep (8007)                                                    │
│    ├─→ PostgreSQL (5432)                                        │
│    ├─→ Redis (6379)                                             │
│    ├─→ Kafka (9092)                                             │
│    ├─→ WebSocket (6001)                                         │
│    └─→ AI Router (8015)                                         │
│                                                                  │
│  AI Router (8015)                                               │
│    ├─→ Redis (6379)                                             │
│    ├─→ OpenAI (openai.com)                                      │
│    ├─→ OpenRouter (openrouter.ai)                               │
│    └─→ NVIDIA NIM (integrate.api.nvidia.com)                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### Data Flow (End-to-End)

#### Scenario: User discovers a security finding

```
Step 1: Asset Creation
────────────────────
User adds AWS account to Connector
  ↓
Connector reads credentials from Vault
  ↓
Connector calls AWS API (DescribeInstances, DescribeSecurityGroups, etc.)
  ↓
Connector normalizes to CDM
  ↓
Connector publishes to Kafka topic: "assets.discovered"
  ↓ [Event ID: asset_evt_123]

Step 2: Graph Indexing
──────────────────────
Graph service consumes from "assets.discovered"
  ↓
Graph service creates Neo4j node: (:EC2Instance { resource_id: "i-123", risk_score: 0 })
  ↓
Graph service creates relationships:
  - EC2Instance --[:IN_ACCOUNT]--> AWSAccount
  - SecurityGroup --[:ATTACHED_TO]--> EC2Instance
  - SecurityGroup --[:ALLOWS_INBOUND_FROM]--> CIDR {0.0.0.0/0}  ← RISK!
  ↓
Graph service indexes in Elasticsearch
  ↓
Graph service publishes to Kafka topic: "graph.updated"
  ↓ [Event ID: graph_evt_123]

Step 3: Policy Evaluation
─────────────────────────
Policy service consumes from "assets.discovered"
  ↓
Policy service pulls Rego rules from /app/rules/rego/
  ↓
Policy service packages EC2 instance as JSON:
  {
    "resource_type": "aws::ec2::instance",
    "provider": "aws",
    "region": "us-east-1",
    "raw": {
      "InstanceId": "i-123",
      "SecurityGroups": [{"GroupId": "sg-456", "IpPermissions": [...]}],
      ...
    }
  }
  ↓
Policy service calls OPA: POST /v1/compile
  ↓
OPA evaluates Rego rules (cspm/aws/ec2/open-security-group)
  ↓
OPA returns violations:
  {
    "findings": [
      {
        "rule_id": "ec2-open-security-group",
        "severity": "HIGH",
        "message": "Security group allows inbound from 0.0.0.0/0"
      }
    ]
  }
  ↓
Policy service publishes to Kafka topic: "finding.raw"
  ↓ [Event ID: finding_raw_123]

Step 4: Finding Ingestion & Deduplication
───────────────────────────────────────────
Alert service consumes from "finding.raw"
  ↓
Alert service computes SHA-256 fingerprint:
  fingerprint = sha256("ec2-open-security-group:i-123:us-east-1")
  ↓
Alert service queries PostgreSQL:
  SELECT * FROM findings WHERE fingerprint = ?
  ↓
If fingerprint exists:
  → Update last_seen_at, increment regression_count
  → Publish "finding.seen_again" event
  ↓
If fingerprint is new:
  → Create new finding record
  → Publish "finding.created" event
  → Notify configured channels (Slack, Jira, Email)
  ↓
Alert service calls Graph service for enrichment:
  POST /internal/finding/{id}/enrich
  ↓
Graph service queries Neo4j:
  MATCH (finding_resource)-[:IN_ACCOUNT]->(account)
  MATCH (resource)-[*1..5]->(sensitive_db:RDSInstance)
  RETURN paths
  ↓
Graph service returns attack paths + risk context
  ↓
Alert service stores finding:
  {
    "id": "finding_789",
    "rule_id": "ec2-open-security-group",
    "resource_id": "i-123",
    "severity": "HIGH",
    "status": "open",
    "fingerprint": "...",
    "context": {
      "attack_paths": [...],
      "risk_score": 78.5
    }
  }
  ↓ [Stored in PostgreSQL + Elasticsearch]

Step 5: Notification
────────────────────
Alert service evaluates notification channels:
  ├─ Slack: severity filter = [HIGH, CRITICAL] → YES
  ├─ Jira: module filter = [cspm] → YES
  ├─ Email: digest only → NO (realtime for HIGH/CRITICAL)
  └─ PagerDuty: severity = CRITICAL only → NO
  ↓
Alert service sends notifications:
  - POST to Slack webhook
  - POST to Jira API
  - Add to email queue
  ↓
Alert service publishes "notification.sent" events
  ↓ [Audit trail]

Step 6: Real-Time UI Update
────────────────────────────
Soketi (WebSocket) receives:
  pusher.trigger('cloudvisor', 'finding.created', {...})
  ↓
Frontend subscribed to 'finding.created' event
  ↓
React state updates
  ↓
Dashboard metrics updated:
  - Finding count: 42 → 43
  - Severity breakdown: HIGH: 12 → 13
  - Risk score: 72.3 → 73.1
  ↓
Real-time list updated
  ↓
User sees finding in dashboard instantly

Step 7: User Query via Copilot
───────────────────────────────
User types: "Why is this finding critical?"
  ↓
Copilot service receives query
  ↓
[1] Intent Classification: FINDING
  ↓
[2] Embedding: text-embedding-3-small
  ↓
[3] Retrieval (6 sources):
  - Neo4j: MATCH (res {resource_id: "i-123"}) RETURN {...}
  - Elasticsearch: finding search (HIGH + "open security")
  - PostgreSQL: CIS benchmark mapping
  - Graph context: attack paths
  ↓
[4] Prompt construction:
  "User asked about finding [finding_789]. Here's the context:
   - Resource: EC2 instance i-123 in account prod-acct
   - Violation: Security group sg-456 allows 0.0.0.0/0 on port 22 (SSH)
   - CIS Control: CIS AWS 5.2
   - Attack Path: This instance connects to RDS database with PII
   - Recommendation: Restrict to authorized IPs only
   
   Answer the user's question based on this context."
  ↓
[5] Claude API call (via AI Router)
  ↓
[6] Response:
  "This finding is critical because:
   1. Your EC2 instance allows SSH from the internet
   2. Attack paths show it can reach your database with PII
   3. CIS benchmark requires restricting this
   
   Remediation: Update security group to allow only [list IPs]"
  ↓
Streaming response to frontend (SSE)
  ↓
Copilot logs query to audit_log table
  ↓
User reads explanation + recommended remediation

Step 8: User Remediation
────────────────────────
User applies remediation via cloud console or API
  ↓
Connector service syncs (scheduled or webhook)
  ↓
Connector detects changed security group
  ↓
Connector publishes "assets.updated" event
  ↓
Graph service updates Neo4j relationship
  ↓
Policy service re-evaluates → PASS
  ↓
Alert service marks finding as "resolved"
  ↓
Alert service publishes "finding.resolved" event
  ↓
Dashboard shows: finding status = RESOLVED ✅
  ↓
SLA tracking recorded: "Resolved in 2 hours"
```

---

## Frontend Documentation

### Technology Stack

- **Framework:** Next.js 14 (React 18, TypeScript)
- **UI Library:** Custom + Tailwind CSS 3.x
- **State Management:** React hooks + Context API
- **HTTP Client:** Fetch API (built-in)
- **WebSocket:** Pusher (Soketi compatible)
- **Charts:** Custom SVG (RiskScore gauge, Compliance donuts)
- **Forms:** React + HTML5 validation
- **Styling:** Tailwind CSS with custom color system

### Project Structure

```
apps/web/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── page.tsx            # Root redirect to /dashboard
│   │   ├── layout.tsx          # Root layout (Sidebar + Header)
│   │   ├── globals.css         # Global styles + color system
│   │   │
│   │   ├── dashboard/
│   │   │   ├── page.tsx        # Dashboard main page
│   │   │   ├── layout.tsx      # Dashboard-specific layout
│   │   │   └── components/     # Dashboard-specific components
│   │   │
│   │   ├── findings/
│   │   │   ├── page.tsx        # Findings list
│   │   │   ├── [id]/page.tsx   # Finding detail
│   │   │   └── components/
│   │   │
│   │   ├── assets/
│   │   │   ├── page.tsx        # Asset inventory
│   │   │   ├── [id]/page.tsx   # Asset detail
│   │   │
│   │   ├── compliance/
│   │   │   ├── page.tsx        # Compliance dashboard
│   │   │   ├── [framework]/page.tsx
│   │   │
│   │   ├── cspm/
│   │   │   └── page.tsx        # Cloud posture
│   │   │
│   │   ├── cwpp/
│   │   │   └── page.tsx        # Workload protection
│   │   │
│   │   ├── cicd/
│   │   │   └── page.tsx        # CI/CD security
│   │   │
│   │   ├── cdr/
│   │   │   └── page.tsx        # Detection & response
│   │   │
│   │   ├── copilot/
│   │   │   └── page.tsx        # AI Copilot interface
│   │   │
│   │   └── settings/
│   │       └── page.tsx        # Account management
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx     # Left navigation (240px)
│   │   │   ├── Header.tsx      # Top header (search bar)
│   │   │   └── AppLayout.tsx   # Layout wrapper
│   │   │
│   │   └── ui/
│   │       ├── Button.tsx
│   │       ├── Card.tsx
│   │       ├── Badge/
│   │       │   ├── SeverityBadge.tsx  # CRITICAL/HIGH/MEDIUM/LOW/INFO
│   │       │   ├── StatusBadge.tsx    # open/resolved/accepted/suppressed
│   │       │   ├── ProviderBadge.tsx  # AWS/Azure/GCP/OCI
│   │       │   └── RiskScore.tsx      # Circular gauge
│   │       ├── Table/
│   │       │   ├── DataTable.tsx
│   │       │   ├── TableHeader.tsx
│   │       │   └── TableRow.tsx
│   │       ├── Form/
│   │       │   ├── Input.tsx
│   │       │   ├── Select.tsx
│   │       │   ├── Checkbox.tsx
│   │       │   └── TextArea.tsx
│   │       └── Charts/
│   │           ├── DonutChart.tsx
│   │           ├── BarChart.tsx
│   │           └── LineChart.tsx
│   │
│   └── lib/
│       ├── utils.ts            # Utility functions
│       ├── api.ts              # API client wrapper
│       ├── hooks/
│       │   ├── useFindings.ts
│       │   ├── useAssets.ts
│       │   └── useWebSocket.ts
│       └── constants/
│           ├── severity.ts
│           └── providers.ts
│
├── public/
│   ├── icons/
│   │   ├── aws.svg
│   │   ├── azure.svg
│   │   ├── gcp.svg
│   │   └── oci.svg
│   └── logos/
│       └── cloudvisor.svg
│
├── .env.development
├── .env.example
├── package.json
├── next.config.js
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
└── Dockerfile
```

### Page Components & Functionality

#### 1. Dashboard (`apps/web/src/app/dashboard/page.tsx`)

**Purpose:** Executive overview of security posture

**Key Sections:**
- **Hero Element:** RiskScore gauge (0-100, animated)
  ```
  Orca-style circular gauge:
  - Outer ring: Red (critical) → Orange (high) → Yellow (medium) → Green (low)
  - Center: Large font score (e.g., "72.3")
  - Animation: Needle rotates to current score
  ```

- **Metrics Cards:** 5 KPIs with trends
  ```
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │ Findings    │  │ Assets      │  │ Compliance  │
  │ 42          │  │ 1,234       │  │ 73%         │
  │ ↑ 12%       │  │ ↑ 5%        │  │ ↓ 2%        │
  └─────────────┘  └─────────────┘  └─────────────┘
  ```

- **Compliance Frameworks:** Stacked bars
  ```
  CIS AWS        ████████░░ 80%
  SOC 2          ██████░░░░ 60%
  PCI-DSS        ███████░░░ 70%
  HIPAA          ██████░░░░ 60%
  ```

- **Top 5 Riskiest Assets:** Table with risk scores
- **Recent Activity Feed:** Last 10 events with timestamps

#### 2. Findings (`apps/web/src/app/findings/page.tsx`)

**Purpose:** Browse and manage security findings

**Features:**
- **Severity Tabs:** All | CRITICAL | HIGH | MEDIUM | LOW
- **Orca-Style Cards:**
  ```
  ┌────────────────────────────────────┐
  │ ████ S3 bucket is publicly readable │ ← 4px left red border
  │                                     │
  │ Severity: CRITICAL                 │
  │ Resource: my-bucket (AWS S3)        │
  │ Status: Open  Age: 3h               │
  │ [Details] [Remediate] [Suppress]   │
  └────────────────────────────────────┘
  ```

- **Filters:**
  - Provider: AWS, Azure, GCP, OCI
  - Status: Open, Resolved, Accepted, Suppressed
  - Module: CSPM, CWPP, CDR, CI/CD
  - Search: Free-text (title, description)

- **Pagination:** Cursor-based (opaque tokens)

#### 3. Assets (`apps/web/src/app/assets/page.tsx`)

**Purpose:** Cloud resource inventory

**Views:**
- **Table View:** Sortable, filterable
  ```
  | Resource ID | Type | Provider | Region | Status | Risk |
  |─────────────|------|----------|--------|--------|------|
  | i-123       | EC2  | AWS      | us-e1  | Ok     | 45   |
  | sg-456      | NSG  | Azure    | eastus | ⚠️     | 72   |
  ```

- **Graph View:** Neo4j-based visualization (future)

- **Provider Breakdown:** Summary cards
  ```
  AWS         Azure       GCP         OCI
  523 assets  127 assets  89 assets   45 assets
  ```

#### 4. Compliance (`apps/web/src/app/compliance/page.tsx`)

**Purpose:** Compliance posture dashboard

**Features:**
- **Framework Tabs:** CIS | SOC2 | PCI-DSS | HIPAA | ISO27001
- **Donut Charts:** (Prisma-style)
  ```
        ╭─────────╮
        │  ███ 45%│ ← Passing
        │  ░░░ 35%│ ← Failing
        │  ▒▒▒ 20%│ ← Not applicable
        ╰─────────╯
  
  "12 / 26 Controls Passing"
  ```

- **Control Domains:** Grouped by category
  - Identity & Access Management
  - Data Protection
  - Logging & Monitoring
  - Network Security
  - etc.

- **Drill-Down:** Click control → see failing resources

#### 5. CSPM (`apps/web/src/app/cspm/page.tsx`)

**Purpose:** Cloud Security Posture Management

**Features:**
- **Provider Cards:** Posture per cloud
  ```
  AWS         Azure       GCP
  82% Pass    71% Pass    78% Pass
  ```

- **Category Breakdown:**
  - Identity & Access
  - Network Security
  - Data Protection
  - Compute Security
  - etc.

- **Risk Heatmap:** Severity × Count

#### 6. Copilot (`apps/web/src/app/copilot/page.tsx`)

**Purpose:** AI-powered security Q&A

**Features:**
- **Conversational Interface:**
  ```
  User: "Which prod workloads are internet-facing?"
         ↑ Input field
  
  Copilot: "I found 3 production workloads exposed to the internet:
           1. Production-Web-Server (EC2, i-123)
           2. API-Gateway (ALB, arn:...)
           3. Database-Replica (RDS, prod-db-r)
           
           [Details] [Remediate]"
  ```

- **Suggested Queries:**
  ```
  • "Show me critical findings"
  • "Which resources have CVEs?"
  • "What's my compliance status?"
  ```

- **Streaming Responses:** Real-time text streaming (SSE)

- **Citation Links:** "[source: finding_789]" clickable

---

### Design System

#### Color Palette

```css
/* Severity Colors (NON-NEGOTIABLE) */
--severity-critical: #dc2626  /* Red */
--severity-high: #ea580c      /* Orange */
--severity-medium: #d97706    /* Amber */
--severity-low: #2563eb       /* Blue */
--severity-info: #6b7280      /* Gray */

/* Cloud Provider Colors */
--provider-aws: #f97316       /* AWS Orange */
--provider-azure: #0078d4     /* Azure Blue */
--provider-gcp: #1a73e8       /* GCP Blue */
--provider-oci: #c74634       /* OCI Red */

/* Status Colors */
--status-open: #dc2626        /* Red */
--status-in-progress: #f59e0b /* Amber */
--status-resolved: #16a34a    /* Green */
--status-accepted: #8b5cf6    /* Purple */
--status-suppressed: #9ca3af  /* Gray */

/* UI Colors */
--background: #ffffff
--surface: #f9fafb
--border: #e5e7eb
--text-primary: #111827
--text-secondary: #6b7280

/* Dark Sidebar */
--sidebar-bg: #1a2332        /* Dark navy */
--sidebar-text: #ffffff
--sidebar-border: #3f4f63
--sidebar-active: #3b82f6    /* Blue left border */
```

#### Typography

```
Font Family:
- Sans: Geist, -apple-system, system-ui, sans-serif
- Mono: Geist Mono, Fira Code, monospace

Sizes:
- 10px (text-xs) - Badge text
- 12px (text-sm) - Body, table text
- 14px (text-base) - Normal text, headings
- 16px (text-lg) - Section headings
- 18px (text-2xl) - Page titles
- 32px (text-4xl) - Metric numbers

Weights:
- 400 (normal) - Body text
- 500 (medium) - Labels
- 600 (semibold) - Headings
- 700 (bold) - Metrics, emphasis
```

#### Spacing (8px Grid)

```
4px   - Tightest (badge padding)
8px   - Small (component padding)
12px  - Normal (form gap)
16px  - Card padding
24px  - Section separation
32px  - Major breaks
48px  - Page margins
```

---

### API Integration

#### Authentication

**Two methods supported:**

1. **JWT Token (Client-side storage)**
   ```javascript
   // GET /auth/login
   POST /auth/login
   {
     "email": "user@example.com",
     "password": "..."
   }
   
   Response:
   {
     "access_token": "eyJhbGc...",
     "refresh_token": "...",
     "expires_in": 900
   }
   
   // Stored in localStorage
   localStorage.setItem('access_token', token)
   ```

2. **HttpOnly Cookies (Default)**
   ```
   POST /auth/login → Set-Cookie: session=...
   
   Browser automatically sends cookies with each request
   No need for manual header injection
   ```

#### API Client Wrapper

```typescript
// lib/api.ts
export const apiClient = {
  async get<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`/v1${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      credentials: 'include', // Send cookies
    });
    return response.json();
  },

  async post<T>(path: string, body?: object, options?: RequestInit): Promise<T> {
    return this.get<T>(path, {
      ...options,
      method: 'POST',
      body: JSON.stringify(body),
    });
  },
};

// Usage:
const findings = await apiClient.get<Finding[]>('/findings');
```

#### Real-Time Updates (WebSocket)

```typescript
// lib/hooks/useWebSocket.ts
export function useWebSocket() {
  const [findings, setFindings] = useState<Finding[]>([]);

  useEffect(() => {
    const pusher = new Pusher('cloudvisor-key', {
      cluster: 'localhost', // or 'mt1' for production
      wsHost: 'localhost',
      wsPort: 6001,
      forceTLS: false, // Dev only
    });

    const channel = pusher.subscribe('cloudvisor');
    
    // Listen for finding.created event
    channel.bind('finding.created', (data: Finding) => {
      setFindings(prev => [data, ...prev]);
    });

    return () => pusher.unsubscribe('cloudvisor');
  }, []);

  return findings;
}
```

---

## Backend Documentation

### Service Architecture Overview

Each backend service follows a consistent structure:

```
services/[service-name]/
├── main.py
├── requirements.txt
├── Dockerfile
├── .env
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── routes/            # HTTP endpoint handlers
│   │   │   ├── __init__.py
│   │   │   └── [route].py
│   │   └── v1/                # Versioned API
│   │
│   ├── core/
│   │   ├── config.py          # Settings/env vars
│   │   ├── dependencies.py    # Dependency injection
│   │   └── exceptions.py      # Custom exceptions
│   │
│   ├── models/
│   │   └── [domain].py        # SQLAlchemy ORM models
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── [entity]_repository.py
│   │
│   ├── schemas/
│   │   ├── request.py         # Pydantic request models
│   │   └── response.py        # Pydantic response models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── [domain]_service.py
│   │
│   ├── consumers/             # Kafka consumers (if applicable)
│   │   └── [topic]_consumer.py
│   │
│   └── producers/             # Kafka producers (if applicable)
│       └── [topic]_producer.py
│
└── tests/
    ├── unit/
    ├── integration/
    └── conftest.py
```

### Authentication Service (Port 8002)

**Purpose:** Multi-tenant RBAC, JWT, MFA, SSO

**Key Endpoints:**

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/register` | ❌ | Register new org + user |
| POST | `/auth/login` | ❌ | Login (email/password) |
| POST | `/auth/logout` | ✅ JWT | Logout + invalidate session |
| GET | `/auth/me` | ✅ JWT | Get current user |
| POST | `/auth/refresh` | ✅ Refresh | Get new access token |
| POST | `/auth/mfa/enroll` | ✅ JWT | Enable 2FA |
| POST | `/auth/mfa/verify` | ✅ JWT | Verify 2FA code |
| GET | `/auth/sessions` | ✅ JWT | List active sessions |
| GET | `/auth/api-keys` | ✅ JWT | List API keys |
| POST | `/auth/api-keys` | ✅ JWT | Create API key |
| DELETE | `/auth/api-keys/{id}` | ✅ JWT | Delete API key |
| POST | `/admin/auth/login` | ❌ | Admin login |
| GET | `/internal/auth/validate` | ✅ JWT | Validate JWT (internal) |
| GET | `/internal/orgs` | ✅ JWT | List orgs (admin) |
| POST | `/internal/orgs` | ✅ JWT | Create org (admin) |

**Authentication Flows:**

1. **Password-based:**
   ```
   POST /auth/login
   {
     "email": "user@org.com",
     "password": "correct-horse-battery-staple"
   }
   
   Response (200):
   {
     "access_token": "eyJhbGc...",
     "refresh_token": "eyJhbGc...",
     "token_type": "Bearer",
     "expires_in": 900
   }
   ```

2. **JWT Validation (by API Gateway):**
   ```
   Request: GET /v1/findings
   Header: Authorization: Bearer eyJhbGc...
   
   API Gateway → Auth Service
   POST /internal/auth/validate
   {"token": "eyJhbGc..."}
   
   Response:
   {
     "valid": true,
     "user_id": "user_123",
     "org_id": "org_456",
     "scopes": ["findings:read", "findings:write"]
   }
   ```

3. **MFA (TOTP):**
   ```
   POST /auth/mfa/enroll
   Response: {"secret": "...", "qr_code": "..."}
   
   Client scans QR in authenticator app
   
   POST /auth/mfa/verify
   {"code": "123456"}
   
   Response: {"enrolled": true, "backup_codes": [...]}
   ```

**RBAC Model:**

```
Organization (tenant)
  ├─ Users (multi-user)
  │  ├─ admin (can manage org, users, settings)
  │  ├─ security_lead (can manage policies, view all findings)
  │  ├─ engineer (can view findings in assigned accounts only)
  │  └─ viewer (read-only access)
  │
  └─ Roles (custom per org in enterprise tier)
     ├─ Name: "Security-Lead"
     ├─ Permissions: ["findings:read", "policies:write"]
     └─ Scope: {accounts: ["prod", "staging"]}
```

**Database Models:**

```python
class OrganizationModel:
    id: UUID
    name: str
    plan: str  # free, pro, enterprise
    billing_email: str

class UserModel:
    id: UUID
    org_id: UUID (FK)
    email: str
    password_hash: str (bcrypt)
    mfa_enabled: bool
    mfa_secret: str (encrypted in Vault)
    provider: str  # local, google, github, saml
    provider_id: str  # Prevents cross-provider collisions

class SessionModel:
    id: UUID
    user_id: UUID (FK)
    org_id: UUID (FK, denormalized for RLS)
    refresh_token_hash: str
    device_info: str
    ip_address: str
    last_active_at: datetime
    expires_at: datetime

class ApiKeyModel:
    id: UUID
    user_id: UUID (FK)
    key_hash: str (bcrypt)
    scopes: List[str]  # fine-grained permissions
    last_used_at: datetime
    expires_at: datetime

class AuditLogModel:
    id: int (autoincrement)
    org_id: UUID
    user_id: UUID (nullable)
    event_type: str  # login, logout, mfa_enrolled, api_key_created
    event_data: dict
    ip_address: str
    success: bool
    timestamp: datetime
```

---

### Connector Service (Port 8000)

**Purpose:** Cloud asset discovery & sync

**Key Endpoints:**

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/internal/accounts` | ✅ | Register cloud account |
| GET | `/internal/accounts` | ✅ | List accounts |
| GET | `/internal/accounts/{id}` | ✅ | Get account details |
| PATCH | `/internal/accounts/{id}` | ✅ | Update config |
| DELETE | `/internal/accounts/{id}` | ✅ | Deregister account |
| POST | `/internal/accounts/{id}/sync` | ✅ | Trigger manual sync |
| GET | `/internal/accounts/{id}/health` | ✅ | Check sync health |
| GET | `/internal/onboarding/{provider}/instructions` | ✅ | Get setup guide |

**Cloud Discovery Process:**

```python
# Pseudo-code
class AWSConnector:
    def discover_assets(self, credentials):
        # 1. Initialize boto3 client
        ec2 = boto3.client('ec2', credentials=credentials)
        
        # 2. List resources
        instances = ec2.describe_instances()
        
        # 3. Normalize to CDM
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                resource = CommonDataModel(
                    resource_id=instance['InstanceId'],
                    resource_type='aws::ec2::instance',
                    provider='aws',
                    region=instance['Placement']['AvailabilityZone'].strip('a'),
                    tags={t['Key']: t['Value'] for t in instance.get('Tags', [])},
                    raw=instance  # Full cloud API response
                )
                # 4. Publish to Kafka
                await self.producer.send('assets.discovered', resource.dict())
```

**Supported Resources:**

**AWS:**
- EC2, VPC, Subnets, Security Groups
- IAM (Users, Roles, Policies, Assume roles)
- RDS, DynamoDB, ElastiCache
- S3, EBS, EFS
- Lambda, EKS, CloudFront, CloudTrail
- KMS, Secrets Manager, API Gateway

**Azure:**
- Virtual Machines, NSGs, Subnets
- Storage Accounts, SQL Servers
- App Services, Key Vaults
- Azure AD (Users, Groups, Role Assignments)
- AKS, Azure Functions, Cosmos DB
- Event Hubs, Container Registry

**GCP:**
- Compute Instances, Firewall Rules
- VPC Networks, Cloud Storage
- Cloud SQL, Cloud Functions, GKE
- IAM Service Accounts, KMS Keys
- BigQuery, Pub/Sub, Cloud Run

**OCI:**
- Compute Instances, Security Lists
- VCNs, Object Storage
- Autonomous Databases, Functions, OKE
- IAM Users/Groups/Policies, Vault Secrets

**Credential Management (Vault):**

```
User adds AWS account:
  ├─ Role ARN: arn:aws:iam::123456789:role/CloudVisor
  ├─ External ID: random UUID
  └─ (or) Access Key / Secret Key

Connector stores in Vault:
  ├─ Mount: cloudvisor/credentials/aws-prod
  ├─ Data:
  │  ├─ access_key: "AKIA..."
  │  ├─ secret_key: "..." (encrypted at rest)
  │  ├─ assume_role_arn: "arn:aws:iam::..."
  │  └─ external_id: "..."
  └─ TTL: 30 days (auto-rotate)

Connector retrieves for sync:
  1. Read /vault/data/vault_token (shared volume)
  2. POST /v1/auth/kubernetes (Vault service auth)
  3. GET /v1/cloudvisor/credentials/aws-prod
  4. Use credentials to call AWS APIs
```

---

### Graph Service (Port 8001)

**Purpose:** Asset relationship graph & risk scoring

**Key Endpoints:**

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/internal/graph/assets` | ✅ | Query Neo4j (Cypher) |
| GET | `/internal/graph/paths` | ✅ | Find attack paths |
| POST | `/internal/graph/assets/{id}/risk` | ✅ | Compute risk score |
| POST | `/internal/finding/{id}/enrich` | ✅ | Enrich with context |
| GET | `/internal/search` | ✅ | Full-text search (ES) |

**Neo4j Graph Schema:**

```cypher
// Node types
(:AWS:Account {account_id, account_name, region})
(:AWS:EC2Instance {resource_id, instance_type, state, ...})
(:AWS:SecurityGroup {resource_id, rules, ...})
(:AWS:S3Bucket {resource_id, public_access, ...})
(:AWS:IAMRole {resource_id, policies, ...})
(:AWS:RDSInstance {resource_id, public_facing, ...})
(:Azure:VirtualMachine {resource_id, ...})
(:Azure:StorageAccount {resource_id, ...})
// ... similar for GCP, OCI

// Relationships
(:EC2Instance)-[:ATTACHED_TO]->(:SecurityGroup)
(:SecurityGroup)-[:ALLOWS_INBOUND_FROM]->(:CIDR {value: "0.0.0.0/0"})
(:EC2Instance)-[:IN_ACCOUNT]->(:Account)
(:EC2Instance)-[:IN_REGION]->(:Region)
(:IAMRole)-[:HAS_POLICY]->(:IAMPolicy)
(:EC2Instance)-[:CONNECTED_TO]->(:RDSInstance)
(:S3Bucket)-[:REPLICATED_TO]->(:S3Bucket)

// Properties
[relationship] {
  created_at: datetime,
  updated_at: datetime,
  risk_level: "high" | "medium" | "low"
}
```

**Risk Scoring Algorithm:**

```
Risk Score = (Exposure × Criticality × Likelihood) / 100

Exposure (0-100):
  - Internet-facing: +40
  - Public cloud: +20
  - Private subnet: +10
  - Requires VPN: +5

Criticality (0-100):
  - Database with PII: +50
  - Authentication service: +30
  - Load balancer: +20
  - Logging service: +10
  - Dev environment: +5

Likelihood (0-100):
  - Unpatched CVE: +30
  - Open security group: +25
  - Default credentials: +20
  - Weak IAM: +15
  - Misconfiguration: +10

Final Score: 0-100 (aggregated to Organization level)
```

**Attack Path Analysis:**

```cypher
// Find internet-exposed resources connected to databases
MATCH path = (i:InternetGateway)-[*1..6]->(db:RDSInstance)
WHERE db.contains_pii = true
RETURN path, length(path) AS hops
ORDER BY hops ASC LIMIT 10

// Example result:
// IGW → Route Table → Subnet → EC2 → SecurityGroup Rule → RDS
// "5 hops to reach database with PII"
```

---

### Policy Service (Port 8003)

**Purpose:** OPA/Rego policy evaluation

**Key Endpoints:**

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/internal/rules` | ✅ | List all rules |
| POST | `/internal/rules` | ✅ | Deploy new rule |
| POST | `/internal/evaluate` | ✅ | Evaluate asset against rules |
| GET | `/internal/compliance/mappings` | ✅ | Compliance framework mappings |

**Rego Rule Structure:**

```rego
# METADATA
# title: "S3 bucket must not have public access"
# description: "S3 buckets containing sensitive data should never be publicly readable"
# severity: CRITICAL
# category: cspm
# provider: aws
# resource_type: aws::s3::bucket
# compliance_mapping: ["CIS AWS 2.1.5", "PCI-DSS 2.2"]
# remediation: |
#   1. Go to S3 console
#   2. Select bucket
#   3. Click "Block Public Access"
#   4. Enable "Block all public access"
# version: "1.0.0"
# tags: [storage, access-control, data-protection]

package cspm.aws.s3

import future.keywords

# DENY — returns violations
deny[finding] {
    input.resource_type == "aws::s3::bucket"
    not input.raw.PublicAccessBlockConfiguration.BlockPublicAcls
    finding := {
        "rule_id": "s3-public-access-block",
        "severity": "CRITICAL",
        "message": "S3 bucket does not have block public access enabled",
        "remediation_steps": [
            "Enable BlockPublicAcls in PublicAccessBlockConfiguration"
        ]
    }
}

# Multiple violations per resource
deny[finding] {
    input.resource_type == "aws::s3::bucket"
    input.raw.Versioning.Status != "Enabled"
    finding := {
        "rule_id": "s3-versioning-enabled",
        "severity": "MEDIUM",
        "message": "S3 bucket versioning is not enabled"
    }
}

# Conditional deny (only applies to production)
deny[finding] {
    input.resource_type == "aws::s3::bucket"
    input.tags.Environment == "prod"
    not input.raw.ServerSideEncryptionConfiguration
    finding := {
        "rule_id": "s3-encryption-at-rest",
        "severity": "HIGH"
    }
}
```

**Policy Evaluation Flow:**

```
Asset: EC2 instance (i-123)
  ↓
Normalize to JSON:
  {
    "resource_id": "i-123",
    "resource_type": "aws::ec2::instance",
    "provider": "aws",
    "region": "us-east-1",
    "tags": {"Environment": "prod"},
    "raw": {
      "InstanceId": "i-123",
      "State": {"Name": "running"},
      "SecurityGroups": [{"GroupId": "sg-456"}],
      "IamInstanceProfile": {"Arn": "..."},
      ...
    }
  }
  ↓
Call OPA:
  POST /v1/compile
  {"query": "package cspm.aws.ec2; deny[...]"}
  ↓
OPA evaluates all rules in cspm.aws.ec2
  ↓
Return violations:
  [
    {
      "rule_id": "ec2-open-security-group",
      "severity": "HIGH",
      "message": "..."
    },
    {
      "rule_id": "ec2-no-iam-role",
      "severity": "MEDIUM",
      "message": "..."
    }
  ]
  ↓
Policy Service publishes to Kafka: finding.raw
```

---

### Alert Service (Port 8004)

**Purpose:** Finding ingestion, deduplication, notifications, SLA tracking

**Key Endpoints:**

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/internal/findings` | ✅ | List findings (with filters) |
| GET | `/internal/findings/{id}` | ✅ | Get finding detail |
| PATCH | `/internal/findings/{id}` | ✅ | Update status |
| POST | `/internal/findings/bulk` | ✅ | Bulk update (max 500) |
| POST | `/internal/findings/submit` | ✅ JWT (CI/CD) | Direct REST submission |
| POST | `/internal/findings/{id}/suppress` | ✅ | Suppress finding |
| POST | `/internal/findings/{id}/accept-risk` | ✅ | Accept risk |
| GET | `/internal/findings/stats` | ✅ | Statistics |
| GET | `/internal/suppressions` | ✅ | List suppression rules |
| POST | `/internal/suppressions` | ✅ | Create rule |
| GET | `/internal/notifications/channels` | ✅ | List channels |
| POST | `/internal/notifications/channels` | ✅ | Create channel |
| POST | `/internal/notifications/test` | ✅ | Test notification |
| GET | `/internal/incidents` | ✅ | List incidents |
| PATCH | `/internal/incidents/{id}` | ✅ | Update incident |

**Deduplication:**

```python
def compute_fingerprint(finding: RawFinding) -> str:
    """SHA-256 fingerprint prevents duplicate findings."""
    key = f"{finding['rule_id']}:{finding['resource_id']}:{finding['region']}"
    return hashlib.sha256(key.encode()).hexdigest()

# Lookup existing
existing = await repo.find_by_fingerprint(fingerprint)

if existing:
    # Update existing finding
    await existing.update(
        last_seen_at=now,
        regression_count=existing.regression_count + 1
    )
    event = 'finding.seen_again'
else:
    # Create new finding
    finding = await repo.create(Finding(...))
    event = 'finding.created'

# Publish event
await producer.send(event, finding.dict())
```

**Suppression Rules:**

```python
class SuppressionRuleModel:
    rule_id: str                  # e.g., "s3-public-access"
    resource_tag_key: str         # e.g., "Environment"
    resource_tag_value: str       # e.g., "dev"
    account_id: str               # e.g., "123456789"
    region: str                   # e.g., "us-east-1"
    reason: str                   # "False positive - configured intentionally"
    expires_at: datetime          # Auto-unsuppress after date
    is_active: bool

def should_suppress(finding: Finding, rules: List[SuppressionRule]) -> bool:
    for rule in rules:
        # Check all conditions (AND logic)
        if (rule.rule_id != finding.rule_id):
            continue
        if (rule.account_id and rule.account_id != finding.account_id):
            continue
        if (rule.region and rule.region != finding.region):
            continue
        if (rule.resource_tag_key and finding.tags.get(rule.resource_tag_key) != rule.resource_tag_value):
            continue
        if (rule.expires_at and rule.expires_at < datetime.now()):
            continue
        
        # All conditions matched
        return True
    
    return False
```

**Notification Channels:**

```python
class NotificationChannelModel:
    channel_type: str             # slack, jira, email, pagerduty, teams, webhook
    config: dict                  # Provider-specific config
    severity_filter: List[str]    # [CRITICAL, HIGH] → Only alert on these
    module_filter: List[str]      # [cspm, cwpp] → Only from these modules
    account_filter: List[str]     # [prod, staging] → Only from these accounts
    tag_filter: dict              # {Environment: prod} → Only tagged resources

# Example: Slack for production CRITICAL findings
{
    "channel_type": "slack",
    "config": {
        "webhook_url": "https://hooks.slack.com/...",
        "channel": "#security-alerts",
        "mention_group": "@security-team"
    },
    "severity_filter": ["CRITICAL"],
    "module_filter": ["cspm"],
    "account_filter": ["prod"],
    "tag_filter": {"Environment": "prod"}
}

# Flow:
# New HIGH finding in CSPM for staging account
#   ├─ Slack channel: severity HIGH not in [CRITICAL] → NO
#   ├─ Jira channel: module cspm in [cspm, cwpp] ✓, severity HIGH in [CRITICAL, HIGH] ✓, account staging in [prod] → NO
#   ├─ Email: digest only → NO
#   └─ PagerDuty: severity HIGH not CRITICAL → NO
# Result: No notifications sent
```

**Notification Implementations:**

- **Slack:**
  ```python
  async def send_slack(channel: NotificationChannel, finding: Finding):
      client = WebClient(token=channel.config['webhook_url'])
      
      severity_color = {
          'CRITICAL': '#dc2626',
          'HIGH': '#ea580c',
          'MEDIUM': '#d97706',
          'LOW': '#2563eb',
      }[finding.severity]
      
      await client.chat_postMessage(
          channel=channel.config['channel'],
          attachments=[{
              'fallback': finding.title,
              'color': severity_color,
              'title': finding.title,
              'text': finding.description,
              'fields': [
                  {'title': 'Severity', 'value': finding.severity, 'short': True},
                  {'title': 'Resource', 'value': finding.resource_id, 'short': True},
                  {'title': 'Remediation', 'value': finding.remediation, 'short': False},
              ],
              'actions': [
                  {'type': 'button', 'text': 'View in Dashboard', 'url': f'https://.../{finding.id}'},
                  {'type': 'button', 'text': 'Acknowledge', 'value': 'acknowledge'},
              ]
          }]
      )
  ```

- **Jira:**
  ```python
  async def send_jira(channel: NotificationChannel, finding: Finding):
      jira = JIRA(
          server=channel.config['url'],
          basic_auth=(channel.config['username'], channel.config['api_token'])
      )
      
      issue = jira.create_issue(
          project=channel.config['project'],
          issuetype='Security Vulnerability',
          summary=finding.title,
          description=finding.description,
          priority={'CRITICAL': 'Highest', 'HIGH': 'High', 'MEDIUM': 'Medium', 'LOW': 'Low'}[finding.severity],
          labels=['cloudvisor', finding.module],
          customfield_10000=finding.remediation,  # Remediation field
      )
      
      # Store issue key for bi-directional sync
      await repo.update(finding.id, {'jira_issue_key': issue.key})
  ```

- **Email:**
  ```
  Daily digest email for MEDIUM/LOW findings
  Real-time for CRITICAL/HIGH findings
  ```

- **PagerDuty:**
  ```python
  # Trigger incident for CRITICAL findings
  # Escalation policy: 5-minute escalation
  # Auto-resolve when finding is resolved
  ```

**SLA Tracking:**

```python
class SLATarget:
    CRITICAL_ACK_HOURS = 4
    CRITICAL_RESOLVE_HOURS = 24
    HIGH_ACK_HOURS = 24
    HIGH_RESOLVE_HOURS = 7 * 24  # 7 days
    MEDIUM_RESOLVE_HOURS = 30 * 24  # 30 days

async def check_sla_violation(finding: Finding) -> bool:
    if finding.status == 'resolved':
        return False  # Already resolved
    
    now = datetime.now(timezone.utc)
    created_age_hours = (now - finding.first_seen_at).total_seconds() / 3600
    
    if finding.acknowledged_at is None:
        # Not yet acknowledged
        sla_target = {
            'CRITICAL': SLATarget.CRITICAL_ACK_HOURS,
            'HIGH': SLATarget.HIGH_ACK_HOURS,
        }.get(finding.severity, float('inf'))
        
        if created_age_hours > sla_target:
            return True  # Ack SLA violated
    
    # Check resolve SLA
    if finding.acknowledged_at:
        ack_age_hours = (now - finding.acknowledged_at).total_seconds() / 3600
    else:
        ack_age_hours = created_age_hours
    
    sla_target = {
        'CRITICAL': SLATarget.CRITICAL_RESOLVE_HOURS,
        'HIGH': SLATarget.HIGH_RESOLVE_HOURS,
        'MEDIUM': SLATarget.MEDIUM_RESOLVE_HOURS,
    }.get(finding.severity, float('inf'))
    
    return ack_age_hours > sla_target
```

**Incident Grouping:**

```python
async def create_or_update_incident(finding: Finding):
    # Group by rule + account + time window
    # Query: findings with same rule_id + account_id created within last 24h
    
    related = await repo.find_findings(
        rule_id=finding.rule_id,
        account_id=finding.account_id,
        created_after=datetime.now() - timedelta(hours=24),
        status=['open', 'in_progress']
    )
    
    if len(related) >= 5:
        # Potential incident: 5+ related findings
        incident = await repo.find_or_create_incident(
            title=f"Bulk {finding.severity} findings: {finding.rule_id}",
            description=f"Multiple violations of {finding.rule_id} detected",
            finding_ids=[f.id for f in related]
        )
        
        await producer.send('incident.created', incident.dict())
```

---

### AI Copilot Service (Port 8010)

**Purpose:** RAG-powered natural language interface to security data

**Key Endpoints:**

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/v1/copilot/query` | ✅ JWT | Submit query |
| GET | `/v1/copilot/history` | ✅ JWT | Get query history |

**RAG Pipeline (6 Steps):**

```python
# Step 1: Intent Classification
def classify_intent(query: str) -> str:
    # Uses keyword matching or light ML model
    # Returns: POSTURE | FINDING | COMPLIANCE | REMEDIATION | THREAT | DRIFT
    
    keywords = {
        'POSTURE': ['exposure', 'risk', 'score', 'vulnerable'],
        'FINDING': ['critical', 'alert', 'violation', 'finding'],
        'COMPLIANCE': ['pci', 'hipaa', 'cis', 'compliance', 'control'],
        'REMEDIATION': ['fix', 'remediate', 'patch', 'resolve', 'code'],
        'THREAT': ['attack', 'breach', 'threat', 'incident', 'exploit'],
        'DRIFT': ['change', 'diff', 'deploy', 'modified', 'updated'],
    }
    
    query_lower = query.lower()
    for intent, kws in keywords.items():
        if any(kw in query_lower for kw in kws):
            return intent
    
    return 'POSTURE'  # Default

# Step 2: Query Embedding
embedding = embed_text(query, model='text-embedding-3-small')
# Returns: 1536-dimensional vector

# Step 3: Multi-Source Retrieval
async def retrieve_context(org_id: str, query: str, intent: str, embedding: List[float]) -> str:
    context_parts = []
    
    # Source 1: Neo4j asset graph
    neo4j_result = await neo4j_query(f"""
        MATCH (r:Resource)-[*1..3]->(related)
        WHERE r.name ILIKE $query OR r.resource_id ILIKE $query
        RETURN r, related LIMIT 10
    """, query=query)
    context_parts.append(f"# Asset Context\n{neo4j_result}")
    
    # Source 2: Elasticsearch findings
    es_result = await es_search(
        index='findings',
        query={
            'bool': {
                'must': [
                    {'match': {'title': query}},
                    {'term': {'organization_id': org_id}},
                    {'range': {'last_seen_at': {'gte': 'now-7d'}}}
                ]
            }
        },
        size=10
    )
    context_parts.append(f"# Related Findings\n{es_result}")
    
    # Source 3: PostgreSQL compliance
    compliance = await db.query(f"""
        SELECT * FROM compliance_controls
        WHERE organization_id = $1 AND (description ILIKE $2)
        LIMIT 5
    """, org_id, query)
    context_parts.append(f"# Compliance Controls\n{compliance}")
    
    # Source 4: CIEM permissions
    perms = await ciem_service.query_permissions(org_id, query)
    context_parts.append(f"# IAM Permissions\n{perms}")
    
    # Source 5: CWPP vulnerabilities
    vulns = await cwpp_service.search_vulnerabilities(org_id, query)
    context_parts.append(f"# Vulnerabilities\n{vulns}")
    
    # Source 6: CDR threat log
    threats = await cdr_service.search_threats(org_id, query)
    context_parts.append(f"# Threat Events\n{threats}")
    
    return "\n\n".join(context_parts)

# Step 4: Prompt Construction
prompt = f"""
You are CloudVisor Q, a security intelligence assistant. Answer the user's question
based ONLY on the provided context. Do not use general knowledge about cloud security.
Always cite your sources.

CONTEXT:
{context}

USER QUERY:
{query}

INSTRUCTIONS:
1. Answer directly and concisely
2. If you don't know the answer, say so
3. Always include citations like [source: finding_123]
4. Suggest next steps or remediation if applicable
5. Use bullet points for clarity

ANSWER:
"""

# Step 5: Claude API Call
response = await claude.messages.create(
    model="claude-3-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": prompt}
    ]
)

answer = response.content[0].text

# Step 6: Audit Logging
await repo.create_query_log(
    org_id=org_id,
    user_id=user_id,
    query=query,
    intent=intent,
    context_sources=source_list,
    response=answer,
    tokens_used=response.usage.output_tokens,
    timestamp=datetime.now()
)
```

**Database Model:**

```python
class CopilotQueryLogModel:
    id: UUID
    org_id: UUID
    user_id: UUID
    query: str
    intent: str
    context_sources: List[str]  # ['neo4j', 'elasticsearch', 'postgresql']
    response: str
    tokens_used: int
    response_time_ms: int
    created_at: datetime
```

---

## Database Documentation

### Multi-Database Architecture

```
PostgreSQL 15 (Primary)
├─ Multi-tenant data store
├─ RLS policies enforce org isolation
├─ JSONB columns for flexibility
├─ 15+ tables across services
└─ Connection pooling (20 connections)

Neo4j 5.15 (Graph Database)
├─ Asset relationship graph
├─ 2-5M nodes (depends on discovery scope)
├─ Risk scoring & attack path analysis
└─ Full-text search integration

Elasticsearch 8.12 (Search Engine)
├─ Finding full-text search
├─ Aggregations (by severity, status, etc.)
├─ Real-time indexing
└─ 10M+ documents (depends on volume)

Redis 7 (Cache & Pub/Sub)
├─ Session cache (Redis DB 0)
├─ Rate limit counters (Redis DB 4)
├─ Pub/Sub for WebSocket updates
└─ TTL-based expiration
```

### PostgreSQL Schema

**Core Tables:**

```sql
-- Authentication (Auth Service)
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',
    billing_email VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    mfa_backup_codes JSONB,  -- Hashed backup codes
    provider VARCHAR(20) DEFAULT 'local',  -- local, google, github, saml
    provider_id VARCHAR(255),  -- Prevents cross-provider collisions
    last_login_at TIMESTAMP,
    locked_until TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT uq_provider_id UNIQUE (provider, provider_id)  -- Composite key
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),  -- Denormalized for RLS
    refresh_token_hash VARCHAR(255) NOT NULL,
    device_info TEXT,
    ip_address INET,
    last_active_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    scopes JSONB DEFAULT '[]',
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    organization_id UUID NOT NULL,
    user_id UUID REFERENCES users(id),
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,
    ip_address INET,
    success BOOLEAN DEFAULT TRUE,
    failure_reason TEXT,
    timestamp TIMESTAMP NOT NULL
);

-- Security Findings (Alert Service)
CREATE TABLE findings (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    rule_id VARCHAR(255) NOT NULL,
    resource_id VARCHAR(512) NOT NULL,
    resource_name VARCHAR(255),
    resource_type VARCHAR(100),
    severity VARCHAR(20) NOT NULL,  -- CRITICAL, HIGH, MEDIUM, LOW, INFO
    status VARCHAR(20) DEFAULT 'open',  -- open, in_progress, resolved, accepted, suppressed
    title VARCHAR(500) NOT NULL,
    description TEXT,
    remediation TEXT,
    provider VARCHAR(20),  -- aws, azure, gcp, oci
    account_id VARCHAR(255),
    region VARCHAR(50),
    tags JSONB,  -- {"Environment": "prod", "Owner": "team-a"}
    compliance_mapping JSONB[],  -- [{"framework": "CIS AWS", "control": "5.2"}]
    context JSONB,  -- Rich context from graph service
    assignee_id UUID REFERENCES users(id),
    fingerprint VARCHAR(64) UNIQUE NOT NULL,  -- SHA-256 dedup key
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    regression_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_org FOREIGN KEY (organization_id) REFERENCES organizations(id),
    CONSTRAINT ck_severity CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')),
    CONSTRAINT ck_status CHECK (status IN ('open', 'in_progress', 'resolved', 'accepted', 'suppressed'))
);

CREATE INDEX idx_findings_org_created ON findings(organization_id, created_at DESC);
CREATE INDEX idx_findings_fingerprint ON findings(fingerprint);
CREATE INDEX idx_findings_status ON findings(organization_id, status);
CREATE INDEX idx_findings_severity ON findings(organization_id, severity);

-- Suppression Rules (Alert Service)
CREATE TABLE suppression_rules (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    rule_id VARCHAR(255),
    resource_tag_key VARCHAR(100),
    resource_tag_value VARCHAR(255),
    account_id VARCHAR(255),
    region VARCHAR(50),
    reason TEXT,
    created_by VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL
);

-- Notification Channels (Alert Service)
CREATE TABLE notification_channels (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    channel_type VARCHAR(50) NOT NULL,  -- slack, jira, email, pagerduty, teams, webhook
    config JSONB NOT NULL,  -- Provider-specific config (encrypted in production)
    severity_filter TEXT[],  -- [CRITICAL, HIGH]
    module_filter TEXT[],  -- [cspm, cwpp]
    account_filter TEXT[],  -- [prod, staging]
    tag_filter JSONB,  -- {Environment: prod}
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Row-Level Security
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation_findings ON findings
    USING (organization_id = current_setting('app.current_org_id')::uuid)
    WITH CHECK (organization_id = current_setting('app.current_org_id')::uuid);

-- Cloud Accounts (Connector Service)
CREATE TABLE cloud_accounts (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    provider VARCHAR(20) NOT NULL,  -- aws, azure, gcp, oci
    account_name VARCHAR(255) NOT NULL,
    provider_account_id VARCHAR(255) NOT NULL,  -- AWS account ID, Azure subscription ID, etc.
    credentials_vault_path VARCHAR(255) NOT NULL,  -- /cloudvisor/credentials/aws-prod
    sync_frequency_minutes INTEGER DEFAULT 60,
    last_sync_at TIMESTAMP,
    last_sync_error TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT uq_org_provider_account UNIQUE (organization_id, provider, provider_account_id)
);

-- Copilot Query Audit Log (Copilot Service)
CREATE TABLE copilot_queries (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    query TEXT NOT NULL,
    intent VARCHAR(50),  -- POSTURE, FINDING, COMPLIANCE, REMEDIATION, THREAT, DRIFT
    context_sources TEXT[],  -- ['neo4j', 'elasticsearch', 'postgresql']
    response TEXT,
    tokens_used INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP NOT NULL
);

-- Incidents (Alert Service)
CREATE TABLE incidents (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'open',  -- open, in_progress, resolved
    finding_ids UUID[],
    assignee_id UUID REFERENCES users(id),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP
);

-- Compliance Controls (Alert Service)
CREATE TABLE compliance_controls (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    framework VARCHAR(100),  -- CIS AWS, SOC 2, PCI-DSS, HIPAA, ISO27001
    control_id VARCHAR(255),  -- CIS AWS 5.2, PCI 2.1, etc.
    description TEXT,
    passing_count INTEGER DEFAULT 0,
    failing_count INTEGER DEFAULT 0,
    last_evaluated_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL
);
```

### Neo4j Graph Schema

**Node Labels & Properties:**

```cypher
// Cloud Accounts
(:Account {
    id: "acc-123",
    provider: "aws",
    account_id: "123456789",
    account_name: "production",
    region: "us-east-1",
    created_at: datetime()
})

// Compute Instances
(:EC2Instance {
    resource_id: "i-1234567890abcdef0",
    instance_type: "t3.medium",
    state: "running",
    public_ip: "203.0.113.45",
    is_internet_facing: true,
    risk_score: 78.5,
    tags: {Environment: "prod", Owner: "team-a"}
})

(:VirtualMachine {
    resource_id: "vm-abc123",
    vm_size: "Standard_B2s",
    os_type: "Windows",
    is_internet_facing: false
})

// Networking
(:SecurityGroup {
    resource_id: "sg-1234567",
    name: "prod-web-sg",
    ingress_rules: [{Port: 443, Protocol: "tcp", Cidr: "0.0.0.0/0"}]
})

(:CIDR {
    value: "0.0.0.0/0",
    is_internet: true
})

// Storage
(:S3Bucket {
    resource_id: "my-prod-bucket",
    region: "us-east-1",
    versioning_enabled: true,
    public_access_blocked: false
})

// Database
(:RDSInstance {
    resource_id: "prod-db-1",
    engine: "postgres",
    is_publicly_accessible: false,
    contains_pii: true,
    backup_retention_days: 30
})

// IAM
(:IAMRole {
    resource_id: "role-123",
    name: "EC2-ReadS3",
    trust_relationship: {...},
    assume_role_policy: {...}
})

(:IAMPolicy {
    resource_id: "policy-456",
    name: "S3FullAccess",
    statement: [...]
})

// Relationships
EC2Instance -[:ATTACHED_TO]-> SecurityGroup
SecurityGroup -[:ALLOWS_INBOUND_FROM]-> CIDR {port: 22, protocol: "tcp"}
EC2Instance -[:IN_ACCOUNT]-> Account
EC2Instance -[:IN_REGION]-> Region
EC2Instance -[:CONNECTED_TO]-> RDSInstance
EC2Instance -[:HAS_IAM_ROLE]-> IAMRole
IAMRole -[:HAS_POLICY]-> IAMPolicy
IAMPolicy -[:GRANTS_ACCESS_TO]-> S3Bucket
Account -[:HAS_FINDING]-> Finding {severity: "HIGH"}

// Relationship properties
[relationship] {
    created_at: datetime(),
    updated_at: datetime(),
    risk_level: "high" | "medium" | "low"
}
```

### Elasticsearch Schema

**Index Mapping (findings):**

```json
{
  "mappings": {
    "properties": {
      "id": {"type": "keyword"},
      "organization_id": {"type": "keyword"},
      "rule_id": {"type": "keyword"},
      "resource_id": {"type": "keyword"},
      "resource_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
      "resource_type": {"type": "keyword"},
      "severity": {"type": "keyword"},
      "status": {"type": "keyword"},
      "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
      "description": {"type": "text"},
      "provider": {"type": "keyword"},
      "account_id": {"type": "keyword"},
      "region": {"type": "keyword"},
      "tags": {"type": "object", "enabled": true},
      "first_seen_at": {"type": "date"},
      "last_seen_at": {"type": "date"},
      "resolved_at": {"type": "date"},
      "created_at": {"type": "date"},
      "fingerprint": {"type": "keyword"}
    }
  }
}
```

**Search Queries:**

```python
# Full-text search
{
  "query": {
    "bool": {
      "must": [
        {"match": {"title": "open security group"}},
        {"term": {"organization_id": "org-123"}},
        {"term": {"severity": "HIGH"}}
      ],
      "filter": [
        {"range": {"created_at": {"gte": "now-7d"}}}
      ]
    }
  }
}

# Aggregations (metrics dashboard)
{
  "aggs": {
    "by_severity": {
      "terms": {"field": "severity", "size": 5}
    },
    "by_status": {
      "terms": {"field": "status"}
    },
    "by_provider": {
      "terms": {"field": "provider"}
    },
    "daily_trend": {
      "date_histogram": {"field": "created_at", "interval": "1d"}
    }
  }
}
```

### Important Queries & Indexing Strategy

**PostgreSQL Indices:**

```sql
-- Findings lookup (most common query)
CREATE INDEX idx_findings_org_created ON findings(organization_id, created_at DESC);
CREATE INDEX idx_findings_fingerprint ON findings(fingerprint);

-- Auth queries
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_sessions_user_expires ON sessions(user_id, expires_at);

-- Audit queries
CREATE INDEX idx_audit_org_timestamp ON audit_log(organization_id, timestamp DESC);

-- Cloud accounts
CREATE INDEX idx_cloud_accounts_org ON cloud_accounts(organization_id);

-- Copilot queries
CREATE INDEX idx_copilot_org_created ON copilot_queries(organization_id, created_at DESC);
```

**Neo4j Indices:**

```cypher
CREATE INDEX resource_by_id IF NOT EXISTS FOR (r:Resource) ON (r.resource_id);
CREATE INDEX account_by_provider IF NOT EXISTS FOR (a:Account) ON (a.account_id);
CREATE INDEX finding_by_severity IF NOT EXISTS FOR (f:Finding) ON (f.severity);

-- Full-text search index
CREATE FULLTEXT INDEX resource_search FOR (r:Resource) ON EACH [r.name, r.resource_type];
```

---

## DevOps & Infrastructure

### Deployment Architecture

```
┌──────────────────────────────────────────────┐
│          Production Environment              │
├──────────────────────────────────────────────┤
│                                               │
│  ┌─────────────────────────────────────┐    │
│  │  Load Balancer (AWS ALB / Nginx)   │    │
│  │  Port 443 (HTTPS)                  │    │
│  └────────────┬────────────────────────┘    │
│               │                              │
│  ┌────────────▼────────────────────────┐    │
│  │  Kubernetes Cluster (1.28+)        │    │
│  │                                     │    │
│  │  ┌─────────────────────────────┐  │    │
│  │  │ Namespace: cloudvisor       │  │    │
│  │  │                             │  │    │
│  │  │ ┌────────┐  ┌─────────────┐ │  │    │
│  │  │ │  Web   │  │ API Gateway │ │  │    │
│  │  │ │  (3)   │  │     (2)     │ │  │    │
│  │  │ └────────┘  └─────────────┘ │  │    │
│  │  │ ┌─────┐ ┌─────┐ ┌─────┐     │  │    │
│  │  │ │Auth │ │ Conn│ │Graph│ ... │  │    │
│  │  │ │ (3) │ │ (2) │ │ (2) │     │  │    │
│  │  │ └─────┘ └─────┘ └─────┘     │  │    │
│  │  │                             │  │    │
│  │  │ PVC: postgres-pvc, neo4j-pvc│  │    │
│  │  └─────────────────────────────┘  │    │
│  │                                     │    │
│  │  StatefulSets:                      │    │
│  │  ├─ postgres (1 replica)            │    │
│  │  ├─ neo4j (1 replica)               │    │
│  │  ├─ elasticsearch (1 replica)       │    │
│  │  ├─ kafka (3 replicas)              │    │
│  │  └─ redis (1 replica)               │    │
│  │                                     │    │
│  └─────────────────────────────────────┘    │
│                                               │
│  ┌─────────────────────────────────────┐    │
│  │  Storage                            │    │
│  │  ├─ PostgreSQL PVC: 100GB          │    │
│  │  ├─ Neo4j PVC: 50GB                │    │
│  │  ├─ Elasticsearch PVC: 200GB       │    │
│  │  └─ Kafka PVC: 500GB               │    │
│  └─────────────────────────────────────┘    │
│                                               │
│  ┌─────────────────────────────────────┐    │
│  │  Secrets (HashiCorp Vault / K8s)   │    │
│  │  ├─ DB credentials                  │    │
│  │  ├─ Cloud provider credentials      │    │
│  │  ├─ API keys                        │    │
│  │  └─ JWT signing keys                │    │
│  └─────────────────────────────────────┘    │
│                                               │
└──────────────────────────────────────────────┘
```

### Docker Compose (Local Development)

**File:** `docker-compose.yml`

**Services Orchestrated:**

1. **Nginx** — Reverse proxy, SSL termination
2. **PostgreSQL** — Primary data store
3. **Neo4j** — Graph database
4. **Elasticsearch** — Search engine
5. **Zookeeper** — Kafka coordination
6. **Kafka** — Message broker
7. **Schema Registry** — Kafka schema management
8. **Redis** — Cache & pub/sub
9. **OPA** — Policy engine
10. **Vault** — Secrets management
11. **Vault-Init** — Vault initialization
12. **Auth Service** — Port 8002
13. **Connector Service** — Port 8000
14. **Graph Service** — Port 8001
15. **Policy Service** — Port 8003
16. **Alert Service** — Port 8004
17. **API Gateway** — Port 8005
18. **CSPM Service** — Port 8006
19. **Keep (AIOps)** — Port 8007
20. **Copilot Service** — Port 8010
21. **AI Router** — Port 8015
22. **Soketi (WebSocket)** — Ports 6001, 9601
23. **Web Frontend** — Port 3000
24. **Adminer** — Port 8082 (database UI)

**Key Docker Configurations:**

```yaml
# Health checks on all services
postgres:
  healthcheck:
    test: ["CMD", "pg_isready", "-U", "cvadmin"]
    interval: 10s
    timeout: 5s
    retries: 5

# Networking: all services on cloudvisor bridge
networks:
  cloudvisor:
    driver: bridge

# Environment variable precedence:
# 1. env_file (.env)
# 2. environment override
# 3. .env.example (default)

# Resource limits on compute-heavy services
api-service:
  deploy:
    resources:
      limits:
        cpus: "1.0"
        memory: 512M
      reservations:
        cpus: "0.25"
        memory: 128M
```

---

### CI/CD Pipeline (GitHub Actions)

**Assumed (not yet implemented):**

```yaml
name: CI/CD
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Backend tests
      - name: Run backend tests
        run: |
          cd services/api && pytest
          cd ../auth && pytest
          cd ../connector && pytest
      
      # Frontend tests
      - name: Run frontend tests
        run: cd apps/web && npm test
      
      # Docker build verification
      - name: Build Docker images
        run: docker-compose build

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Deploy to K8s cluster
      - name: Deploy to production
        run: |
          kubectl apply -f k8s/
          kubectl rollout status deployment/api-service
```

---

### Environment Variables & Configuration

**File:** `.env.example`

```bash
# ─── Secrets (NEVER hardcode, use .env) ────────────────────────────────

# PostgreSQL
POSTGRES_PASSWORD=change-me-to-a-secure-password

# Neo4j
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-me-to-a-secure-password

# Elasticsearch
ELASTIC_USERNAME=elastic
ELASTIC_PASSWORD=change-me-to-a-secure-password

# AI/ML APIs
COPILOT_NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxx

# ─── Service URLs (Docker network) ─────────────────────────────────────

DB_URL=postgresql+asyncpg://cvadmin:${POSTGRES_PASSWORD}@cv-postgres:5432/cloudvisor
REDIS_URL=redis://cv-redis:6379/0
KAFKA_BOOTSTRAP_SERVERS=cv-kafka:9092

# ─── Application Settings ─────────────────────────────────────────────

APP_ENVIRONMENT=development  # or production
DEBUG=false

API_RATE_LIMIT_REQUESTS_PER_MINUTE=600
AUTH_SECRET_KEY=change-me-in-production-min-32-chars!

# ─── Observability ────────────────────────────────────────────────────

OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
LOG_LEVEL=INFO
```

**Loading Order:**

```python
# services/auth/main.py
settings = get_settings()

# Searches:
# 1. .env (loaded first)
# 2. Environment variables
# 3. defaults in code
# 4. .env.example (fallback documentation)
```

---

### Cloud Services Integration

**AWS:**
- **IAM** — Connector assumes role via STS
- **EC2, VPC, S3, RDS, Lambda, etc.** — Discovered via API
- **KMS** — Encrypt Vault credentials at rest
- **CloudTrail** — Cloud event auditing
- **CloudWatch** — Centralized logging

**Azure:**
- **Managed Identity** — Connector auth
- **Azure AD** — User SSO (future)
- **Key Vault** — Credential storage
- **Log Analytics** — Centralized logging
- **Monitor** — Metrics collection

**GCP:**
- **Service Accounts** — Connector auth
- **IAM** — Workload identity
- **Secret Manager** — Credential storage
- **Cloud Logging** — Centralized logging
- **Cloud Monitoring** — Metrics

**OCI:**
- **OCI IAM** — Connector auth
- **API Signing** — Request authentication
- **Vault** — Credential storage
- **Logging** — Centralized logging
- **Monitoring** — Metrics

---

### Monitoring, Logging, & Scaling

**Logging:**

```
Application Logs:
  ├─ Structured JSON format (ECS)
  ├─ Severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  ├─ Correlation ID propagation (X-Correlation-ID header)
  └─ Service name + instance ID included

Collection:
  ├─ Docker: docker logs cv-auth (local dev)
  ├─ K8s: kubectl logs -l app=auth (production)
  └─ Log aggregation: ELK stack or Cloud logging

Audit Logging:
  ├─ All auth events → audit_log table
  ├─ All copilot queries → copilot_queries table
  ├─ All finding changes → finding_history table
  └─ 365-day minimum retention
```

**Metrics (Prometheus):**

```
# Exported from each service
cloudvisor_http_requests_total{method, endpoint, status}
cloudvisor_http_request_duration_ms{method, endpoint, quantile}
cloudvisor_kafka_messages_consumed_total{topic, consumer_group}
cloudvisor_database_query_duration_ms{query, quantile}
cloudvisor_findings_total{severity, status, provider}
cloudvisor_assets_total{resource_type, provider}
cloudvisor_api_rate_limit_hits_total{org_id}
```

**Alerts (Prometheus AlertManager):**

```yaml
alert: HighErrorRate
condition: >
  (sum(rate(cloudvisor_http_requests_total{status="5xx"}[5m])) by (service))
  /
  (sum(rate(cloudvisor_http_requests_total[5m])) by (service))
  > 0.05
annotation: "{{ $labels.service }} has >5% error rate"

alert: DatabaseConnectionPoolExhausted
condition: cloudvisor_db_connections_used >= 18  # Out of 20
```

**Scaling:**

```
Horizontal Scaling (add replicas):
  ├─ Stateless services: Auth, API, Policy
  │  └─ Min 2, max 10 replicas (HPA)
  ├─ Stateful services: Connector, Copilot
  │  └─ Min 1, max 3 replicas (manage state carefully)
  └─ Worker services: Alert consumer
     └─ Min 1, max 5 replicas (per Kafka partition)

Vertical Scaling (increase resources per pod):
  ├─ CPU: 250m (request) → 1000m (limit)
  └─ Memory: 128M (request) → 512M (limit)

Database Scaling:
  ├─ PostgreSQL: Read replicas (standby servers)
  ├─ Neo4j: Enterprise clustering (3+ nodes)
  └─ Elasticsearch: Horizontal sharding (3-5 nodes)

Kafka Scaling:
  └─ Increase topic partitions (enables parallel consumption)
```

---

## Security Analysis

### Authentication Flows

#### 1. User Registration & Login

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ POST /auth/register
       ├─ email, password, org_name
       ↓
┌──────────────────────────────────────┐
│  Auth Service                        │
├──────────────────────────────────────┤
│  1. Hash password (bcrypt, rounds=12)│
│  2. Create organization              │
│  3. Create user                      │
│  4. Store MFA secret (encrypted)     │
│  5. Generate JWT + refresh token     │
│  6. Log: user.created                │
└──────┬───────────────────────────────┘
       │
       │ Response (200 OK)
       ├─ access_token (JWT, 15min)
       ├─ refresh_token (opaque, 30d)
       ├─ Set-Cookie: session (HttpOnly, Secure, SameSite=Strict)
       ↓
┌─────────────┐
│   Browser   │ stores JWT in localStorage (for API calls)
│             │ stores cookies in secure storage (HttpOnly)
└─────────────┘
```

#### 2. Multi-Factor Authentication (TOTP)

```
User enables MFA:
  1. POST /auth/mfa/enroll
  2. Service generates secret (pyotp.random_base32())
  3. Returns QR code + secret
  4. User scans in authenticator app (Google Authenticator, Authy, etc.)
  
  5. User submits 6-digit code
  6. Service verifies code (pyotp.verify_totp(code, secret))
  7. Generates backup codes (10x 8-digit, bcrypt-hashed)
  
Subsequent logins:
  1. Username + password
  2. Server responds with MFA required
  3. Client prompts for 6-digit code
  4. POST /auth/mfa/verify with code
  5. Server verifies + creates session
```

#### 3. API Key Authentication

```
Application needs access to CloudVisor API:
  1. User generates API key: POST /auth/api-keys
  2. Service returns: "cv_live_abc123def456ghi789"  (never returned again)
  3. User stores securely in environment variables
  
Subsequent API calls:
  Header: X-API-Key: cv_live_abc123def456ghi789
  
  API Gateway:
    1. Extracts key from header
    2. Computes bcrypt hash
    3. Queries database: SELECT * FROM api_keys WHERE key_hash = ?
    4. Verifies scopes (e.g., ["findings:read"])
    5. Sets user_id + org_id in request context
    6. Calls upstream service with X-Authenticated-User header
```

#### 4. Service-to-Service Authentication (Internal)

```
Internal service calls (e.g., Alert → Graph):
  1. Service creates JWT with internal secret
  2. Includes org_id + service_name in token
  3. Signs with HS256
  
  Header: Authorization: Bearer eyJhbGc...
  
  Receiving service:
    1. Validates signature (must be internal secret)
    2. Extracts org_id + service_name
    3. Verifies service_name is in allowlist
    4. Proceeds with request
```

### Authorization Model

**RBAC (Role-Based Access Control):**

```
Organization
  ├─ Role: admin
  │  ├─ Permissions: *:* (all)
  │  └─ Scope: all accounts, all regions
  │
  ├─ Role: security_lead
  │  ├─ Permissions: findings:*, policies:write, compliance:read, assets:read
  │  └─ Scope: all accounts
  │
  ├─ Role: engineer
  │  ├─ Permissions: findings:read, assets:read, incidents:read
  │  └─ Scope: assigned accounts only
  │
  └─ Role: viewer
     ├─ Permissions: findings:read, assets:read, compliance:read
     └─ Scope: all accounts
```

**Resource-Level Scoping:**

```python
# Custom role for "staging_lead"
{
    "role_name": "staging_lead",
    "permissions": ["findings:read", "findings:write", "assets:read"],
    "scope": {
        "account_ids": ["staging-123", "dev-456"],
        "regions": ["us-east-1", "eu-west-1"],
        "tags": {"Environment": ["staging", "dev"]}
    }
}

# Authorization check before returning findings:
def can_access_finding(user, finding):
    # 1. Check if user has findings:read permission
    if "findings:read" not in user.permissions:
        return False
    
    # 2. Check resource-level scope
    if user.scope.account_ids:
        if finding.account_id not in user.scope.account_ids:
            return False
    
    if user.scope.tags:
        for key, allowed_values in user.scope.tags.items():
            if finding.tags.get(key) not in allowed_values:
                return False
    
    return True
```

---

### Security Best Practices Implemented

#### 1. **Password Security**

```python
# Bcrypt hashing (rounds=12 = ~250ms per hash)
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

password_hash = pwd_context.hash("user_password")
pwd_context.verify("user_password", password_hash)  # True or False
```

**Strength Requirements:**
- Minimum 12 characters
- Uppercase + lowercase + numbers + special chars
- Not common/breached passwords (checked against haveibeenpwned API)
- Failed login lockout: 5 attempts → lock 30 minutes

#### 2. **JWT Security**

```python
# Token structure
{
    "sub": "user_123",                      # Subject (user ID)
    "org_id": "org_456",                    # Organization
    "exp": 1234567890,                      # Expiration (15 minutes)
    "iat": 1234567500,                      # Issued at
    "nbf": 1234567500,                      # Not before
    "iss": "cloudvisor",                    # Issuer
    "aud": ["api", "web"],                  # Audience
    "scopes": ["findings:read", "..."]      # Permissions
}

# Signed with HS256 (HMAC-SHA256)
# Secret: minimum 32 characters, rotated quarterly
```

**Validation on every request:**
- ✅ Signature valid
- ✅ Not expired
- ✅ Issued by trusted issuer
- ✅ Audience matches

#### 3. **Credential Management (Vault)**

```
Secrets stored in HashiCorp Vault:
  ├─ AWS credentials (access key, secret key, role ARN)
  ├─ Azure credentials (client ID, client secret, subscription)
  ├─ GCP service account (JSON key)
  ├─ OCI credentials (private key, tenancy)
  ├─ External API keys (NVIDIA, OpenAI, Slack webhooks)
  └─ Database credentials (connection strings)

Encryption:
  ├─ At rest: AES-256-GCM
  ├─ In transit: TLS 1.3
  └─ Authenticated: HMAC-SHA256

Access Control:
  ├─ Kubernetes Service Account authentication
  ├─ Approle (for CI/CD automation)
  └─ LDAP/SAML (future enterprise tier)

TTL & Rotation:
  ├─ Cloud provider credentials: 30-day rotation
  ├─ API keys: quarterly rotation
  └─ Audit trail: all accesses logged
```

#### 4. **TLS/SSL**

```
HTTPS everywhere:
  ├─ Port 443 with TLS 1.3 (minimum 1.2)
  ├─ HSTS header: max-age=31536000 (1 year)
  ├─ Certificate pinning (optional, for mobile apps)
  └─ Self-signed for local dev, Let's Encrypt for prod

Nginx configuration:
  ssl_protocols TLSv1.3 TLSv1.2;
  ssl_ciphers HIGH:!aNULL:!MD5;
  ssl_prefer_server_ciphers on;
  add_header Strict-Transport-Security "max-age=31536000" always;
```

#### 5. **Input Validation & Sanitization**

```python
# Pydantic schemas enforce validation
from pydantic import BaseModel, Field, validator

class FindingFilter(BaseModel):
    severity: str = Field(..., regex="^(CRITICAL|HIGH|MEDIUM|LOW|INFO)$")
    rule_id: str = Field(..., min_length=1, max_length=255)
    limit: int = Field(default=50, ge=1, le=1000)

# SQL Injection prevention
# ✅ Use parameterized queries
stmt = select(Finding).where(Finding.id == finding_id)

# ❌ Never do this
stmt = f"SELECT * FROM findings WHERE id = '{finding_id}'"  # Vulnerable!
```

#### 6. **CORS & CSRF Protection**

```python
# CORS (restrict allowed origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://cloudvisor.io", "https://app.cloudvisor.io"],
    allow_credentials=True,  # Allow cookies
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-Request-ID"],
    max_age=3600
)

# CSRF (token in cookie + header)
# POST /findings with header: X-CSRF-Token: <token>
# Nginx validates: cookie token == header token
```

#### 7. **Rate Limiting**

```python
# Redis-backed sliding window limiter
RATE_LIMIT = 600  # requests per minute per org/key
WINDOW = 60  # seconds

redis_key = f"ratelimit:{org_id}:{int(time.time() // WINDOW)}"
count = await redis.incr(redis_key)

if count > RATE_LIMIT:
    return Response(status_code=429, headers={
        "X-RateLimit-Limit": "600",
        "X-RateLimit-Remaining": "0",
        "Retry-After": str(int(time.time() // WINDOW) * WINDOW + WINDOW - time.time())
    })
```

#### 8. **Security Headers**

```
X-Content-Type-Options: nosniff
  ↳ Prevents MIME sniffing attacks

X-Frame-Options: DENY
  ↳ Prevents clickjacking (no iframes allowed)

X-XSS-Protection: 1; mode=block
  ↳ Enable browser XSS filter (deprecated but useful fallback)

Referrer-Policy: strict-origin-when-cross-origin
  ↳ Only send referrer to same-origin requests

Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.copilotkit.ai
  ↳ Restrict resources to trusted origins

Permissions-Policy: camera=(), microphone=(), geolocation=()
  ↳ Disable sensitive APIs
```

---

### Vulnerability Risks & Recommendations

| Risk | Severity | Current State | Recommendation |
|------|----------|---------------|-----------------|
| Dependency vulnerabilities | Medium | No automated scanning | Implement Dependabot + GitHub security alerts |
| API key exposure in logs | High | ✅ Sanitized | ✓ Logging filters for secrets |
| Database credentials in .env | High | ⚠️ Partially | Move to Vault, add pre-commit hooks to prevent commits |
| Missing encryption at rest | High | ⚠️ Local dev only | Enable encryption for PostgreSQL (prod) |
| No API request signing | Medium | ✅ JWT provided | ✓ Optional for CI/CD webhooks |
| OWASP Top 10 coverage | High | ⚠️ Partial | Conduct full OWASP audit |
| Audit logging completeness | Medium | ⚠️ Auth only | Extend to all sensitive operations |
| Rate limiting bypass | Medium | ✅ Implemented | Monitor for DDoS patterns |
| Query injection in Rego | Medium | ⚠️ At risk | Validate all input before OPA evaluation |
| Lateral movement (service-to-service) | Medium | ⚠️ Basic JWT | Require service-to-service mutual TLS (mTLS) |

**Key Recommendations:**

1. **Implement mTLS** between all services
   - Use cert-manager in K8s
   - Auto-rotate certificates
   - Enforce mutual authentication

2. **Add Web Application Firewall (WAF)**
   - AWS WAF or similar
   - Block common attack patterns
   - Rate limit per IP

3. **Secrets scanning**
   - Pre-commit hooks (detect AWS keys, API keys)
   - GitHub Actions for PR scanning
   - Vault audit logs

4. **Penetration testing**
   - Annual security audit
   - Red team exercises
   - Bug bounty program

5. **Zero-knowledge architecture (future)**
   - End-to-end encryption for sensitive findings
   - Client-side filtering before transmission

---

## API Documentation

### Base URL & Standards

```
Production: https://api.cloudvisor.io/v1
Development: http://localhost:8080/v1

Authentication:
  Bearer token: Authorization: Bearer <JWT>
  API key: X-API-Key: cv_live_<key>

Response Format (always):
  {
    "data": {...},
    "meta": {
      "request_id": "req_abc123",
      "total": 42,
      "took_ms": 125,
      "cursor": "next_page_token"
    },
    "errors": []  // Empty array if success
  }

Pagination:
  Cursor-based (opaque tokens)
  Query params: ?limit=50&cursor=<token>
  Response includes: meta.cursor for next page

Status Codes:
  200 OK — Success
  201 Created — Resource created
  204 No Content — Success, no response body
  400 Bad Request — Invalid input
  401 Unauthorized — Missing/invalid auth
  403 Forbidden — Insufficient permissions
  404 Not Found — Resource doesn't exist
  429 Too Many Requests — Rate limited
  500 Internal Server Error — Server fault
```

### Core Endpoints

#### 1. Assets

```
GET /v1/assets
  Query params:
    ?limit=50
    &cursor=<opaque_token>
    &filter[provider]=aws,azure
    &filter[resource_type]=ec2::instance
    &filter[status]=ok,warning
    &sort=-risk_score
    &fields[asset]=id,name,risk_score,tags
  
  Response:
  {
    "data": [
      {
        "id": "asset_123",
        "resource_id": "i-1234567890abcdef0",
        "resource_type": "aws::ec2::instance",
        "provider": "aws",
        "account_id": "123456789",
        "region": "us-east-1",
        "name": "production-web-1",
        "tags": {"Environment": "prod", "Owner": "team-a"},
        "risk_score": 78.5,
        "status": "ok",
        "open_findings_count": 3,
        "last_updated": "2025-01-15T10:30:00Z"
      }
    ],
    "meta": {
      "total": 1234,
      "cursor": "next_page_token",
      "took_ms": 145
    }
  }

GET /v1/assets/{id}
  Response:
  {
    "data": {
      "id": "asset_123",
      "...": "...",
      "attack_paths": [
        {
          "path": ["internet", "sg-456", "i-123", "rds-789"],
          "hops": 3,
          "risk": "high"
        }
      ],
      "findings": [
        {
          "id": "finding_abc",
          "severity": "HIGH",
          "title": "..."
        }
      ]
    }
  }

POST /v1/assets/{id}/rescan
  Trigger immediate sync for single asset
  Response: 202 Accepted

PATCH /v1/assets/{id}
  Update tags or metadata
  Request:
  {
    "tags": {"Owner": "team-b"}
  }
  Response: 200 OK (updated asset)
```

#### 2. Findings

```
GET /v1/findings
  Query params:
    ?limit=50
    &filter[severity]=CRITICAL,HIGH
    &filter[status]=open
    &filter[rule_id]=s3-public-access
    &filter[account_id]=prod-123
    &sort=-first_seen_at
    &fields[finding]=id,title,severity,status
  
  Response:
  {
    "data": [
      {
        "id": "finding_789",
        "rule_id": "s3-public-access",
        "resource_id": "my-bucket",
        "resource_type": "aws::s3::bucket",
        "severity": "CRITICAL",
        "status": "open",
        "title": "S3 bucket is publicly readable",
        "description": "...",
        "remediation": "1. Go to S3 console...",
        "first_seen_at": "2025-01-10T08:00:00Z",
        "last_seen_at": "2025-01-15T10:30:00Z",
        "acknowledged_at": null,
        "compliance_mapping": [
          {"framework": "CIS AWS", "control": "2.1.5"}
        ]
      }
    ],
    "meta": {"total": 42, "cursor": "...", "took_ms": 230}
  }

GET /v1/findings/{id}
  Response: 200 OK (full finding detail)

PATCH /v1/findings/{id}
  Request:
  {
    "status": "in_progress",
    "assignee_id": "user_123"
  }
  Response: 200 OK (updated finding)

POST /v1/findings/{id}/acknowledge
  Mark as acknowledged (SLA tracking)
  Response: 200 OK

POST /v1/findings/{id}/suppress
  Request:
  {
    "reason": "False positive - configured intentionally",
    "expires_at": "2025-02-15T00:00:00Z"
  }
  Response: 200 OK

POST /v1/findings/{id}/accept-risk
  Request:
  {
    "justification": "Acceptable risk for dev environment",
    "expires_at": "2025-06-15T00:00:00Z"
  }
  Response: 200 OK

POST /v1/findings/bulk
  Bulk update findings
  Request:
  {
    "finding_ids": ["finding_1", "finding_2", "finding_3"],
    "status": "resolved"
  }
  Response: 200 OK {updated_count: 3}
```

#### 3. Compliance

```
GET /v1/compliance
  Response:
  {
    "data": {
      "frameworks": [
        {
          "name": "CIS AWS",
          "score": 82,  // percentage
          "controls_total": 131,
          "controls_passing": 107,
          "controls_failing": 24,
          "last_evaluated": "2025-01-15T10:00:00Z",
          "domains": [
            {
              "name": "Identity and Access Management",
              "score": 75,
              "controls": [
                {
                  "id": "CIS AWS 1.1",
                  "description": "Avoid the use of root account",
                  "status": "pass",  // pass, fail, not_applicable
                  "failing_resources": []
                }
              ]
            }
          ]
        }
      ]
    }
  }

GET /v1/compliance/{framework}/controls/{control_id}
  Response: 200 OK (control details + failing resources)
```

#### 4. Copilot

```
POST /v1/copilot/query
  Request:
  {
    "query": "Which production workloads are internet-facing?",
    "stream": true
  }
  
  Response (streaming):
  ```
  data: {"content": "I found", "type": "text_delta"}
  data: {"content": " 3 production workloads", "type": "text_delta"}
  data: {"content": " exposed to the internet:", "type": "text_delta"}
  data: {"type": "message_stop"}
  ```
  
  Or non-streaming (stream=false):
  {
    "data": {
      "response": "I found 3 production workloads...",
      "citations": [
        {"source": "finding_123", "text": "..."}
      ],
      "tokens_used": 324
    }
  }

GET /v1/copilot/history
  Get user's query history
  Response:
  {
    "data": [
      {
        "id": "query_123",
        "query": "...",
        "created_at": "2025-01-15T10:30:00Z",
        "response": "..."
      }
    ]
  }
```

#### 5. Accounts

```
GET /v1/accounts
  List connected cloud accounts
  Response:
  {
    "data": [
      {
        "id": "account_123",
        "provider": "aws",
        "account_name": "production",
        "account_id": "123456789",
        "last_sync_at": "2025-01-15T10:00:00Z",
        "sync_status": "healthy",  // healthy, warning, error
        "sync_error": null,
        "asset_count": 1234
      }
    ]
  }

POST /v1/accounts
  Register new cloud account
  Request:
  {
    "provider": "aws",
    "account_name": "staging",
    "assume_role_arn": "arn:aws:iam::987654321:role/CloudVisor"
  }
  Response: 201 Created (new account)

POST /v1/accounts/{id}/sync
  Trigger manual sync
  Response: 202 Accepted

GET /v1/accounts/{id}/health
  Check sync health
  Response: 200 OK {status: "healthy", last_sync: "..."}
```

#### 6. GraphQL

```
POST /graphql
  Request:
  {
    "query": "query GetAssets($orgId: String!) {
      assets(orgId: $orgId, limit: 10) {
        id
        resourceId
        resourceType
        riskScore
        findings {
          id
          severity
          status
        }
      }
    }",
    "variables": {
      "orgId": "org_456"
    }
  }
  
  Response:
  {
    "data": {
      "assets": [
        {
          "id": "asset_123",
          "resourceId": "i-123",
          "resourceType": "aws::ec2::instance",
          "riskScore": 78.5,
          "findings": [...]
        }
      ]
    }
  }
```

---

## AI/ML Components

### AI Copilot (CloudVisor Q)

**Technology:** Claude 3 Sonnet (Anthropic) + RAG

**Pipeline:**

1. **Intent Classification**
   - POSTURE: "Show me my risk score", "Which resources are at risk?"
   - FINDING: "Explain this alert", "Why is this critical?"
   - COMPLIANCE: "What's my CIS AWS score?", "Show failing controls"
   - REMEDIATION: "How do I fix this?", "Generate remediation code"
   - THREAT: "Was I breached?", "Show attack paths"
   - DRIFT: "What changed?", "Show deployment diffs"

2. **Multi-Source Retrieval**
   - Neo4j: Asset graph queries (MATCH ... RETURN)
   - Elasticsearch: Full-text finding search
   - PostgreSQL: Compliance controls, audit events
   - CIEM Service: Permission data, role analysis
   - CWPP Service: Vulnerability data, CVEs
   - CDR Service: Threat events, incident history

3. **Prompt Construction**
   ```
   You are CloudVisor Q, a security assistant. 
   
   CONTEXT:
   [Retrieved data from 6 sources]
   
   USER QUERY:
   [User's natural language question]
   
   Answer based ONLY on the provided context.
   Cite your sources with [source: id] format.
   ```

4. **Claude API Call**
   - Model: claude-3-sonnet-4-20250514
   - Max tokens: 1024
   - Temperature: 0.7 (balanced creativity/accuracy)
   - Streaming: Real-time text chunks (SSE)

5. **Audit Logging**
   - Every query logged to copilot_queries table
   - Includes: query, intent, sources, response, tokens_used
   - Accessible to security team (audit transparency)

---

### AI Router (LLM Gateway)

**Purpose:** Unified interface for multiple LLM providers

**Providers:**

- **OpenAI** — GPT-4o, GPT-4-turbo, GPT-3.5-turbo (production standard)
- **OpenRouter** — Llama 3.3, Claude 3.5, Gemini Pro, Mistral (cost-effective)
- **NVIDIA NIM** — Llama 3.1 (8B/70B), Mistral, Gemma 2 (on-prem option)

**Routing Logic:**

```python
async def route_request(provider: str, model: str, prompt: str):
    # If provider specified, use it
    if provider:
        return await call_provider(provider, model, prompt)
    
    # Otherwise, use default with fallback chain
    providers = [
        ('openai', 'gpt-4o'),
        ('openrouter', 'gpt-4o'),
        ('nvidia', 'llama-3.1-70b'),
    ]
    
    for prov, mdl in providers:
        try:
            return await call_provider(prov, mdl, prompt)
        except Exception as e:
            logger.warn(f"{prov} failed: {e}, trying next...")
            continue
    
    raise Exception("All LLM providers failed")
```

**Features:**

- ✅ Automatic failover
- ✅ Rate limiting per tenant
- ✅ Response caching (Redis)
- ✅ Cost tracking per provider
- ✅ Health monitoring
- ✅ Streaming support (SSE)

---

## Code Quality & Engineering Practices

### Coding Standards

**Python:**

```python
# Style: PEP 8 + Black formatter
# Type hints: Full coverage (mypy)
# Docstrings: Google-style

def find_findings_by_severity(
    org_id: str,
    severity: str,
    limit: int = 50
) -> List[Finding]:
    """
    Retrieve findings filtered by severity.
    
    Args:
        org_id: Organization ID (UUID string)
        severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW, INFO)
        limit: Max number of results (1-1000, default 50)
    
    Returns:
        List of Finding objects sorted by first_seen_at (DESC)
    
    Raises:
        ValueError: If severity not in allowed values
        NotFoundException: If org_id doesn't exist
    """
    if severity not in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
        raise ValueError(f"Invalid severity: {severity}")
    
    stmt = select(FindingModel).where(
        (FindingModel.organization_id == org_id) &
        (FindingModel.severity == severity)
    ).order_by(
        FindingModel.first_seen_at.desc()
    ).limit(limit)
    
    results = await session.execute(stmt)
    return results.scalars().all()
```

**TypeScript/React:**

```typescript
// Strict mode enabled
// Type strict: true
// ESLint + Prettier

interface Finding {
  id: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  title: string;
  status: 'open' | 'in_progress' | 'resolved';
}

export const FindingCard: React.FC<{finding: Finding}> = ({finding}) => {
  return (
    <Card className={`border-l-4 border-${finding.severity.toLowerCase()}`}>
      <h3>{finding.title}</h3>
      <p>Severity: {finding.severity}</p>
    </Card>
  );
};
```

### Reusability Patterns

**Repository Pattern (Data Access):**

```python
# Generic base class
class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model_class: Type[T]):
        self.session = session
        self.model_class = model_class
    
    async def find_by_id(self, id: str) -> T:
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one()
    
    async def find_all(self, limit: int = 50) -> List[T]:
        stmt = select(self.model_class).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

# Inheritance
class FindingRepository(BaseRepository[FindingModel]):
    async def find_by_severity(self, org_id: str, severity: str) -> List[FindingModel]:
        stmt = select(self.model_class).where(
            (self.model_class.organization_id == org_id) &
            (self.model_class.severity == severity)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

**Service Layer (Business Logic):**

```python
class FindingService:
    def __init__(self, repo: FindingRepository, graph_service: GraphService):
        self.repo = repo
        self.graph_service = graph_service
    
    async def create_finding(self, org_id: str, data: RawFinding) -> Finding:
        # Compute fingerprint
        fingerprint = self._compute_fingerprint(data)
        
        # Check for duplicates
        existing = await self.repo.find_by_fingerprint(fingerprint)
        if existing:
            # Update existing
            return await self._update_finding(existing, data)
        
        # Create new
        finding = await self.repo.create(Finding(
            organization_id=org_id,
            fingerprint=fingerprint,
            **data
        ))
        
        # Enrich with graph context
        enriched = await self.graph_service.enrich_finding(finding)
        
        # Publish event
        await self.producer.send('finding.created', enriched.dict())
        
        return enriched
```

### Technical Debt Identified

| Item | Impact | Effort | Priority |
|------|--------|--------|----------|
| No integration tests | High | High | 🔴 High |
| Missing OpenTelemetry in all services | Medium | Medium | 🟡 Medium |
| Duplicate code in notification handlers | Low | Low | 🟢 Low |
| No E2E tests for critical flows | High | High | 🔴 High |
| Rego rule testing framework missing | Medium | Medium | 🟡 Medium |
| Frontend component library not documented | Low | Medium | 🟢 Low |
| Legacy BASIC auth in Keep (AIOps) | High | Low | 🔴 High |

### Performance Bottlenecks

| Bottleneck | Root Cause | Impact | Fix |
|------------|-----------|--------|-----|
| Graph queries slow (>5s) | No query caching | P95 latency spike | Add Redis cache for common queries |
| Finding ingestion (>10 findings/sec) | Sequential processing | High latency | Batch processing + async |
| Asset discovery sync | Sequential cloud API calls | 30min+ for large orgs | Parallel API calls (threadpool) |
| ES indexing lag | Synchronous indexing | 2-3sec delay | Async indexing via queue |
| PostgreSQL connection pool exhaustion | Insufficient pooling | Service errors | Increase pool size to 30 |

### Scalability Concerns

| Concern | Current Limit | Production Target | Solution |
|---------|---------------|-------------------|----------|
| Finding ingestion | 100 findings/sec | 10,000 findings/sec | Kafka partitioning, batch processing |
| Asset graph size | 1M nodes | 100M nodes | Neo4j enterprise clustering |
| Dashboard response time | P95 < 500ms | P95 < 200ms | Caching layer, query optimization |
| Concurrent users | 100 | 10,000 | K8s autoscaling, load balancing |
| Storage growth | 500GB/year | 50TB/year | Data archival, partitioning |

---

## Setup & Development Guide

### Prerequisites

- **Docker** 20.10+ with Docker Compose 2.0+
- **Node.js** 18.x (for frontend)
- **Python** 3.12 (for backend development)
- **Git**
- **curl** / **Postman** (API testing)

### Installation & Local Setup

#### Step 1: Clone Repository

```bash
git clone https://github.com/cloudvisor/cloudvisor.git
cd cloudvisor
```

#### Step 2: Configure Environment

```bash
cp .env.example .env

# Edit .env with your values
# IMPORTANT: Change all default passwords
POSTGRES_PASSWORD=your-secure-password-here
NEO4J_PASSWORD=your-secure-password-here
ELASTIC_PASSWORD=your-secure-password-here
COPILOT_NVIDIA_API_KEY=nvapi-xxxxx  # Get from https://build.nvidia.com/
```

#### Step 3: Start Services

```bash
# Build all services (first time only)
docker-compose build

# Start all services
docker-compose up -d

# Wait for all services to be healthy (30-60 seconds)
docker-compose logs -f

# Verify all services are running
docker-compose ps
```

**Expected output:**

```
NAME                   STATUS      PORTS
cv-nginx              Up (healthy) 0.0.0.0:8080
cv-postgres           Up (healthy) 0.0.0.0:5432
cv-neo4j              Up (healthy) 0.0.0.0:7687
cv-elasticsearch      Up (healthy) 0.0.0.0:9200
cv-kafka              Up (healthy) 0.0.0.0:9092
cv-redis              Up (healthy) 0.0.0.0:6379
cv-opa                Up (healthy) 0.0.0.0:8181
cv-vault              Up (healthy) 0.0.0.0:8200
cv-auth               Up (healthy) 0.0.0.0:8002
cv-connector          Up (healthy) 0.0.0.0:8000
cv-graph              Up (healthy) 0.0.0.0:8001
cv-policy             Up (healthy) 0.0.0.0:8003
cv-alert              Up (healthy) 0.0.0.0:8004
cv-api                Up (healthy) 0.0.0.0:8005
cv-cspm               Up (healthy) 0.0.0.0:8006
cv-copilot            Up (healthy) 0.0.0.0:8010
cv-ai-router          Up (healthy) 0.0.0.0:8015
cv-keep               Up (healthy) 0.0.0.0:8007
cv-web                Up (healthy) 0.0.0.0:3000
cv-soketi             Up (healthy) 0.0.0.0:6001
```

#### Step 4: Verify Installation

```bash
# Check health endpoint
curl http://localhost:8080/auth/health
# Expected: {"status": "healthy", "service": "auth"}

# Check API docs
open http://localhost:8080/v1/docs
# Swagger UI at localhost:8080/v1/docs

# Open dashboard
open http://localhost:8080
# Login with: admin@cloudvisor.io / AdminPass123!
```

#### Step 5: Create First Cloud Account

```bash
# Via API
curl -X POST http://localhost:8080/internal/accounts \
  -H "Authorization: Bearer $(curl -s http://localhost:8080/auth/login -d '{"email":"admin@cloudvisor.io","password":"AdminPass123!"}' | jq -r '.access_token')" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws",
    "account_name": "dev",
    "assume_role_arn": "arn:aws:iam::123456789:role/CloudVisor"
  }'

# Or via dashboard:
# Settings → Add Cloud Account → AWS → Paste IAM role ARN
```

---

### Backend Development

#### Running Services Individually

```bash
# Terminal 1: Auth service
cd services/auth
pip install -r requirements.txt
python main.py
# Service running at http://localhost:8002

# Terminal 2: API service
cd services/api
pip install -r requirements.txt
python main.py
# Service running at http://localhost:8005

# Terminal 3: Connector service
cd services/connector
pip install -r requirements.txt
python main.py
# Service running at http://localhost:8000
```

#### Database Migrations

```bash
# List migrations
alembic current

# Create new migration
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

#### Interactive Development

```bash
# Use FastAPI's automatic reload
uvicorn app.main:app --reload --port 8002

# Logs will show on code change
```

---

### Frontend Development

#### Running React App

```bash
cd apps/web

# Install dependencies
npm install

# Start development server (with hot reload)
npm run dev

# Open browser
open http://localhost:3000
```

#### Build for production

```bash
npm run build

# Test production build
npm run start
```

---

### Testing

#### Backend Tests

```bash
# Run all backend tests
docker-compose exec auth pytest tests/ -v

# Run specific test
docker-compose exec auth pytest tests/test_auth.py::test_login -v

# With coverage
docker-compose exec auth pytest --cov=app tests/

# Report
docker-compose exec auth coverage html  # Opens coverage/index.html
```

#### Frontend Tests

```bash
cd apps/web

# Run all tests
npm test

# With coverage
npm test -- --coverage

# E2E tests (Playwright)
npm run test:e2e
```

---

## Testing & QA

### Test Structure

```
services/[service]/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Fixtures (DB, Redis, etc.)
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_schemas.py
│   │   └── test_services.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   ├── test_kafka_consumers.py
│   │   └── test_database_queries.py
│   └── e2e/
│       └── test_critical_flows.py

apps/web/
├── __tests__/
│   ├── components/
│   │   └── Badge.test.tsx
│   ├── pages/
│   │   └── dashboard.test.tsx
│   └── hooks/
│       └── useFindings.test.ts
```

### Test Frameworks

| Component | Framework | Purpose |
|-----------|-----------|---------|
| Backend unit | pytest | Test individual functions |
| Backend integration | pytest + containers | Test services with real DB/Kafka |
| Backend API | pytest + FastAPI TestClient | Test HTTP endpoints |
| Frontend unit | Vitest | Test React components |
| Frontend E2E | Playwright | Test user workflows |

### Test Examples

#### Unit Test (Auth Service)

```python
# services/auth/tests/unit/test_auth_service.py
import pytest
from passlib.context import CryptContext

@pytest.fixture
def auth_service():
    return AuthService()

def test_password_hashing(auth_service):
    # Arrange
    password = "TestPassword123!"
    
    # Act
    hashed = auth_service.hash_password(password)
    is_valid = auth_service.verify_password(password, hashed)
    
    # Assert
    assert is_valid is True
    assert hashed != password  # Never stored as plain text
    assert auth_service.verify_password("WrongPassword", hashed) is False
```

#### Integration Test (Finding Ingestion)

```python
# services/alert/tests/integration/test_finding_ingestion.py
@pytest.mark.asyncio
async def test_finding_deduplication(db_session, kafka_producer):
    # Arrange: Create two identical findings
    finding1 = RawFinding(
        rule_id="s3-public",
        resource_id="bucket-1",
        severity="HIGH"
    )
    finding2 = RawFinding(
        rule_id="s3-public",
        resource_id="bucket-1",
        severity="HIGH"
    )
    
    # Act: Ingest both
    await ingest_finding(db_session, finding1)
    result = await ingest_finding(db_session, finding2)
    
    # Assert: Second should be duplicate
    assert result.is_duplicate is True
    assert result.regression_count == 1
```

#### E2E Test (Critical Flow)

```python
# tests/e2e/test_add_cloud_account.py
@pytest.mark.asyncio
async def test_add_aws_account_end_to_end(client, admin_token):
    """
    Test complete flow:
    1. Add AWS account
    2. Start discovery
    3. Verify assets appear in dashboard
    """
    # Step 1: Add account
    response = await client.post(
        "/v1/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "provider": "aws",
            "account_name": "test-account",
            "assume_role_arn": "arn:aws:iam::123456789:role/CloudVisor"
        }
    )
    assert response.status_code == 201
    account_id = response.json()["data"]["id"]
    
    # Step 2: Trigger sync
    response = await client.post(
        f"/v1/accounts/{account_id}/sync",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 202
    
    # Step 3: Wait for discovery and verify
    await asyncio.sleep(5)  # Wait for async processing
    response = await client.get(
        f"/v1/accounts/{account_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()["data"]
    assert data["asset_count"] > 0
    assert data["sync_status"] == "healthy"
```

### Coverage Goals

- **Backend:** Minimum 70% unit + integration test coverage
- **Frontend:** Minimum 60% component test coverage
- **Critical paths:** 100% coverage (auth, finding ingestion, policy eval)

### Current Coverage Status

```
Backend:
  services/auth: 82% ✅
  services/api: 75% ✅
  services/alert: 68% ⚠️
  services/connector: 45% ❌
  services/graph: 52% ⚠️
  services/policy: 38% ❌
  services/copilot: 55% ⚠️

Frontend:
  components: 70% ✅
  pages: 45% ⚠️
  hooks: 60% ⚠️

Overall: 58% (Target: 70%)
```

---

## Improvement Recommendations

### Short-term (1-2 months)

1. **Complete Test Coverage**
   - Add integration tests for all Kafka consumers
   - Add E2E tests for critical user journeys
   - Target: 70% overall coverage
   - Effort: 80 hours

2. **Fix Security Vulnerabilities**
   - Implement mTLS between services
   - Move all secrets to Vault
   - Add WAF rules
   - Effort: 40 hours

3. **Performance Optimization**
   - Add caching layer (Redis) for common queries
   - Batch process asset discovery
   - Optimize Neo4j queries
   - Effort: 60 hours

4. **Documentation**
   - API documentation (OpenAPI/Swagger)
   - Architecture decision records (ADRs)
   - Runbooks for common operations
   - Effort: 30 hours

### Medium-term (3-6 months)

1. **Multi-Region Support**
   - Replicate infrastructure across regions
   - Database replication + failover
   - Effort: 120 hours

2. **Enhanced RBAC**
   - Resource-level permissions (accounts, regions, tags)
   - Custom role creation
   - Permission inheritance
   - Effort: 60 hours

3. **Advanced Reporting**
   - PDF report generation
   - Scheduled email reports
   - Executive dashboard
   - Effort: 80 hours

4. **Webhook Integrations**
   - Generic webhook API
   - Signature verification (HMAC-SHA256)
   - Retry logic + dead letter queue
   - Effort: 40 hours

### Long-term (6-12 months)

1. **ML-Based Risk Scoring**
   - Anomaly detection for finding patterns
   - Predictive severity classification
   - Attack surface prediction
   - Effort: 200 hours

2. **Automated Remediation**
   - Safe remediation workflows
   - Approval + audit trail
   - Rollback capability
   - Effort: 150 hours

3. **Industry Expansion**
   - Add support for additional cloud providers (Alibaba, IBM)
   - Kubernetes-native security module (KSPM)
   - Serverless security (Lambda, Cloud Functions, Functions)
   - Effort: 300 hours

4. **Enterprise Features**
   - Multi-tenant isolation (current: shared infrastructure)
   - Dedicated hardware + VPC
   - SLA guarantees (99.95% uptime)
   - Effort: 200 hours

---

### Roadmap (Next 24 Months)

```
Q1 2025
├─ [IN PROGRESS] Complete CSPM foundation
├─ [IN PROGRESS] Deploy AI Copilot (MVP)
├─ [TODO] 70% test coverage
├─ [TODO] mTLS between services
└─ [TODO] Performance baseline (P95 latency)

Q2 2025
├─ [TODO] CWPP (Cloud Workload Protection)
├─ [TODO] CI/CD Security Module
├─ [TODO] Multi-region support
└─ [TODO] Advanced compliance reporting

Q3 2025
├─ [TODO] CIEM (Cloud Infrastructure Entitlements)
├─ [TODO] KSPM (Kubernetes Security)
├─ [TODO] Automated remediation (beta)
└─ [TODO] Enterprise RBAC

Q4 2025
├─ [TODO] CDR (Detection & Response)
├─ [TODO] DSPM (Data Security Posture)
├─ [TODO] ML-based risk scoring
└─ [TODO] Production SLA (99.95%)

2026
├─ Additional cloud providers
├─ Industry-specific modules (PCI-DSS, HIPAA, etc.)
├─ AI-powered incident response automation
└─ IP rating 9.5+ (industry leader)
```

---

### Known Limitations & Workarounds

| Limitation | Impact | Workaround |
|------------|--------|-----------|
| Single Neo4j instance (no clustering) | 10M asset limit | Deploy Neo4j Enterprise cluster |
| No read replicas for PostgreSQL | Single point of failure | Add standby replicas + automated failover |
| Kafka retention 7 days | Cannot replay old events | Archive to S3, implement event replay from backups |
| No data encryption at rest (dev only) | Data exposure risk | Enable PostgreSQL encryption in production |
| Keep service uses basic auth | Security risk | Migrate to service-to-service JWT authentication |
| Frontend not cached by CDN | Slow global load times | Deploy to CDN (CloudFront, CloudFlare) |
| No request signing for webhooks (optional) | Security risk | Implement HMAC-SHA256 signature verification |

---

## Summary

CloudVisor is an enterprise-grade CNAPP platform built with:

- **Scalable microservices** (FastAPI + Python 3.12)
- **Multi-cloud support** (AWS, Azure, GCP, OCI)
- **Real-time threat detection** (Policy Engine + OPA)
- **AI-powered assistance** (Claude + RAG)
- **Multi-tenant architecture** (PostgreSQL RLS)
- **Event-driven processing** (Kafka message bus)
- **Production-ready infrastructure** (Docker/K8s)

**Key strengths:**
✅ Comprehensive cloud security coverage  
✅ Scalable event-driven architecture  
✅ Strong authentication & RBAC  
✅ Real-time finding ingestion & deduplication  
✅ AI Copilot for security intelligence  

**Areas for improvement:**
⚠️ Test coverage (58% → target 70%)  
⚠️ Performance optimization needed  
⚠️ Security hardening (mTLS, encryption at rest)  
⚠️ Documentation gaps  

**Next 90 days:**
1. Increase test coverage to 70%
2. Implement mTLS between services
3. Add performance optimizations
4. Complete security audit

---

**End of Technical Documentation**

*Generated for: CloudVisor Development Team*  
*Date: January 2025*  
*Version: 2.0*  
*Scope: Complete platform analysis*
