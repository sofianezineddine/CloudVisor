# CloudVisor CNAPP Platform — Master Engineering Prompt
> **Version:** 2.0
> **Purpose:** This document is the single authoritative engineering brief for the CloudVisor
> platform. It must be read in full before writing any code. Every architectural decision,
> service role, data model, API contract, event schema, and build priority defined here
> is binding. Do not deviate without explicit instruction.

---

## 0. How to Use This Document

This prompt is designed to be given to an LLM coding assistant at the start of every
session. It provides complete context so the assistant never needs to guess about
intent, architecture, or priority.

**Before writing any code, the assistant must:**
1. Read all sections of this document
2. Identify which service or module is being asked to implement
3. Locate the detailed spec for that service in Section 3 (foundational) or Section 4 (modules)
4. Follow the build order in Section 9
5. Apply all coding rules from Section 10

**Every service spec in this document answers:**
- What is the role of this service? (its reason for existence)
- What specific tasks does it perform? (exhaustive list)
- What data does it consume and produce? (Kafka events, DB reads/writes)
- What APIs does it expose? (endpoints, request/response shapes)
- How does it interact with other services?
- How does it handle failures?
- What are its performance targets?

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Platform name** | CloudVisor |
| **Type** | Cloud-Native Application Protection Platform (CNAPP) |
| **Tagline** | Unified cloud security — from code to runtime |
| **Backend language** | Python (all services) |
| **Frontend** | React 18 + TypeScript |
| **Target users** | Security engineers, DevOps teams, SOC analysts, CISOs, compliance officers |
| **Deployment models** | SaaS (multi-tenant), single-tenant cloud, on-premises (Helm chart / appliance) |
| **Cloud targets** | AWS, Microsoft Azure, Google Cloud Platform (GCP), Oracle Cloud Infrastructure (OCI) |

CloudVisor is a modular, API-first security platform. Every module must function as a
standalone product AND integrate seamlessly into the unified platform. The platform is
built mobile-first, dark-mode-ready, and fully accessible (WCAG 2.1 AA).

---

## 2. Architecture Principles (Non-Negotiable)

These are hard constraints. Every line of code must comply.

### 2.1 Core rules

- **API-first:** Every feature must be reachable via REST or GraphQL API before any UI
  is built. The UI is a consumer of the API, not a shortcut around it.

- **Multi-tenant from day one:** All data rows are scoped to `organization_id`.
  Tenant isolation is enforced at the database layer using PostgreSQL Row-Level Security
  (RLS), not in application code. Never trust the application layer alone for isolation.

- **Modular monorepo:** All services live in a single monorepo managed by Turborepo.
  Shared code lives in `packages/` only. Services never import from each other directly.

- **Event-driven core:** All inter-service communication for async work goes through
  Apache Kafka. No direct HTTP calls between services for anything asynchronous.
  Synchronous reads (e.g., auth token validation) may use internal HTTP with mTLS.

- **Graph-first data model:** Cloud resources and their relationships live in Neo4j.
  Transactional and user data live in PostgreSQL. Never store resource relationships
  in a relational table — that belongs in the graph.

- **Policy-as-code:** Every security evaluation rule is a Rego policy stored in Git
  under `/rules/rego/`. No security logic is hardcoded in Python. The OPA engine is
  the only place rules are evaluated.

- **Zero-trust internally:** All inter-service HTTP communication uses mutual TLS (mTLS).
  Every service verifies the identity of the caller. No service is trusted by position alone.

- **Observability built-in:** Every service emits structured JSON logs (to stdout),
  Prometheus metrics (on `/metrics`), and OpenTelemetry traces from the first commit.
  Observability is not added later — it is part of the service definition.

### 2.2 Technology stack

| Layer | Technology |
|---|---|
| Backend services | Python 3.12 (FastAPI for HTTP, Faust/Confluent for Kafka consumers) |
| Frontend | React 18, TypeScript, Tailwind CSS, React Query v5, Recharts, Next.js 14 |
| Graph database | Neo4j 5.x (Community or Enterprise) |
| Relational DB | PostgreSQL 15 with Row-Level Security (RLS) |
| Cache / queues | Redis 7 (cache, rate limiting, distributed locks) |
| Message broker | Apache Kafka 3.x (Confluent Schema Registry for Avro schemas) |
| Search | Elasticsearch 8.x (synced from Neo4j via Kafka) |
| Policy engine | Open Policy Agent (OPA) 0.60+ with Rego v1 |
| Container runtime | Kubernetes 1.28+ |
| Infrastructure-as-Code | Terraform 1.6+ |
| Auth | Keycloak 23+ (OIDC, SAML 2.0, social login) |
| API gateway | Kong Gateway 3.x |
| ML / AIOps | Python: scikit-learn, PyTorch, LangChain, Anthropic Claude API |
| Observability | Prometheus + Grafana, OpenTelemetry Collector, Loki (logs) |
| CI/CD | GitHub Actions |
| Container scanning | Trivy |
| SAST | Semgrep |
| Secrets scanning | TruffleHog |

### 2.3 Monorepo structure

```
cloudvisor/
├── apps/
│   ├── web/                  # Next.js 14 frontend application
│   ├── api-gateway/          # Kong Gateway configuration + custom plugins
│   └── docs/                 # Docusaurus developer documentation portal
│
├── services/                 # All backend microservices (Python / FastAPI)
│   ├── connector/            # [Foundation 1] Cloud connector & asset ingestion
│   ├── graph/                # [Foundation 2] Asset graph service (Neo4j)
│   ├── auth/                 # [Foundation 3] Authentication & RBAC
│   ├── policy/               # [Foundation 4] OPA policy engine service
│   ├── alert/                # [Foundation 5] Alert pipeline & notifications
│   ├── api/                  # [Foundation 6] Public REST + GraphQL API
│   ├── cspm/                 # [Module 1] Cloud Security Posture Management
│   ├── cwpp/                 # [Module 2] Cloud Workload Protection Platform
│   ├── cicd/                 # [Module 3] CI/CD pipeline security
│   ├── ciem/                 # [Module 4] Cloud Infrastructure Entitlement Mgmt
│   ├── kspm/                 # [Module 5] Kubernetes Security Posture Mgmt
│   ├── dspm/                 # [Module 6] Data Security Posture Management
│   ├── cdr/                  # [Module 7] Cloud Detection & Response
│   ├── aiops/                # [Module 8a] AIOps ML intelligence layer
│   └── copilot/              # [Module 8b] LLM security copilot (RAG)
│
├── packages/                 # Shared code (no service imports another service)
│   ├── types/                # Shared Python dataclasses + TypeScript interfaces
│   ├── ui/                   # Shared React component library (Storybook)
│   ├── sdk-python/           # Public Python SDK (pip install cloudvisor)
│   ├── kafka-schemas/        # Avro schemas for all Kafka topics (shared)
│   └── utils/                # Shared Python utilities (logging, tracing, auth middleware)
│
├── infra/
│   ├── terraform/            # All cloud infrastructure (modular, per-environment)
│   ├── helm/                 # Helm charts for Kubernetes deployment
│   └── docker/               # Dockerfiles (one per service)
│
└── rules/
    └── rego/                 # All OPA/Rego policy rules (Git-backed, version-controlled)
        ├── cspm/             # CSPM rules (aws/, azure/, gcp/, oci/)
        ├── kspm/             # Kubernetes rules
        ├── iac/              # IaC scanning rules (terraform/, helm/, cloudformation/)
        ├── cicd/             # CI/CD pipeline rules
        ├── cdr/              # CDR detection rules
        └── custom/           # Customer-authored custom rules (per-org namespace)
```

### 2.4 Standard service structure (every service must follow this layout)

```
services/<service-name>/
├── main.py                   # Entry point
├── app/
│   ├── api/                  # FastAPI routers (one file per resource group)
│   ├── consumers/            # Kafka consumer definitions
│   ├── producers/            # Kafka producer helpers
│   ├── models/               # SQLAlchemy models (PostgreSQL)
│   ├── schemas/              # Pydantic schemas (request/response validation)
│   ├── services/             # Business logic layer (no DB or HTTP here)
│   ├── repositories/         # DB access layer (queries only, no logic)
│   └── core/                 # Config, dependencies, startup/shutdown hooks
├── tests/
│   ├── unit/                 # Unit tests (pytest, mock all I/O)
│   └── integration/          # Integration tests (Docker Compose, real DB + Kafka)
├── Dockerfile
├── requirements.txt
└── README.md                 # Service-specific README: purpose, setup, env vars
```

---

## 3. Foundational Services

These 6 services are the non-negotiable prerequisites for every security module.
They must be built, tested, documented, and deployed before any module work begins.
Every module depends on all 6 of these services.

Build them in the order listed. There are dependency relationships:
- Service 2 (Graph) depends on Service 1 (Connector) producing Kafka events
- Service 4 (Policy) depends on Service 2 (Graph) for resource data
- Service 5 (Alert) depends on Service 4 (Policy) producing findings
- Service 6 (API) depends on all 5 preceding services being operational

---

### 3.1 — Service 1: Cloud Connector & Asset Ingestion

#### Role

The Cloud Connector is the data acquisition layer of CloudVisor. It is responsible
for establishing and maintaining read-only connections to customer cloud accounts
across AWS, Azure, GCP, and OCI, and continuously ingesting the complete inventory
of cloud resources into the platform.

This service is the origin of all data in CloudVisor. Without it, no other service
has anything to scan, analyze, or display. It acts as a translation layer that
normalizes the wildly different APIs and resource models of four cloud providers
into a single, consistent Common Data Model (CDM) that the rest of the platform uses.

Every other service treats the cloud provider APIs as opaque. Only the Connector
ever calls AWS, Azure, GCP, or OCI APIs. This is a strict boundary.

#### Tasks this service performs

**Connection management:**
- Accept cloud account connection requests from the API (provider type, credentials/role ARN)
- For AWS: generate and validate a CloudFormation template that creates a read-only
  IAM role with `sts:AssumeRole` trust policy targeting the CloudVisor AWS account
- For Azure: guide users through creating a service principal with Reader role
  across the target subscription or Management Group
- For GCP: guide users through creating a service account with Viewer role
  and downloading the JSON key file
- For OCI: guide users through creating an API signing key and setting up
  a cross-tenancy policy for read-only access
- Store encrypted credentials in HashiCorp Vault (never in PostgreSQL directly)
- Validate connectivity on first connection by performing a test API call
- Track connector health: last successful sync, consecutive error count, resource count

**Full resource discovery (initial sync):**
- On first connection, perform a comprehensive scan of all resources in the account
- Enumerate all supported resource types (see full list below)
- Map each discovered resource to the CDM schema
- Publish each resource as a `resource.discovered` Kafka event
- Track sync progress so restarts resume rather than restart from scratch
- Support concurrent discovery across multiple regions in parallel (async)

**Continuous incremental sync:**
- Schedule incremental polling every 15 minutes (configurable per account: 5 / 15 / 30 / 60 min)
- For each poll cycle: fetch only changed resources (use API change tokens where available)
- Compare new resource state against last known state (stored in Redis cache)
- Publish `resource.updated` event only when state actually differs (avoid noise)
- Publish `resource.deleted` event when a resource disappears from the cloud account

**Real-time event ingestion:**
- Subscribe to real-time change streams for near-instant updates:
  - AWS: CloudTrail → S3/SQS → Connector consumer
  - Azure: Azure Event Hub (resource change events via Azure Monitor)
  - GCP: GCP Pub/Sub (Cloud Asset Inventory feeds)
  - OCI: OCI Events Service
- Parse incoming events, identify the affected resource, fetch its current state
- Publish the appropriate Kafka event (`resource.updated` or `resource.deleted`)
- Target latency: resource change reflected in CloudVisor asset graph within 60 seconds

**Resource normalization:**
- Map every cloud provider resource type to the CDM schema (see schema below)
- Preserve the full raw API response in the `raw` field (stored as JSONB in PostgreSQL)
- Normalize tags/labels across providers (AWS tags, Azure tags, GCP labels → unified `tags` map)
- Infer missing fields where possible (e.g., derive `environment` tag from name patterns)
- Flag resources with missing required fields rather than silently dropping them

**Supported resource types (must cover all of these):**
```
AWS:   EC2 instances, Security Groups, VPCs, Subnets, S3 Buckets, IAM Users,
       IAM Roles, IAM Policies, RDS Instances, Lambda Functions, EKS Clusters,
       ECS Tasks, CloudFront Distributions, Route53 Hosted Zones, KMS Keys,
       CloudTrail Trails, Config Rules, SNS Topics, SQS Queues, DynamoDB Tables,
       ElastiCache Clusters, ALB/NLB/CLB, API Gateways, Secrets Manager Secrets,
       ECR Repositories, EFS File Systems, Elastic IPs

Azure: Virtual Machines, NSGs, Virtual Networks, Subnets, Storage Accounts,
       Blob Containers, Azure SQL Servers, Azure Functions, AKS Clusters,
       App Services, Key Vaults, Azure AD Users, Azure AD Service Principals,
       RBAC Role Assignments, Azure Firewall, Load Balancers, API Management,
       Cosmos DB, Azure Container Registry, Event Hubs, Service Bus

GCP:   Compute Instances, Firewall Rules, VPC Networks, Subnets, Cloud Storage
       Buckets, Cloud SQL Instances, Cloud Functions, GKE Clusters, Cloud Run,
       IAM Service Accounts, IAM Bindings, Cloud KMS Keys, BigQuery Datasets,
       Pub/Sub Topics, Cloud DNS Zones, Artifact Registry, Secret Manager Secrets

OCI:   Compute Instances, Security Lists, VCNs, Subnets, Object Storage Buckets,
       Autonomous Databases, Functions, OKE Clusters, IAM Users, IAM Groups,
       IAM Policies, Vault Secrets, Load Balancers
```

**Error handling and resilience:**
- Wrap all cloud API calls in retry logic: exponential backoff starting at 1s,
  max 5 retries, jitter added to avoid thundering herd
- On rate-limit errors (429): back off for the `Retry-After` header duration
- On auth errors (403/401): mark connector as `auth_failed`, notify org admins,
  stop polling (do not keep retrying — credentials may be permanently broken)
- On partial sync failure: log failed resource types, continue with others,
  mark the account as `partial_sync` rather than completely failing
- Circuit breaker: if cloud API error rate exceeds 50% for 5 minutes,
  pause polling for that account and alert the org

**Connector health monitoring:**
- Expose metrics: `cloudvisor_connector_last_sync_age_seconds`,
  `cloudvisor_connector_resources_total`, `cloudvisor_connector_errors_total`
- Write connector status to PostgreSQL `cloud_accounts` table after each sync
- Emit `connector.health_changed` Kafka event when status changes (active ↔ error)

#### CDM resource schema

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

@dataclass
class CloudResource:
    id: str                  # CloudVisor internal UUID (generated on discovery)
    cloud_resource_id: str   # AWS ARN / Azure Resource ID / GCP full resource name / OCI OCID
    provider: Literal['aws', 'azure', 'gcp', 'oci']
    account_id: str          # AWS Account ID / Azure Subscription ID / GCP Project ID / OCI Tenancy OCID
    region: str              # Cloud region (us-east-1, eastus, us-central1, us-ashburn-1)
    resource_type: str       # Namespaced type: "aws::ec2::instance", "azure::compute::virtualmachine"
    name: str                # Human-readable name
    tags: dict[str, str]     # Normalized tags/labels from any provider
    raw: dict[str, Any]      # Complete raw API response — stored as JSONB, never modified
    first_seen_at: datetime  # When CloudVisor first discovered this resource
    last_seen_at: datetime   # When CloudVisor last confirmed this resource exists
    organization_id: str     # Tenant scoping — always set, never null
    is_public: bool          # Whether this resource is internet-accessible (computed)
    environment: str         # prod | staging | dev | unknown (from tags or heuristics)
```

#### Kafka events this service produces

```
Topic: resource.discovered    # New resource found for the first time
Topic: resource.updated       # Existing resource state has changed
Topic: resource.deleted       # Resource no longer exists in the cloud account
Topic: connector.sync_started # A sync cycle has begun for an account
Topic: connector.sync_finished # A sync cycle has completed (with stats)
Topic: connector.health_changed # Connector status changed (active/error/paused)
```

All events use Avro schema registered in Confluent Schema Registry.
All events include: `organization_id`, `account_id`, `provider`, `timestamp`, `correlation_id`.

#### APIs this service exposes (internal only — consumed by API Gateway)

```
POST   /internal/accounts          Register a new cloud account
GET    /internal/accounts          List all accounts for an org
GET    /internal/accounts/{id}     Get account status and health
PATCH  /internal/accounts/{id}     Update connector config (polling interval etc.)
DELETE /internal/accounts/{id}     Remove a cloud account (stops polling, emits deleted events)
POST   /internal/accounts/{id}/sync  Trigger an immediate on-demand sync
GET    /internal/accounts/{id}/health  Detailed health: last sync, error rate, resource counts
GET    /internal/onboarding/aws/template  Download CloudFormation template for AWS onboarding
GET    /internal/onboarding/azure/instructions  Azure service principal setup guide
GET    /internal/onboarding/gcp/instructions   GCP service account setup guide
```

#### Performance targets

- Initial full sync for 10,000 resources: complete within 5 minutes
- Incremental sync cycle: complete within 60 seconds for accounts up to 50,000 resources
- Real-time event → Kafka event latency: under 60 seconds end-to-end
- Connector service uptime: 99.9% (sync pauses gracefully on cloud API outages)

---

### 3.2 — Service 2: Unified Asset Graph & Inventory

#### Role

The Asset Graph is CloudVisor's central nervous system. It stores every cloud resource
discovered by the Connector and — crucially — the relationships between those resources.
It is the single source of truth that every other module queries.

This service exists because security decisions are never about isolated resources —
they are about the relationships between them. "Is this S3 bucket dangerous?" depends
on whether it is publicly accessible, which IAM roles can read it, whether those roles
are over-privileged, and whether those roles are assumed by internet-facing services.
Answering that question requires traversing a graph, not querying a flat table.

Every module that needs to understand the cloud environment queries this service.
No module calls cloud provider APIs directly — they all ask the graph.

#### Tasks this service performs

**Graph construction and maintenance:**
- Consume `resource.discovered`, `resource.updated`, `resource.deleted` events from Kafka
- Map each CDM resource to a Neo4j node with appropriate label (`:EC2Instance`, `:S3Bucket`, etc.)
- Store all CDM fields as node properties; store `raw` as a compressed JSONB property
- After creating/updating nodes, compute and create relationship edges between resources
  based on the following relationship resolution rules:

```
EC2Instance -[:RUNS_IN]-> Subnet
EC2Instance -[:BELONGS_TO]-> SecurityGroup
EC2Instance -[:HAS_ROLE]-> IAMRole
EC2Instance -[:EXPOSES]-> Port (virtual node for open ports)
Subnet -[:BELONGS_TO]-> VPC
SecurityGroup -[:ALLOWS_INBOUND_FROM]-> CIDR (virtual node "0.0.0.0/0" = internet)
IAMRole -[:HAS_ACCESS_TO]-> S3Bucket (resolved from IAM policies)
IAMRole -[:HAS_ACCESS_TO]-> RDSInstance
IAMRole -[:ASSUMES]-> IAMRole (cross-account trust)
IAMUser -[:HAS_ACCESS_TO]-> IAMRole (via group membership + policy)
Lambda -[:HAS_ROLE]-> IAMRole
Lambda -[:CONNECTS_TO]-> RDSInstance (via VPC config + security groups)
S3Bucket -[:CONTAINS]-> DataClassification (added by DSPM module)
EKSCluster -[:RUNS_IN]-> VPC
EKSCluster -[:CONTAINS]-> NodeGroup
NodeGroup -[:RUNS_ON]-> EC2Instance
```

- Resolve IAM effective permissions by flattening AWS IAM policies,
  SCPs, resource policies, permission boundaries into net effective permissions
- Mark nodes with computed properties: `is_internet_exposed`, `has_public_access`,
  `contains_sensitive_data`, `is_production`, `risk_score`

**Historical snapshotting:**
- Every time a node is updated, store a versioned snapshot (timestamp + diff from previous)
- Enable "time travel" queries: "what did this resource look like 7 days ago?"
- Retain snapshots for 90 days (configurable per plan)
- Use TimescaleDB (PostgreSQL extension) for time-series snapshot storage

**Risk score computation:**
- After every node update, recompute the node's risk score (0–100)
- Risk score formula: weighted combination of:
  - Open findings severity (CRITICAL=40pts, HIGH=20pts, MEDIUM=5pts per finding, max 60pts)
  - Internet exposure (public = +20pts)
  - Data sensitivity (contains PII/PHI = +15pts)
  - Privilege level (admin IAM access = +10pts)
  - Environment (production asset = multiplier ×1.5)
- Emit `asset.risk_score_changed` Kafka event when score changes by more than 5 points

**Elasticsearch sync:**
- Maintain a synchronized Elasticsearch index of all nodes for full-text search
- Sync on every node create/update/delete (via Kafka consumer + Elasticsearch bulk API)
- Enable queries like: "find all resources containing 'payment' in name or tags"
- Elasticsearch index maps to the CDM schema; `raw` field is excluded (too large)

**Graph query API:**
- Expose a GraphQL endpoint for flexible, nested graph queries
- Expose a REST endpoint for paginated, filtered asset listing
- Support complex filters: type, region, account, tag, risk score range, exposure
- Support relationship traversal in GraphQL: `asset { relatedAssets { findings } }`
- Cache frequent queries in Redis (TTL: 60 seconds)

**Change detection:**
- Track which node properties changed between updates
- Emit `asset.relationship_changed` when an edge is added or removed
- This feeds CDR anomaly detection and CSPM drift detection

#### Cypher queries the graph must natively support

```cypher
-- All internet-exposed resources with open findings
MATCH (r)-[:ALLOWS_INBOUND_FROM]->(c:CIDR {value: "0.0.0.0/0"})
WHERE r.open_findings_count > 0
RETURN r ORDER BY r.risk_score DESC LIMIT 100

-- Full attack path: internet → sensitive database (up to 6 hops)
MATCH path = (i:InternetGateway)-[:CONNECTS_TO*1..6]->(db:RDSInstance)
WHERE db.contains_pii = true
RETURN path, length(path) ORDER BY length(path) ASC LIMIT 10

-- Over-privileged IAM roles with access to production resources
MATCH (role:IAMRole)-[:HAS_ACCESS_TO]->(res)
WHERE role.unused_permissions_count > 20
  AND res.environment = 'prod'
RETURN role, collect(res) AS prod_resources

-- All resources a compromised IAM role could reach (blast radius)
MATCH (role:IAMRole {id: $role_id})-[:HAS_ACCESS_TO*1..3]->(target)
RETURN target, labels(target) AS type
```

#### Kafka events this service produces

```
Topic: asset.created              # New node added to graph
Topic: asset.updated              # Node properties changed
Topic: asset.deleted              # Node removed from graph
Topic: asset.risk_score_changed   # Node risk score updated significantly
Topic: asset.relationship_changed # Edge added or removed between nodes
```

#### Kafka events this service consumes

```
Topic: resource.discovered  → create node + compute edges
Topic: resource.updated     → update node + recompute edges + snapshot
Topic: resource.deleted     → delete node + cascade edge removal
Topic: finding.created      → update node's open_findings_count + recompute risk score
Topic: finding.resolved     → update node's open_findings_count + recompute risk score
```

#### APIs this service exposes

```
GET    /internal/assets                  List assets (paginated, filterable)
GET    /internal/assets/{id}             Get single asset with all properties
GET    /internal/assets/{id}/related     Get related assets (graph neighbors, configurable depth)
GET    /internal/assets/{id}/history     Get historical snapshots for an asset
GET    /internal/assets/{id}/findings    Get all open findings for an asset
GET    /internal/assets/{id}/attack-paths  Compute attack paths to/from this asset
GET    /internal/assets/search           Full-text search across all assets (Elasticsearch)
POST   /internal/assets/query            Execute a parameterized Cypher query (restricted set)
GET    /internal/graph/stats             Asset counts by type, region, account
```

#### Performance targets

- Graph query (1M nodes, 5M edges): p95 < 500ms
- Attack path computation (6 hops, 1M nodes): p95 < 2 seconds
- Elasticsearch full-text search: p95 < 200ms
- Node create/update (from Kafka event to indexed in graph): p95 < 3 seconds
- Risk score recomputation: < 100ms per node

---

### 3.3 — Service 3: Multi-Tenant Auth & RBAC

#### Role

The Auth service is the identity and access control backbone of CloudVisor. It is
responsible for authenticating every human user and machine client, and for authorizing
every action they attempt. It also enforces tenant isolation — ensuring that data from
one organization is completely invisible to another.

This service must be treated as the highest-security component in the platform.
A bug here does not result in a missing feature — it results in a customer's
confidential security data being exposed to another customer. That is a company-ending event.

Every other service delegates all authentication and authorization decisions to this
service. No service implements its own auth logic.

#### Tasks this service performs

**Organization (tenant) management:**
- Create new organizations on signup (name, slug, plan, billing email)
- Generate organization-specific encryption keys (managed in HashiCorp Vault)
- Enforce organization-level feature flags based on `plan` (free/starter/growth/enterprise)
- Support organization deletion with full data purge cascade
- Emit `org.created`, `org.plan_changed`, `org.deleted` Kafka events

**User authentication:**
- Email + password authentication: bcrypt password hashing (cost factor 12), no plaintext ever
- Google OAuth 2.0 / GitHub OAuth (social login via Keycloak identity brokering)
- SAML 2.0 SSO for enterprise customers (IdP-initiated and SP-initiated flows)
- OIDC SSO: Okta, Azure AD, Ping Identity, any OIDC-compliant provider
- Issue JWT access tokens (RS256 signed, 15-minute expiry)
- Issue refresh tokens (opaque, stored hashed in PostgreSQL, 30-day expiry)
- Refresh token rotation: every use issues a new refresh token and invalidates the old one
- Token introspection endpoint: all other services call this to validate tokens

**MFA (Multi-Factor Authentication):**
- TOTP-based MFA (RFC 6238) compatible with Google Authenticator, Authy, 1Password
- MFA enrollment: generate QR code + backup codes (10 single-use codes, bcrypt hashed)
- Enforce MFA for all users in enterprise-tier organizations (configurable)
- MFA bypass for machine API keys (API keys are long-lived credentials, not sessions)

**API key management:**
- Generate API keys: `cv_live_<32-char-random>` format, only shown once on creation
- Store only the SHA-256 hash of the key in PostgreSQL (never the key itself)
- Scopes: keys can be limited to specific permission sets (e.g., `findings:read`)
- Key rotation: deprecate old key with a configurable grace period before revocation
- Per-key rate limits stored in Redis
- Emit `api_key.created`, `api_key.rotated`, `api_key.revoked` audit events

**Role-Based Access Control (RBAC):**
- Built-in roles (cannot be deleted, cannot be modified):

| Role | Permissions |
|---|---|
| `owner` | All permissions including billing, org deletion, member removal |
| `admin` | All security permissions, user management, no billing access |
| `security_engineer` | Read/write: findings, policies, suppressions, reports |
| `devops` | Read/write: CI/CD module, IaC scanning results; read-only elsewhere |
| `viewer` | Read-only across all modules, no settings access |
| `auditor` | Read-only across all modules + export compliance reports |

- Custom roles (enterprise tier): define arbitrary permission sets from a permission list
- Resource-level scoping: restrict a role to specific cloud accounts or regions
  (e.g., a devops engineer can only see findings for their team's AWS account)
- Permission check API: all services call `POST /internal/auth/authorize` with
  `{user_id, action, resource_type, resource_id}` — never implement checks locally

**Session management:**
- Track all active sessions: device, IP, user agent, last active timestamp
- Allow users to view and revoke any active session from the UI
- Automatic session expiry after 7 days of inactivity
- Force-expire all sessions on password change or suspicious activity detection

**Audit logging:**
- Record every authentication event: login (success/fail), logout, MFA attempt,
  token refresh, API key use
- Record every authorization event: permission check result, access denied reason
- Emit all audit events to Kafka topic `audit.events` (consumed by the alert service
  and CDR service)
- Store audit log in append-only PostgreSQL table (no deletes, no updates ever)
- Retain audit logs for 365 days minimum (configurable up to 7 years for compliance)

**Tenant data isolation — how it works end-to-end:**
1. Auth service validates token → extracts `organization_id`
2. Auth service injects `organization_id` into request context
3. API Gateway forwards request to target service with `X-Org-ID` header
4. Each service sets `SET LOCAL app.current_org_id = '{org_id}'` at DB session start
5. RLS policies on all tables automatically filter by `current_org_id`
6. Service never needs to add `WHERE organization_id = ?` — the DB handles it

#### APIs this service exposes

```
-- Public endpoints (no auth required)
POST   /auth/register               Create new account (email + org name)
POST   /auth/login                  Email + password login → access + refresh token
POST   /auth/refresh                Exchange refresh token for new access token
POST   /auth/logout                 Invalidate refresh token
POST   /auth/sso/saml/callback      SAML 2.0 assertion handler
GET    /auth/sso/saml/metadata      SAML SP metadata (for IdP configuration)
POST   /auth/sso/oidc/callback      OIDC authorization code handler
POST   /auth/forgot-password        Send password reset email
POST   /auth/reset-password         Consume reset token, set new password

-- Authenticated endpoints
GET    /auth/me                     Current user profile + permissions
POST   /auth/mfa/enroll             Begin MFA enrollment → QR code
POST   /auth/mfa/verify             Verify TOTP code during enrollment
POST   /auth/mfa/validate           Validate TOTP code during login
GET    /auth/sessions               List active sessions
DELETE /auth/sessions/{id}          Revoke a specific session
GET    /auth/api-keys               List API keys (metadata only, not key values)
POST   /auth/api-keys               Create new API key
DELETE /auth/api-keys/{id}          Revoke an API key

-- Internal endpoints (mTLS, not exposed externally)
POST   /internal/auth/validate      Validate JWT or API key → return user + org + permissions
POST   /internal/auth/authorize     Check if action is permitted for user + resource
GET    /internal/auth/org/{id}      Get organization details including plan + feature flags
```

#### PostgreSQL RLS implementation

```sql
-- Set the org context at the start of every database session
-- (done in middleware, before any query)
SET LOCAL app.current_org_id = '550e8400-e29b-41d4-a716-446655440000';

-- RLS policy applied to every tenant-scoped table
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON findings
  AS PERMISSIVE FOR ALL TO cloudvisor_app
  USING (organization_id = current_setting('app.current_org_id')::UUID)
  WITH CHECK (organization_id = current_setting('app.current_org_id')::UUID);

-- Apply the same pattern to: cloud_accounts, users, rules, reports,
-- notifications, api_keys, suppressions, incidents, audit_log
```

#### Performance targets

- Token validation (`/internal/auth/validate`): p99 < 10ms (cached in Redis after first validation)
- Login (email + password): p95 < 300ms
- Authorization check (`/internal/auth/authorize`): p99 < 5ms (Redis-cached permission matrix)
- Token cache TTL in Redis: 5 minutes (short enough for revocation to propagate)

---

### 3.4 — Service 4: Policy & Rules Engine

#### Role

The Policy Engine is the security brain of CloudVisor. It is the sole location where
security evaluation logic lives. Every security check that CloudVisor performs —
whether it is a CSPM misconfiguration check, a Kubernetes pod security audit,
an IaC pre-deployment scan, or a CI/CD pipeline gate — is expressed as a Rego policy
and evaluated by this service.

This service exists to enforce a critical architectural rule: **no security logic
is hardcoded in Python application code.** If a rule needs to change (and rules always
need to change — new CVEs, new compliance frameworks, new cloud services), the Rego
file is updated in Git and the change takes effect without a service deployment.

This service is shared infrastructure. It does not belong to any single module.
Every security module calls this service to evaluate rules.

#### Tasks this service performs

**Rule storage and versioning:**
- Serve as the authoritative source of all OPA rules for the platform
- Load rules from the `/rules/rego/` Git-backed directory on startup
- Hot-reload rules without service restart when Git changes are pushed to main branch
  (poll Git every 60 seconds or receive a webhook from GitHub Actions on merge)
- Track rule versions: every rule has a `version` field in its metadata annotation
- Support rule rollback: revert to a previous version of a specific rule
- Maintain a rule registry in PostgreSQL: all rules, their metadata, enable/disable status per org

**Rule organization:**
- Rules are organized in namespaced directories:
  - `/rules/rego/cspm/aws/` — AWS CSPM rules
  - `/rules/rego/cspm/azure/` — Azure CSPM rules
  - `/rules/rego/cspm/gcp/` — GCP CSPM rules
  - `/rules/rego/cspm/oci/` — OCI CSPM rules
  - `/rules/rego/kspm/` — Kubernetes security rules
  - `/rules/rego/iac/terraform/` — Terraform IaC rules
  - `/rules/rego/iac/helm/` — Helm chart rules
  - `/rules/rego/iac/cloudformation/` — CloudFormation rules
  - `/rules/rego/cicd/` — CI/CD pipeline rules
  - `/rules/rego/cdr/` — CDR detection rules
  - `/rules/rego/custom/{org_id}/` — Per-organization custom rules

**Rule metadata standard:**
Every Rego rule file must include structured metadata annotations:
```rego
# METADATA
# title: "S3 bucket must not have public access enabled"
# description: "Public S3 buckets expose data to the internet without authentication.
#   Any object in the bucket can be read by anyone."
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
#     control: "1.3.2"
# remediation: "1. Go to S3 console → select bucket → Permissions tab.
#   2. Under Block Public Access, enable all four settings.
#   3. Remove any bucket policy that grants public access (Principal: '*')."
# references:
#   - https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
# version: "1.2.0"
# tags: [storage, public-access, data-exposure]

package cspm.aws.s3

import future.keywords

deny[finding] {
    input.resource_type == "aws::s3::bucket"
    not input.raw.PublicAccessBlockConfiguration.BlockPublicAcls
    finding := {
        "rule_id": "s3-public-access-block-not-enabled",
        "title": "S3 bucket must not have public access enabled",
        "severity": "CRITICAL",
    }
}
```

**Rule evaluation:**
- Accept evaluation requests from any module: `POST /internal/policy/evaluate`
- Input: one or many CDM resource objects + optional rule filter (category, rule_id list)
- Pass inputs to the OPA engine (embedded Python OPA library or sidecar process)
- Collect all violations (deny rules that fired)
- Enrich each violation with full rule metadata (title, description, remediation, compliance)
- Return structured Finding objects ready for the Alert Pipeline to ingest
- Support batch evaluation: evaluate 10,000 resources in a single request

**Compliance framework mapping:**
- Maintain a compliance framework registry: CIS AWS/Azure/GCP/OCI, SOC 2, PCI-DSS,
  HIPAA, ISO 27001, NIST 800-53, GDPR, FedRAMP, CCPA
- Map each rule to the controls it covers (stored in rule metadata, indexed in PostgreSQL)
- Provide a compliance posture API: given an org + framework, return pass/fail per control
- Calculate framework compliance percentage: (passing controls / total controls) × 100

**Custom rule management:**
- Allow security engineers to write and test custom Rego rules via the UI
- Provide a dry-run endpoint: evaluate a custom rule against current asset graph
  without creating findings (preview mode)
- Validate Rego syntax before saving (OPA --check)
- Namespace custom rules per org: `package custom.{org_id}.{rule_name}`
- Version and audit all custom rule changes (who changed what, when)

**Rule enable/disable per organization:**
- Each org can disable specific built-in rules they have accepted as risk
- Disabled rules are stored in PostgreSQL (rule_id + org_id + reason + user_id)
- Disabled rules are skipped during evaluation for that org
- Disabled rules still appear in the UI as "suppressed" with the reason

#### Kafka events this service produces

```
Topic: finding.raw          # A rule evaluation produced a violation
Topic: rule.updated         # A rule was added, changed, or disabled
```

#### Kafka events this service consumes

```
Topic: resource.discovered  → trigger evaluation of all rules for the new resource
Topic: resource.updated     → re-evaluate all rules for the changed resource
```

#### APIs this service exposes

```
-- Rule management
GET    /internal/policy/rules                 List all rules (filter by category, provider, severity)
GET    /internal/policy/rules/{id}            Get rule detail including full metadata
POST   /internal/policy/rules/custom          Create a custom rule for an org
PUT    /internal/policy/rules/custom/{id}     Update a custom rule
DELETE /internal/policy/rules/custom/{id}     Delete a custom rule
POST   /internal/policy/rules/{id}/disable    Disable a built-in rule for an org
POST   /internal/policy/rules/{id}/enable     Re-enable a disabled rule

-- Evaluation
POST   /internal/policy/evaluate             Evaluate rules against one or many resources
POST   /internal/policy/evaluate/dry-run     Test a custom rule without creating findings

-- Compliance
GET    /internal/policy/compliance                      Overall posture across all frameworks
GET    /internal/policy/compliance/{framework}          Control-by-control breakdown
GET    /internal/policy/compliance/{framework}/evidence Download evidence for a control
```

#### Performance targets

- Single resource evaluation (all applicable rules): p95 < 100ms
- Batch evaluation (10,000 resources × 500 rules): complete within 30 seconds
- Rule hot-reload after Git push: new rules active within 90 seconds
- Compliance posture query: p95 < 500ms (cached in Redis for 5 minutes)

---

### 3.5 — Service 5: Alert Pipeline & Notification Engine

#### Role

The Alert Pipeline is the unified findings management system for all of CloudVisor.
Every security module produces findings — CSPM finds misconfigurations, CWPP finds
vulnerabilities, CDR detects threats, CI/CD gates catch insecure code. Without a
shared pipeline, each module would need its own deduplication logic, its own
notification system, its own state management, and its own UI integration.

The Alert Pipeline solves this by being the single funnel through which all findings
pass. It normalizes, deduplicates, enriches, routes, and tracks every finding from
every module. The UI shows one inbox. The Jira integration sends one type of ticket.
The Slack bot sends one format of message. This consistency is what makes CloudVisor
usable as a unified platform rather than a collection of disconnected scanners.

#### Tasks this service performs

**Finding ingestion:**
- Consume `finding.raw` events from Kafka (published by Policy Engine and CDR service)
- Validate the Finding schema: reject malformed events, log, and send to dead-letter topic
- Accept direct REST submissions from modules that cannot use Kafka (CI/CD CLI output)
- Process events at sustained throughput of 10,000+ findings/second

**Deduplication:**
- Compute a deterministic fingerprint for each finding:
  `SHA-256(rule_id + resource_id + account_id + organization_id)`
- Check Redis cache for existing finding with same fingerprint (TTL: indefinite, evict on resolve)
- If duplicate: update `last_seen_at` on existing finding, emit `finding.seen_again` event
- If new: create finding record in PostgreSQL, emit `finding.created` event
- This ensures a finding for a misconfigured S3 bucket appears once, not thousands of times

**Finding enrichment:**
- After creating a finding, enrich it with context from other services:
  - Query Asset Graph service: add asset metadata (name, tags, environment, risk score)
  - Query Policy Engine: add compliance mappings for the rule that fired
  - Query AIOps service (when available): add AI-computed risk score and priority rank
- Store enriched context in `findings.context` JSONB column

**Finding lifecycle management:**
- Enforce a strict state machine for every finding:

```
[open] → [in_progress] → [resolved]
[open] → [suppressed]
[open] → [accepted_risk]
[in_progress] → [open]        (if assignee unassigns)
[resolved] → [open]           (if same resource regresses — drift detection)
```

- Validate all state transitions — reject invalid transitions with a clear error
- Track state history: every transition recorded in `finding_history` table
- Auto-resolve findings when the underlying resource is fixed (detected by `resource.updated`
  event → re-evaluation → rule no longer fires → finding resolved automatically)
- Drift detection: when a previously-resolved finding fires again for the same resource,
  reopen the finding and increment a `regression_count` counter
- SLA tracking: compute time-in-state for each severity level:
  - CRITICAL: target acknowledge < 4 hours, resolve < 24 hours
  - HIGH: target acknowledge < 24 hours, resolve < 7 days
  - MEDIUM: target acknowledge < 7 days, resolve < 30 days

**Alert grouping into incidents:**
- Continuously look for findings that should be grouped together into a single incident
- Grouping criteria (configurable, applied in order):
  1. Same attack path (findings linked by graph traversal)
  2. Same root cause rule on the same account (bulk misconfiguration)
  3. Same resource with multiple findings (compromised resource)
  4. CDR alerts on the same entity within a 1-hour window
- Create an `Incident` record that links multiple findings
- Incidents have their own lifecycle: `open` → `investigating` → `resolved`
- Emit `incident.created`, `incident.updated` Kafka events

**Suppression rules:**
- Allow orgs to create suppression rules that automatically suppress matching findings
- Suppression criteria: rule_id, resource tag (e.g., `env=dev`), account, region, time window
- Evaluate all active suppressions against every new finding before persisting
- Log all suppressed findings for audit purposes (suppressed ≠ deleted)
- Suppression rules expire (configurable: 7 days / 30 days / never)

**Notification routing:**
- For every new finding that is NOT suppressed, evaluate notification routing rules
- Routing rules: match by severity, module, resource tag, account → route to channel(s)
- Default routing: CRITICAL → immediate Slack + PagerDuty; HIGH → Slack; all → email digest
- Notification channels:

| Channel | Details |
|---|---|
| Slack | Per-channel routing by severity/team, message includes resource name, severity, direct link to finding |
| Jira | Auto-create issue with finding title, description, remediation, priority mapped from severity; bi-directional status sync |
| Microsoft Teams | Adaptive Card format, configurable webhook per team |
| Email | Real-time on CRITICAL/HIGH; daily digest at 9am org timezone for MEDIUM/LOW |
| PagerDuty | CRITICAL severity triggers on-call escalation; resolves automatically when finding resolved |
| ServiceNow | Create incident or change request, map severity to priority |
| Generic webhook | JSON payload (finding + context) to any HTTPS endpoint, HMAC-SHA256 signed |

- Rate limiting per channel: prevent notification storms (max 10 Slack messages/minute/channel)
- Notification deduplication: never send duplicate notifications for the same finding

**Bulk operations:**
- Support bulk status updates: select 500 findings → mark all as `accepted_risk`
- Support bulk assignment: assign a set of findings to a team member
- Support bulk suppression: suppress all findings matching a filter

**Metrics and reporting data:**
- Maintain pre-aggregated counters in Redis for dashboard performance:
  - Findings by severity (updated in real-time)
  - Findings by module, account, region
  - Trend data: new findings per day for the last 90 days
  - MTTR (mean time to resolve) per severity
- These counters are what the dashboard queries — not raw SQL aggregations

#### Kafka events this service produces

```
Topic: finding.created           # New unique finding persisted
Topic: finding.updated           # Finding status, assignee, or context changed
Topic: finding.resolved          # Finding moved to resolved state
Topic: finding.seen_again        # Duplicate finding detected (last_seen_at updated)
Topic: finding.suppressed        # Finding matched a suppression rule
Topic: incident.created          # Multiple findings grouped into an incident
Topic: incident.updated          # Incident status or composition changed
Topic: notification.sent         # A notification was dispatched to a channel
Topic: notification.failed       # A notification delivery failed
```

#### Kafka events this service consumes

```
Topic: finding.raw          → deduplicate + enrich + persist + route notifications
Topic: resource.updated     → check if any open findings for this resource should auto-resolve
Topic: resource.deleted     → auto-resolve all open findings for deleted resource
Topic: audit.events         → pass-through to audit log storage
```

#### APIs this service exposes

```
-- Findings
GET    /internal/findings                     List findings (paginated, extensive filters)
GET    /internal/findings/{id}                Get finding detail + context + history
PATCH  /internal/findings/{id}                Update status, assignee, notes
POST   /internal/findings/{id}/suppress       Suppress with reason
POST   /internal/findings/{id}/accept-risk    Accept risk with justification
POST   /internal/findings/bulk                Bulk status update
GET    /internal/findings/stats               Aggregated counts by severity, status, module

-- Incidents
GET    /internal/incidents                    List incidents
GET    /internal/incidents/{id}               Get incident + linked findings
PATCH  /internal/incidents/{id}              Update incident status, assignee

-- Suppression rules
GET    /internal/suppressions                 List active suppression rules
POST   /internal/suppressions                 Create suppression rule
DELETE /internal/suppressions/{id}            Delete suppression rule

-- Notification config
GET    /internal/notifications/channels       List configured channels
POST   /internal/notifications/channels       Add notification channel
PUT    /internal/notifications/channels/{id}  Update channel config
DELETE /internal/notifications/channels/{id}  Remove channel
POST   /internal/notifications/test           Send test notification to a channel
```

#### Performance targets

- Finding ingestion throughput: 10,000 findings/second sustained
- Deduplication check (Redis lookup): p99 < 5ms
- End-to-end latency (Kafka event → Slack message): p95 < 10 seconds
- Bulk operation (500 findings status update): complete within 5 seconds

---

### 3.6 — Service 6: Core Dashboard UI & Public API

#### Role

The Core Dashboard and Public API are the customer-facing layer of CloudVisor. The
dashboard is the interface that CISOs, security engineers, SOC analysts, and compliance
officers log into every day. The public API is how enterprise customers integrate
CloudVisor into their existing toolchains, automation workflows, and SIEM systems.

These two components are what closes deals. A CSPM module without a polished UI is
a script. With a dashboard that loads in under 2 seconds and shows a compelling risk
posture report, it is a product.

The API is a first-class product, not an afterthought. Every feature in the UI must
be accessible via API. Enterprise customers will evaluate the API before they evaluate
the UI.

#### Tasks — Dashboard UI

**Page: Risk overview (`/dashboard`):**
- Overall security posture score (0–100) with trend vs. last 30 days
- Finding breakdown: donut chart by severity (CRITICAL/HIGH/MEDIUM/LOW)
- Compliance posture: mini-cards per framework showing pass percentage
- Top 10 riskiest assets: list with risk score, asset name, type, open findings count
- Recent activity feed: last 20 finding state changes, new assets discovered, scan completions
- Quick actions: "Run scan", "Connect cloud account", "View critical findings"

**Page: Asset explorer (`/assets`):**
- Filterable table: filter by provider, account, region, resource type, tags, risk score range
- Toggle between table view (for filtering) and graph view (interactive Neo4j visualization)
- Click any asset → side drawer with full asset details, relationships, and open findings
- Search: full-text search across asset name, ID, tags (Elasticsearch-backed)
- Export filtered assets to CSV

**Page: Findings inbox (`/findings`):**
- Full findings table with columns: severity badge, title, resource, account, age, status, assignee
- Multi-select + bulk actions: assign, suppress, accept risk, change status
- Advanced filter panel: module, severity, status, account, region, rule, compliance framework, date range
- Click any finding → full detail page with:
  - Finding description and full remediation steps
  - Affected resource details + link to asset page
  - Compliance controls this finding impacts
  - AI-generated plain-English explanation (when AIOps available)
  - AI-generated fix code snippet (when AIOps available)
  - State history timeline
  - Comment thread for team collaboration

**Page: Compliance dashboard (`/compliance`):**
- Framework selector: CIS AWS/Azure/GCP, SOC 2, PCI-DSS, HIPAA, ISO 27001, NIST, GDPR
- Heatmap: rows = control domains, cells = pass/fail percentage
- Click any cell → list of controls in that domain with pass/fail per control
- Click any failing control → list of findings that are causing the failure
- Generate compliance report button → PDF export with evidence table

**Page: Connectors (`/settings/connectors`):**
- List all connected cloud accounts with status indicator (green/amber/red)
- Click "Connect AWS/Azure/GCP/OCI" → guided onboarding wizard
- Each account card shows: resource count, last sync time, finding count, health status
- Remove account button (with confirmation and impact warning)

**Page: Notifications (`/settings/notifications`):**
- List all configured notification channels with status
- Add Slack: OAuth flow to authorize workspace + channel picker
- Add Jira: API token + project key + issue type configuration
- Add PagerDuty: service integration key
- Add webhook: URL + secret for HMAC verification
- Per-channel routing rules: configure which severities/modules trigger each channel

**Page: Team management (`/settings/team`):**
- List all users with roles, last login, MFA status
- Invite user: email + role assignment
- Edit user role
- Remove user (with confirmation)
- API keys panel: create, name, set scopes, see last-used date, revoke

**Page: Reports (`/reports`):**
- List previously generated reports with download links
- Generate new report: select framework, date range, accounts to include
- Report formats: PDF (formatted for auditors) and CSV (raw data)
- Schedule recurring reports: weekly/monthly, auto-emailed to specified addresses

#### Tasks — Public REST API

**API standards:**
- Base URL: `https://api.cloudvisor.io/v1`
- Authentication: `Authorization: Bearer <JWT>` or `X-API-Key: <key>`
- All responses use the standard envelope:
```json
{
  "data": {},
  "meta": {
    "page": 1,
    "per_page": 50,
    "total": 1247,
    "next_cursor": "eyJpZCI6IjEyMyJ9"
  },
  "errors": []
}
```
- Pagination: cursor-based for all list endpoints (no offset pagination)
- Filtering: query parameters using `filter[field]=value` syntax
- Sorting: `sort=severity,-created_at` (prefix `-` for descending)
- Field selection: `fields[findings]=id,severity,title` to reduce response size
- Rate limiting: headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Webhooks: all outbound payloads signed with `X-CloudVisor-Signature: sha256=<hmac>`

**Full MVP endpoint list:**
```
-- Assets
GET  /v1/assets                       List assets (filter by type, region, account, risk_score)
GET  /v1/assets/{id}                  Get asset with properties and related asset IDs
GET  /v1/assets/{id}/findings         Get findings for a specific asset
GET  /v1/assets/{id}/attack-paths     Get computed attack paths to/from this asset

-- Findings
GET    /v1/findings                   List findings with full filter support
GET    /v1/findings/{id}              Finding detail with remediation and compliance
PATCH  /v1/findings/{id}             Update status (open/in_progress/resolved/accepted_risk)
POST   /v1/findings/{id}/suppress    Suppress with required reason field
POST   /v1/findings/bulk             Bulk status update (max 500 per request)

-- Compliance
GET  /v1/compliance                   Posture summary across all active frameworks
GET  /v1/compliance/{framework}       Control-level detail for one framework

-- Cloud accounts
GET    /v1/accounts                   List connected cloud accounts
POST   /v1/accounts                   Connect new cloud account
GET    /v1/accounts/{id}              Account status and health
DELETE /v1/accounts/{id}              Remove cloud account
POST   /v1/accounts/{id}/scan         Trigger on-demand scan

-- Reports
GET    /v1/reports                    List generated reports
POST   /v1/reports                    Generate new report (async — returns job ID)
GET    /v1/reports/{id}               Report status and download URL

-- Rules
GET    /v1/rules                      List all rules (filter by category, severity)
GET    /v1/rules/{id}                 Rule detail including metadata and compliance mappings
POST   /v1/rules/{id}/disable         Disable a rule for this org
POST   /v1/rules/custom               Create a custom rule

-- Notifications
GET    /v1/webhooks                   List configured webhooks
POST   /v1/webhooks                   Register a new webhook endpoint
DELETE /v1/webhooks/{id}              Remove a webhook

-- AIOps
POST   /v1/copilot/query              Natural language security query
GET    /v1/risk/attack-paths          Get all computed attack paths for the org
GET    /v1/risk/top-assets            Top N riskiest assets by risk score

-- Scans
POST   /v1/scan                       Trigger full on-demand scan across all accounts
GET    /v1/scans/{id}                 Get scan status and results summary
```

**OpenAPI spec:** Auto-generated from FastAPI route decorators. Served at `/v1/docs`.
Never hand-write the spec — it must always be generated from code.

**GraphQL API:**
- Endpoint: `POST /graphql`
- Schema covers: assets (with relationship traversal), findings, rules, compliance
- Primary use case: complex nested queries like:
  ```graphql
  query {
    assets(filter: { is_public: true, risk_score_gte: 70 }) {
      id name resourceType
      findings(status: OPEN, severity: [CRITICAL, HIGH]) {
        title severity remediationSteps
      }
      relatedAssets(relationship: HAS_ACCESS_TO) {
        id name resourceType
      }
    }
  }
  ```

**Public Python SDK:**
```python
from cloudvisor import CloudVisor

cv = CloudVisor(api_key="cv_live_...")

# List critical findings
findings = cv.findings.list(severity="CRITICAL", status="open")
for f in findings:
    print(f.title, f.resource.name, f.remediation)

# Query natural language
result = cv.copilot.query("Which prod S3 buckets contain PII and are publicly accessible?")
print(result.answer)
```

#### Performance targets

- Dashboard initial page load: < 2 seconds (Lighthouse performance score > 90)
- API list endpoint response: p95 < 200ms
- API detail endpoint response: p95 < 100ms
- GraphQL query: p95 < 500ms
- Report generation (10,000 findings, PDF): complete within 60 seconds
- Concurrent users supported without degradation: 500

---

## 4. Security Modules

Build in this priority order. Every module depends on all 6 foundational services.
A module may not be started until its dependencies are fully operational and tested.

---

### 4.1 — Module 1: CSPM (Cloud Security Posture Management)

#### Role

CSPM is CloudVisor's wedge product and first revenue source. Its job is to continuously
evaluate the configuration of every cloud resource against the policy engine's rule library
and surface misconfigurations before they become breaches.

It is agentless — it requires no software to be installed on customer infrastructure.
Onboarding takes under 5 minutes. The first scan completes within minutes and produces
a risk report that answers: "How badly misconfigured is my cloud environment, and what
are the top things I need to fix right now?" That report is CloudVisor's closing tool
in enterprise sales demos.

#### Key tasks and behaviors

- Subscribe to `resource.discovered` and `resource.updated` Kafka events
- For each event, call the Policy Engine's evaluate endpoint with the CDM resource object
- Pass the full `raw` field to OPA (the rules inspect the raw API response for precise checks)
- Collect all violations returned by the policy engine
- Enrich violations with the rule metadata (title, description, remediation, compliance)
- Publish each violation as a `finding.raw` Kafka event (consumed by Alert Pipeline)
- When `resource.updated` fires and a previous finding for the same resource no longer fires
  → publish `finding.resolved` event (auto-remediation detection)
- Maintain a finding history: track every time a resource regressed (was fixed, then broke again)
- Compute per-account risk score: weighted average of open finding severities
- Provide a drift detection API: compare current posture snapshot to a previous snapshot

**Scanning trigger modes:**
- Event-driven: scan a resource immediately when it changes (primary mode)
- Scheduled full scan: scan every resource in an account every 24 hours
  (catches any findings that may have been missed due to event delivery failures)
- On-demand scan: triggered by user via API or UI button

**Built-in rule coverage (500+ rules):**
- AWS: S3 (public access, encryption, versioning, logging), EC2 (public AMIs, IMDSv1,
  unencrypted EBS), IAM (root MFA, key rotation, over-permissive policies),
  RDS (public access, unencrypted, backup retention), VPC (flow logs, default VPC usage),
  CloudTrail (multi-region, log validation), KMS (key rotation), Lambda (unrestricted invocation)
- Azure: Storage Accounts (public blob access, HTTPS only), Virtual Machines (disk encryption,
  OS disk unencrypted), NSGs (unrestricted inbound SSH/RDP), SQL (TDE, auditing, firewall),
  Key Vault (soft delete, purge protection), AKS (RBAC, network policy), Identity (MFA, admin users)
- GCP: Cloud Storage (uniform bucket access, public buckets), Compute (OS login, serial port access,
  project-wide SSH keys), IAM (service account keys, primitive roles), Cloud SQL (public IP,
  backup, SSL), GKE (legacy auth, network policy, node auto-upgrade), Logging (audit log config)
- OCI: Object Storage (public access, versioning), Compute (public IP, OS management),
  IAM (policies, MFA for admin users), Autonomous DB (public endpoint, backup)

#### Kafka events this module produces

```
Topic: finding.raw           # New misconfiguration detected
Topic: finding.resolved      # Previously-detected misconfiguration is now fixed
Topic: scan.started          # Scan cycle has begun for an account
Topic: scan.completed        # Scan cycle has completed (with stats: resources scanned, findings created)
```

#### APIs this module exposes

```
GET  /internal/cspm/scans            List scan history for an account
POST /internal/cspm/scans            Trigger on-demand scan
GET  /internal/cspm/scans/{id}       Scan status and finding summary
GET  /internal/cspm/posture          Current posture score per account
GET  /internal/cspm/drift            Drift report: changes since a given date
```

---

### 4.2 — Module 2: CWPP (Cloud Workload Protection Platform)

#### Role

CWPP protects running workloads — virtual machines, containers, and serverless functions.
While CSPM asks "is this resource configured correctly?", CWPP asks "is this running
workload vulnerable?" It discovers known vulnerabilities (CVEs) in the software packages
installed on workloads and in the container images they run, and optionally monitors
workload behavior at runtime to detect threats.

CWPP uses two modes of scanning:
- **Agentless** (default): works by taking read-only snapshots of VM disks and container
  images — no software installed on customer workloads. Zero performance impact.
- **Agent-based** (optional): a lightweight eBPF agent provides runtime visibility —
  process execution, network connections, syscall patterns.

#### Key tasks and behaviors

**Agentless vulnerability scanning:**
- For EC2/Azure VM/GCP Compute instances: mount read-only EBS/managed disk snapshot,
  scan the OS filesystem for installed packages using `syft` (SBOM generation)
- Cross-reference installed packages against vulnerability databases:
  NVD (NIST), GitHub Advisory Database, OSV (Open Source Vulnerabilities)
- For container images: pull image layers from ECR/ACR/GCR/Docker Hub using registry API,
  extract filesystem, scan packages with Trivy
- For Lambda/Azure Functions/GCP Cloud Functions: download deployment package,
  extract dependency files (`requirements.txt`, `package.json`, `pom.xml`), scan with Grype
- Generate a CycloneDX SBOM for each scanned workload and store as an artifact

**CVE prioritization:**
- Do not simply sort by CVSS score — that produces too many "critical" findings
- Compute a risk-adjusted priority score using:
  - CVSS base score (0–10)
  - EPSS score from `api.first.org/epss` (probability of exploitation in next 30 days)
  - CISA KEV (Known Exploited Vulnerabilities): +50 point bonus if actively exploited
  - Internet exposure: is the workload running behind a public load balancer? (+30%)
  - Data sensitivity: does the workload have access to a database with PII? (+20%)
  - Environment: production workloads weighted more heavily than dev
- Result: a "CloudVisor Priority Score" that is more actionable than raw CVSS

**Runtime agent (eBPF, optional):**
- Deploy as a Kubernetes DaemonSet or via Linux package manager (apt/yum)
- Monitor using Linux eBPF programs attached to kernel tracepoints:
  - Process execution: detect new process launches, compare against allowlist
  - Network connections: track outbound connections to unexpected destinations
  - File system writes: detect writes to sensitive paths (`/etc/passwd`, `/bin/`)
  - Syscall patterns: detect unusual syscall sequences (privilege escalation attempts)
- All events streamed to Kafka topic `cwpp.runtime_events`
- CDR service consumes `cwpp.runtime_events` for threat correlation

**File integrity monitoring:**
- For agent-deployed workloads: monitor a configurable set of critical file paths
- Alert on any modification to monitored files: hash change, permission change, owner change
- Use inotify (Linux) via the eBPF agent

#### APIs this module exposes

```
GET  /internal/cwpp/workloads              List all scanned workloads with vulnerability counts
GET  /internal/cwpp/workloads/{id}         Workload detail: all CVEs, risk scores, SBOM link
GET  /internal/cwpp/workloads/{id}/sbom    Download CycloneDX SBOM for a workload
GET  /internal/cwpp/images                 List all scanned container images
GET  /internal/cwpp/images/{id}            Image vulnerability detail
POST /internal/cwpp/scans                  Trigger workload scan for an account
GET  /internal/cwpp/cves/{cve_id}          Get all workloads affected by a specific CVE
```

---

### 4.3 — Module 3: CI/CD Pipeline Security

#### Role

The CI/CD Security module shifts security left — embedding checks at the developer's
workstation and in the pipeline, before code ever reaches production. It catches
secrets, vulnerable dependencies, insecure IaC, and dangerous container images
at the moment they are introduced, not months later when they become a breach.

This is also CloudVisor's product-led growth (PLG) engine. The `cloudvisor scan` CLI
is free, open-source, and works without a CloudVisor account. Developers install it
because it helps them. Their usage generates awareness in their organizations. Security
teams buy the full platform because they want centralized visibility into what the
CLI found across all their developers.

#### Key tasks and behaviors

**`cloudvisor scan` CLI (open source, offline-capable):**
- Single binary (Python packaged with PyInstaller or published to pip)
- Works fully offline for basic scans (SAST, secrets, IaC) — no account required
- With account connected: sends results to CloudVisor for centralized tracking
- Scan types triggered by target:
  - `cloudvisor scan .` → SAST + secrets scan + SCA + IaC scan (auto-detected)
  - `cloudvisor scan image myapp:latest` → container image scan
  - `cloudvisor scan iac ./terraform/` → IaC scan only
- Output formats: `--format table` (human), `--format json`, `--format sarif` (for GitHub)
- Exit codes: `0` = no findings above threshold, `1` = findings at or above `--fail-on` level

**SAST (Static Application Security Testing):**
- Powered by Semgrep with 2,000+ rules for Python, JavaScript, TypeScript, Go, Java, Ruby
- Detect: SQL injection, command injection, hardcoded credentials, insecure deserialization,
  XSS, path traversal, SSRF, XXE, insecure crypto, known-vulnerable function usage
- Respect `.semgrepignore` files in the repo
- Support custom Semgrep rules stored in org's custom rules directory

**Secrets detection:**
- Powered by TruffleHog v3 with entropy analysis + pattern matching
- Detect: AWS Access Keys, GitHub tokens, Stripe keys, Slack tokens, private keys,
  connection strings, JWT secrets, generic high-entropy strings
- Scan: current working tree + full git history (configurable: `--scan-history`)
- Respect `.trufflehogignore` for whitelisted false-positives

**SCA (Software Composition Analysis):**
- Scan all package manifests in the repository:
  `package.json`, `package-lock.json`, `requirements.txt`, `poetry.lock`,
  `go.mod`, `pom.xml`, `build.gradle`, `Gemfile.lock`, `Cargo.toml`
- Cross-reference dependencies against OSV + GitHub Advisory Database + NVD
- Report: vulnerable package name, installed version, fixed version, CVE ID, severity
- License scanning: flag GPL-3.0, AGPL-3.0, LGPL in commercial repositories

**IaC scanning:**
- Terraform: scan `.tf` files using Checkov + custom OPA rules from `/rules/rego/iac/terraform/`
- Helm: scan `values.yaml` + templates using custom OPA rules
- CloudFormation: scan YAML/JSON templates
- Pulumi: scan Python/TypeScript Pulumi programs
- Ansible: scan playbooks for common security anti-patterns
- Detect: public security groups, unencrypted storage, missing logging, default VPC usage,
  IAM wildcard permissions, missing KMS encryption, public RDS instances

**Container image scanning:**
- Powered by Trivy for CVE detection in OS packages and language libraries
- Scan Dockerfiles: detect `USER root`, `--no-check-certificate`, `curl | bash` patterns
- Generate SBOM in CycloneDX format as a pipeline artifact
- Registry scanning: scan images already in ECR/ACR/GCR on a schedule (not just at build time)

**Supply chain security:**
- SBOM generation: produce CycloneDX SBOM for every scanned artifact
- Sigstore: verify artifact signatures in the pipeline; sign outbound artifacts
- SLSA provenance: generate and verify SLSA provenance attestations
- Dependency confusion detection: flag packages that could be hijacked via public registry
- Typosquatting detection: flag packages with names similar to popular packages

**CI/CD native integrations:**
- GitHub Actions: `cloudvisor/scan-action@v1` — available in GitHub Marketplace
- GitLab CI: shareable `.cloudvisor-scan.yml` include template
- Jenkins: Shared Library with `cloudvisorScan()` step
- Azure DevOps: Extension in Azure Marketplace with pipeline task
- CircleCI: Orb published to CircleCI Registry
- Tekton: ClusterTask definition
- Each integration: configurable gate mode (advisory / soft / hard)

**Developer feedback:**
- GitHub PR annotations: post inline comments on the exact file + line of each finding
- VS Code extension: real-time SAST + secrets scan as you type (Language Server Protocol)
- Auto-fix PRs: for findings with known fixes (e.g., bump a dependency version),
  automatically open a PR with the fix applied (uses GitHub/GitLab API)

**Centralized results (when account connected):**
- CLI sends scan results to CloudVisor API after each scan
- Results stored and deduplicated like any other module's findings
- Dashboard shows CI/CD findings alongside cloud infrastructure findings
- Trend view: is the number of secrets in code increasing or decreasing over time?

#### APIs this module exposes

```
POST /internal/cicd/results          Submit scan results from CLI (authenticated)
GET  /internal/cicd/results          List all CI/CD scan results for an org
GET  /internal/cicd/results/{id}     Get specific scan result detail
GET  /internal/cicd/pipelines        List pipelines that have run scans
GET  /internal/cicd/trends           Trend data: findings over time by type
```

---

### 4.4 — Module 4: CIEM (Cloud Infrastructure Entitlement Management)

#### Role

Identity misconfigurations are the leading cause of cloud breaches. CIEM answers
the most dangerous question in cloud security: "Who can do what to which resources —
and should they be allowed to?" It builds a complete permissions graph across all
cloud providers, identifies identities with excessive access, detects privilege
escalation paths, and automatically generates least-privilege policy replacements.

#### Key tasks and behaviors

- Pull all IAM data from the Asset Graph: users, roles, policies, groups, service accounts
- For AWS: resolve effective permissions by processing: identity-based policies +
  resource-based policies + SCPs + permission boundaries → net effective permissions per resource
- For Azure: resolve effective permissions from RBAC role assignments +
  management group inheritance + deny assignments
- For GCP: resolve effective permissions from IAM bindings at project/folder/org level +
  service account impersonation chains
- Build the "permissions graph" in Neo4j (separate from but linked to the asset graph):
  nodes = identities + resources, edges = `CAN_READ`, `CAN_WRITE`, `CAN_DELETE`, `CAN_ADMIN`

**Over-permission detection:**
- Analyze CloudTrail/Activity Log/Audit Log for last-used data per API call per identity
- Identify permissions granted but not used in the last 90 days
- Classify identities: `least-privileged` / `over-privileged` / `severely-over-privileged`
- Severity: flag any identity with admin access that has not used admin permissions in 90 days

**Privilege escalation detection:**
- Find paths in the permissions graph where a low-privilege identity can gain higher privilege:
  - `iam:AttachRolePolicy` permission → can attach any policy to any role (including admin)
  - `iam:PassRole` → can pass a privileged role to a service
  - `iam:CreatePolicyVersion` → can update existing policies
- Enumerate all known privilege escalation techniques (from Rhino Security Labs research)
- Flag each escalation path with the minimum steps required

**Least-privilege policy generation:**
- For any over-privileged IAM identity, generate a replacement policy
- Use actual usage data (CloudTrail API calls for last 90 days) to determine needed permissions
- Output: a valid AWS IAM policy JSON, Azure role definition JSON, or GCP role YAML
- Present for human review before applying; optionally apply automatically

**Cross-cloud identity correlation:**
- When a workload spans AWS + Azure (e.g., EC2 instances syncing data to Azure Blob):
  correlate the AWS service role with the Azure service principal
  to understand the full cross-cloud permission surface

**Service account risk scoring:**
- Score every service account and machine identity on:
  - Permissions scope (narrow = low risk, admin = critical)
  - Last rotation date of credentials/keys
  - Whether key file was downloaded (GCP) / static credentials created (AWS access keys)
  - Number of resources the identity has access to

#### APIs this module exposes

```
GET  /internal/ciem/identities              List all IAM identities with risk scores
GET  /internal/ciem/identities/{id}         Identity detail: effective permissions, last used
GET  /internal/ciem/identities/{id}/paths   Privilege escalation paths from this identity
GET  /internal/ciem/over-privileged         List over-privileged identities above threshold
GET  /internal/ciem/permissions-graph       Export the full permissions graph
POST /internal/ciem/remediate/{id}          Generate least-privilege replacement policy
GET  /internal/ciem/escalation-paths        All detected privilege escalation paths
```

---

### 4.5 — Module 5: KSPM (Kubernetes Security Posture Management)

#### Role

KSPM provides continuous security auditing for Kubernetes clusters, wherever they run:
managed (EKS, AKS, GKE) or self-hosted (OpenShift, Rancher, kubeadm). It audits
cluster configuration, workload security, network policies, RBAC, and container images.

KSPM works by connecting to the Kubernetes API Server (read-only) — no agent required.
For on-premises clusters, a network-accessible Kubernetes API is sufficient.

#### Key tasks and behaviors

- Connect to Kubernetes clusters via kubeconfig or in-cluster service account (read-only)
- Enumerate: Namespaces, Pods, Deployments, DaemonSets, StatefulSets, Services, Ingresses,
  ConfigMaps, Secrets, ServiceAccounts, Roles, ClusterRoles, RoleBindings,
  ClusterRoleBindings, NetworkPolicies, PodSecurityPolicies/PodSecurityAdmission, Nodes
- Evaluate all K8s objects through the OPA policy engine (rules in `/rules/rego/kspm/`)

**Audit coverage:**
- Cluster-level: API server flags (--anonymous-auth, --insecure-port, --authorization-mode),
  etcd encryption at rest, audit logging enabled, admission controllers configured
- Pod security: containers running as root, privileged containers, host network/PID/IPC
  access, missing read-only root filesystem, writable hostPath mounts, missing resource limits
- RBAC: wildcard permissions (`*`), cluster-admin bound to service accounts,
  default service account auto-mounting tokens, overly-broad role bindings
- Network: pods without NetworkPolicy (default-deny not configured), services with
  `type: LoadBalancer` exposing sensitive services, unrestricted ingress/egress
- Image security: images without digest pinning (`:latest` tag), images from untrusted
  registries, images with critical CVEs (CWPP integration)
- Secrets management: secrets mounted as env vars vs. volume mounts vs. external secrets operator

**Runtime admission webhook (optional):**
- Deploy a Kubernetes ValidatingAdmissionWebhook that calls the CloudVisor policy engine
- Block pods at creation time if they violate hard security policies (e.g., root container)
- Log and alert on soft violations without blocking

**CIS Kubernetes Benchmark:**
- Map all KSPM checks to the CIS Kubernetes Benchmark controls
- Generate a compliance report: pass/fail per control, downloadable as PDF

#### APIs this module exposes

```
POST /internal/kspm/clusters         Register a Kubernetes cluster
GET  /internal/kspm/clusters         List registered clusters with posture scores
GET  /internal/kspm/clusters/{id}    Cluster detail: node count, namespace count, finding breakdown
POST /internal/kspm/clusters/{id}/scan  Trigger on-demand cluster scan
GET  /internal/kspm/workloads        List all pods/deployments with security issues
GET  /internal/kspm/rbac             RBAC analysis: over-privileged roles and bindings
```

---

### 4.6 — Module 6: DSPM (Data Security Posture Management)

#### Role

DSPM answers the questions every compliance team dreads: "Where is our sensitive data?
Who can access it? Is any of it exposed to the internet?" It discovers all cloud data
stores, classifies their contents for sensitivity, maps access permissions, and scores
data risk — enabling GDPR Article 30 registers, HIPAA data asset inventories,
and PCI-DSS CDE scoping to be produced automatically.

#### Key tasks and behaviors

- Discover all data stores from the Asset Graph:
  AWS S3, RDS, DynamoDB, Redshift, Glue; Azure Blob, Azure SQL, Cosmos DB, Synapse;
  GCP Cloud Storage, Cloud SQL, BigQuery, Firestore; OCI Object Storage, Autonomous DB
- For each data store: sample a representative subset of data (not full scan by default)
- Classify sampled data using Microsoft Presidio (open source PII detection):
  - PII: names, emails, phone numbers, national ID numbers, passports
  - PHI: health records, diagnoses, medication data
  - PCI: credit card numbers, CVV, cardholder names
  - Credentials: API keys, passwords, connection strings embedded in data
  - Financial: bank account numbers, SWIFT codes, tax IDs
- Store classification results in Neo4j: add `DataClassification` nodes linked to data store nodes
- Compute data risk score per store:
  `risk = sensitivity_score × exposure_score × access_breadth_score`
- Alert when a previously-private sensitive store becomes public
- Generate GDPR Article 30 processing activity register from discovered data stores
- Map PCI-DSS cardholder data environment (CDE) based on stores containing PCI data

#### APIs this module exposes

```
GET  /internal/dspm/datastores             List all discovered data stores with risk scores
GET  /internal/dspm/datastores/{id}        Detail: classification results, access map, risk score
GET  /internal/dspm/sensitive              All data stores containing sensitive data
GET  /internal/dspm/exposed               Sensitive stores with public access
GET  /internal/dspm/reports/gdpr-art30    Generate GDPR Article 30 register
GET  /internal/dspm/reports/pci-cde       Generate PCI CDE scoping report
```

---

### 4.7 — Module 7: CDR (Cloud Detection & Response)

#### Role

CDR is the active defense module. While CSPM, CWPP, and CIEM find security problems
in the configuration and posture of cloud infrastructure, CDR detects threats as
they happen. It ingests cloud activity logs in real time, builds behavioral baselines
for every identity and workload, and detects deviations that indicate active attacks:
account compromise, data exfiltration, lateral movement, crypto mining, and more.

CDR requires at least 2–4 weeks of behavioral baseline data before it produces
high-quality detections. This is why it is built in Phase 3 — it needs real customer
traffic from earlier modules before it can be effective.

#### Key tasks and behaviors

**Log ingestion and normalization:**
- Stream CloudTrail events (S3/SQS delivery or Kinesis Firehose)
- Stream Azure Monitor activity logs and Azure Defender alerts via Event Hub
- Stream GCP Audit Logs via GCP Pub/Sub
- Stream Kubernetes audit logs from each registered cluster
- Stream VPC Flow Logs, DNS query logs, WAF logs
- Normalize all events into a common CloudVisor log schema (similar to ECS — Elastic Common Schema)
- Store in Elasticsearch with 30-day hot tier retention, 90-day warm tier

**Behavioral baseline construction:**
- For each unique IAM identity (user, role, service account): build a behavioral model capturing:
  - API calls made (which services, which actions)
  - Time-of-day and day-of-week patterns
  - Source IP address ranges and geographic regions
  - Resources accessed (which S3 buckets, which EC2 instances)
  - Data volume accessed (bytes downloaded per session)
- For each workload: build a model of normal network connections, process executions
- Models trained using Isolation Forest (scikit-learn) with 2-week rolling window
- Retrain models nightly on the previous 14 days of data

**UEBA (User and Entity Behavior Analytics):**
- After baseline is established, evaluate every new log event against the identity's model
- Anomaly triggers (examples):
  - API call from a geographic region the identity has never accessed from
  - API calls at 3am when the identity only ever acts during business hours
  - Download of 10GB from S3 when the identity's max was previously 100MB
  - New IAM role assumption that is not in the identity's normal pattern
  - Use of a rarely-used (or never-used) API action

**Pre-built threat detections (MITRE ATT&CK Cloud Matrix):**
```
Initial Access:    Publicly exposed service exploitation, stolen credential use, phishing simulation
Execution:         Lambda invocation from unusual source, EC2 user-data execution
Persistence:       New IAM user creation, new API key generation, backdoor Lambda, new admin role
Privilege Escalation: IAM policy attachment, PassRole to privileged role, STS AssumeRole chain
Defense Evasion:   CloudTrail logging disabled, GuardDuty disabled, Security Hub suppressed
Credential Access: Secrets Manager GetSecretValue spike, SSM Parameter Store bulk read
Discovery:         Enumerate all S3 buckets, describe all EC2 instances, list all IAM users
Lateral Movement:  Unusual AssumeRole to cross-account role, new VPC peering
Collection:        Mass S3 GetObject (>1000 objects in 10 minutes), RDS snapshot export
Exfiltration:      Unusual data volume to external IP, S3 bucket replication to external account
Impact:            EC2 instance termination in bulk, S3 object deletion, database deletion
```

**Incident management:**
- Group correlated detections into incidents (same attacker, same attack campaign)
- Assign incidents to team members
- Track incident lifecycle: `detected` → `investigating` → `contained` → `resolved`
- Timeline view: chronological reconstruction of all events in an incident

**Automated response playbooks:**
- Pre-built playbooks (require human approval by default, can be set to auto-execute):
  - Compromised IAM user: revoke all active sessions, disable access key, enforce MFA reset
  - Compromised EC2 instance: isolate (modify security group to deny all traffic), create snapshot
  - Data exfiltration: revoke the IAM role, block the source IP in WAF
  - Crypto miner detected: terminate the instance, create forensic snapshot first
- Playbook steps are documented and logged for compliance/forensic purposes

**Threat intelligence integration:**
- Ingest STIX/TAXII feeds (AlienVault OTX, abuse.ch, Emerging Threats)
- Extract IOCs: malicious IPs, domains, file hashes, URL patterns
- Match IOCs against log streams in real time using Elasticsearch percolator queries
- Alert immediately when a CloudVisor customer's infrastructure contacts a known malicious endpoint

#### Kafka events this module produces

```
Topic: cdr.detection             # An anomaly or rule-based detection fired
Topic: cdr.incident.created      # Multiple detections grouped into an incident
Topic: cdr.incident.updated      # Incident status or investigation notes changed
Topic: cdr.playbook.executed     # An automated response playbook was triggered
```

#### Kafka events this module consumes

```
Topic: cwpp.runtime_events   → runtime threat correlation
Topic: asset.updated         → update behavioral context for detections
Topic: audit.events          → user action audit correlation
```

---

### 4.8 — Module 8: AIOps Intelligence Layer

#### Role

AIOps is not a separate product customers use directly — it is a cross-cutting
intelligence layer that makes every other module smarter. It consumes data from
all modules and uses ML and LLMs to: reduce alert noise dramatically, prioritize
the findings that matter most, explain findings in plain English, generate fixes
automatically, detect attack paths, and answer natural language questions about
the customer's security posture.

This module has two sub-services: `aiops` (ML pipeline, Python) and `copilot` (LLM/RAG, Python).

#### 8.1 — Noise Reduction & Alert Correlation

**Tasks:**
- Consume all `finding.created` events from Kafka
- Apply DBSCAN clustering: group findings with similar features into clusters
  (same resource type + same rule category + same account = same cluster)
- Represent each cluster as one incident rather than N individual alerts
- Train a false-positive suppression model:
  - Features: rule_id, resource_type, account, environment, time_of_day, tags
  - Label: finding was resolved as `false_positive` (user feedback)
  - Model: gradient boosting classifier (XGBoost)
  - Auto-suppress findings above the false-positive probability threshold (configurable)
- Retrain model weekly on accumulated feedback data

**Goal:** Reduce raw alert volume by 80–90% while missing fewer than 1% of real threats.

#### 8.2 — Contextual Risk Prioritization

**Tasks:**
- For every new finding, compute a CloudVisor Priority Score (0–100):
```python
def compute_priority_score(finding: Finding, asset: CloudResource) -> float:
    score = 0.0

    # CVSS base score contribution (max 40 pts)
    score += (finding.cvss_score / 10.0) * 40

    # EPSS exploit probability (max 20 pts)
    epss = fetch_epss(finding.cve_id)  # from api.first.org
    score += epss * 20

    # CISA KEV (active exploitation)
    if is_in_kev(finding.cve_id):
        score += 25

    # Internet exposure
    if asset.is_internet_exposed:
        score *= 1.3

    # Data sensitivity
    if asset.contains_sensitive_data:
        score *= 1.2

    # Environment
    env_multipliers = {"prod": 1.5, "staging": 1.0, "dev": 0.6}
    score *= env_multipliers.get(asset.environment, 1.0)

    return min(score, 100.0)
```
- Write `priority_score` back to the finding record
- Emit `finding.priority_scored` event so the dashboard can sort by priority

#### 8.3 — Attack Path Analysis

**Tasks:**
- Periodically (every hour and on significant graph changes) run attack path computation:
- Identify all internet-accessible entry points in the asset graph (public IPs, public S3, public ALBs)
- From each entry point, run Neo4j graph traversal (BFS, max 8 hops)
- Look for paths that lead to "crown jewel" assets: production databases, secrets stores,
  assets tagged `criticality=high`, assets containing PII
- Store found paths as `AttackPath` nodes in Neo4j
- Score each path by: number of hops (fewer = higher risk), severity of misconfigs along the path,
  sensitivity of the target asset
- Expose attack paths via API and visualize as interactive graph in the UI
- "What if" simulation: given a resource ID, show all paths that lead through it
  (blast radius if that resource is compromised)

#### 8.4 — Security Copilot (LLM + RAG)

**Tasks:**
- Provide a natural language interface to CloudVisor's data (`POST /v1/copilot/query`)
- Architecture: RAG (Retrieval Augmented Generation) pipeline:
  1. User sends a natural language query
  2. Embed the query using a text embedding model
  3. Retrieve relevant context from: asset graph (via GraphQL), findings (via Elasticsearch),
     compliance posture (via Policy API), recent changes (via audit log)
  4. Construct a prompt including the retrieved context + user query
  5. Call Anthropic Claude API (claude-sonnet-4-6 model) with the constructed prompt
  6. Parse the response and return structured answer with citations

**Example queries the copilot must handle:**
- `"Which of our production workloads have critical CVEs and are internet-facing?"`
  → Query graph for internet-exposed prod workloads + query CWPP for critical CVEs + correlate
- `"Show me all IAM roles that can access our payments RDS database"`
  → Cypher traversal: `MATCH (role:IAMRole)-[:HAS_ACCESS_TO]->(db:RDSInstance {name: 'payments'})`
- `"What changed in our AWS environment in the last 24 hours?"`
  → Query audit log + `asset.updated` events for the last 24 hours
- `"Explain this finding in plain English and tell me how to fix it"`
  → Retrieve finding + rule metadata + context, ask Claude to explain in simple terms
- `"Generate a SOC 2 Type II evidence report for our logging controls"`
  → Query compliance API for logging control pass/fail + retrieve evidence + format as report

**Prompt safety:**
- The copilot must never execute destructive operations — it is read-only
- All data it returns must be scoped to the requesting organization (RLS enforced at retrieval)
- Log every copilot query and response for audit purposes

#### 8.5 — Auto-Remediation

**Tasks:**
- For each finding, check if an auto-fix is available (stored in rule metadata: `auto_fix_available: true`)
- When requested (user clicks "Generate fix" or API call): send finding context to Claude API
- System prompt:
  ```
  You are a cloud security remediation specialist. Given a security finding, generate
  the exact configuration fix required. Output only valid, directly applicable code
  (Terraform, IAM policy JSON, K8s YAML, CLI command). Include a brief explanation
  of why this fix addresses the security issue. Never invent configurations — only
  use settings that exist in the official documentation for the service.
  ```
- Parse the LLM response, extract the fix code
- If the finding is in IaC (Terraform/Helm): offer to open a PR against the customer's
  Git repo via GitHub/GitLab API with the fix applied
- Track: was the PR opened? was it merged? did the finding resolve after merge?

---

## 5. Data Models

### 5.1 Core PostgreSQL Schema

```sql
-- =============================================================
-- Organizations (tenants) — foundational table, no org_id FK
-- =============================================================
CREATE TABLE organizations (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name         TEXT        NOT NULL,
  slug         TEXT        NOT NULL UNIQUE,
  plan         TEXT        NOT NULL DEFAULT 'free'
                           CHECK (plan IN ('free','starter','growth','enterprise')),
  max_accounts INT         NOT NULL DEFAULT 1,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
-- Users
-- =============================================================
CREATE TABLE users (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  email           TEXT        NOT NULL UNIQUE,
  name            TEXT,
  password_hash   TEXT,                  -- null if SSO-only
  role            TEXT        NOT NULL DEFAULT 'viewer'
                              CHECK (role IN ('owner','admin','security_engineer','devops','viewer','auditor')),
  mfa_enabled     BOOLEAN     NOT NULL DEFAULT FALSE,
  mfa_secret      TEXT,                  -- TOTP secret, encrypted at rest
  last_login_at   TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON users
  USING (organization_id = current_setting('app.current_org_id')::UUID);

-- =============================================================
-- Cloud accounts (connector config per tenant)
-- =============================================================
CREATE TABLE cloud_accounts (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID       NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider       TEXT        NOT NULL CHECK (provider IN ('aws','azure','gcp','oci')),
  account_id     TEXT        NOT NULL,  -- AWS Account ID / Azure Subscription / GCP Project / OCI Tenancy
  name           TEXT,
  status         TEXT        NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending','active','error','paused','auth_failed')),
  error_message  TEXT,
  last_synced_at TIMESTAMPTZ,
  resource_count INT         NOT NULL DEFAULT 0,
  polling_interval_minutes INT NOT NULL DEFAULT 15,
  vault_secret_path TEXT,               -- Path in HashiCorp Vault where credentials are stored
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(organization_id, provider, account_id)
);
ALTER TABLE cloud_accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON cloud_accounts
  USING (organization_id = current_setting('app.current_org_id')::UUID);

-- =============================================================
-- Findings — central findings table, written by Alert Pipeline
-- =============================================================
CREATE TABLE findings (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id  UUID        NOT NULL REFERENCES organizations(id),
  cloud_account_id UUID        NOT NULL REFERENCES cloud_accounts(id),
  module           TEXT        NOT NULL CHECK (module IN ('cspm','cwpp','ciem','kspm','dspm','cdr','cicd')),
  rule_id          TEXT        NOT NULL,
  resource_id      TEXT        NOT NULL,  -- CloudVisor CDM UUID
  cloud_resource_id TEXT       NOT NULL,  -- AWS ARN / Azure ID etc.
  severity         TEXT        NOT NULL CHECK (severity IN ('CRITICAL','HIGH','MEDIUM','LOW','INFO')),
  title            TEXT        NOT NULL,
  description      TEXT,
  remediation      TEXT,
  compliance       TEXT[]      NOT NULL DEFAULT '{}',
  status           TEXT        NOT NULL DEFAULT 'open'
                               CHECK (status IN ('open','in_progress','resolved','suppressed','accepted_risk')),
  fingerprint      TEXT        NOT NULL UNIQUE,  -- SHA-256 for deduplication
  priority_score   NUMERIC(5,2),               -- 0-100, computed by AIOps
  risk_score       NUMERIC(5,2),               -- 0-100, from asset graph
  assignee_id      UUID        REFERENCES users(id),
  first_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at      TIMESTAMPTZ,
  regression_count INT         NOT NULL DEFAULT 0,
  context          JSONB       NOT NULL DEFAULT '{}',
  CONSTRAINT findings_org_rls CHECK (true)
);
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON findings
  USING (organization_id = current_setting('app.current_org_id')::UUID)
  WITH CHECK (organization_id = current_setting('app.current_org_id')::UUID);
CREATE INDEX idx_findings_org_status ON findings(organization_id, status);
CREATE INDEX idx_findings_org_severity ON findings(organization_id, severity);
CREATE INDEX idx_findings_fingerprint ON findings(fingerprint);

-- =============================================================
-- Finding history — every state transition recorded
-- =============================================================
CREATE TABLE finding_history (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  finding_id  UUID        NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
  from_status TEXT,
  to_status   TEXT        NOT NULL,
  changed_by  UUID        REFERENCES users(id),
  note        TEXT,
  changed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
-- Incidents — groups of correlated findings
-- =============================================================
CREATE TABLE incidents (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID        NOT NULL REFERENCES organizations(id),
  title           TEXT        NOT NULL,
  description     TEXT,
  status          TEXT        NOT NULL DEFAULT 'open'
                              CHECK (status IN ('open','investigating','contained','resolved')),
  severity        TEXT        NOT NULL,  -- highest severity among linked findings
  assignee_id     UUID        REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at     TIMESTAMPTZ
);
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON incidents
  USING (organization_id = current_setting('app.current_org_id')::UUID);

CREATE TABLE incident_findings (
  incident_id UUID NOT NULL REFERENCES incidents(id),
  finding_id  UUID NOT NULL REFERENCES findings(id),
  PRIMARY KEY (incident_id, finding_id)
);

-- =============================================================
-- Audit log — append-only, never update or delete rows
-- =============================================================
CREATE TABLE audit_log (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID        NOT NULL REFERENCES organizations(id),
  user_id         UUID        REFERENCES users(id),
  action          TEXT        NOT NULL,  -- e.g. "finding.status_changed"
  resource_type   TEXT,
  resource_id     TEXT,
  ip_address      INET,
  user_agent      TEXT,
  metadata        JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- No RLS on audit_log — only accessible to owner/admin roles via application logic
-- No DELETE or UPDATE ever issued against this table
```

---

## 6. Kafka Topic Registry

All topics use Avro schemas registered in Confluent Schema Registry.
Topic naming convention: `{domain}.{event_name}` (snake_case, past tense for events).

| Topic | Producer | Consumers | Description |
|---|---|---|---|
| `resource.discovered` | connector | graph, cspm, cwpp, ciem | New cloud resource found |
| `resource.updated` | connector | graph, cspm, cwpp | Existing resource changed |
| `resource.deleted` | connector | graph, alert | Resource no longer exists |
| `connector.health_changed` | connector | alert, api | Connector status changed |
| `asset.created` | graph | elasticsearch-sync | Graph node created |
| `asset.updated` | graph | cdr, aiops | Graph node updated |
| `asset.risk_score_changed` | graph | alert, api | Risk score updated |
| `asset.relationship_changed` | graph | ciem, cdr, aiops | Edge added/removed |
| `finding.raw` | policy, cdr | alert | Raw undeduped finding |
| `finding.created` | alert | aiops, api, copilot | Deduped finding persisted |
| `finding.updated` | alert | api | Finding status/context changed |
| `finding.resolved` | alert | api, aiops | Finding resolved |
| `finding.suppressed` | alert | api | Finding suppressed |
| `incident.created` | alert, aiops | api | Incident created |
| `cdr.detection` | cdr | alert, aiops | CDR anomaly/rule fired |
| `cwpp.runtime_events` | cwpp-agent | cdr, aiops | eBPF runtime events from workload |
| `audit.events` | auth, api, all | alert | User and system audit events |
| `notification.sent` | alert | api | Notification dispatched |
| `rule.updated` | policy | all modules | Rule added/changed/disabled |

---

## 7. API Design Standards

```
Base URL:     https://api.cloudvisor.io/v1
Auth:         Authorization: Bearer <JWT>  OR  X-API-Key: cv_live_<key>
Content-Type: application/json
API Version:  Passed via Accept: application/vnd.cloudvisor.v1+json

Standard response envelope (ALL endpoints must use this):
{
  "data": <payload | null>,
  "meta": {
    "request_id": "req_01HXK2...",        // unique per request, for support
    "next_cursor": "eyJpZCI6IjEyMyJ9",    // null if no more pages
    "total": 1247,                         // total matching records (estimated for large sets)
    "took_ms": 48                          // server processing time in ms
  },
  "errors": []
}

Standard error format:
{
  "data": null,
  "errors": [
    {
      "code": "FINDING_NOT_FOUND",          // machine-readable, SCREAMING_SNAKE_CASE
      "message": "Finding '123' not found", // human-readable, never expose internal details
      "field": null                          // field name if a validation error
    }
  ]
}

HTTP status codes:
  200 OK                  — successful read
  201 Created             — successful create
  202 Accepted            — async operation started (returns job ID)
  204 No Content          — successful delete
  400 Bad Request         — validation error (include field errors)
  401 Unauthorized        — missing or invalid token
  403 Forbidden           — valid token but insufficient permissions
  404 Not Found           — resource does not exist (or not visible to this tenant)
  409 Conflict            — duplicate resource (e.g. duplicate fingerprint)
  422 Unprocessable Entity — semantic validation error
  429 Too Many Requests   — rate limit exceeded (include Retry-After header)
  500 Internal Server Error — unexpected server error (log, never expose stack traces)

Pagination: Always cursor-based. Never offset-based.
  Request:  GET /v1/findings?cursor=eyJpZCI6IjEyMyJ9&per_page=50
  Response: meta.next_cursor contains the next page cursor (null if last page)

Filtering:  GET /v1/findings?filter[severity]=CRITICAL&filter[status]=open
Sorting:    GET /v1/findings?sort=-priority_score,first_seen_at
            (prefix - = descending, no prefix = ascending, multiple fields comma-separated)
```

---

## 8. Security Requirements for CloudVisor Itself

CloudVisor is a security company. Its platform must be hardened beyond standard practices.

- All data encrypted at rest (AES-256); all data in transit encrypted (TLS 1.3 minimum)
- Credentials: stored exclusively in HashiCorp Vault. Never in environment variables, code, or DB.
- Customer cloud credentials: envelope-encrypted using a KMS key per organization
  (even Vault operators cannot read plaintext credentials without the org-specific KMS key)
- OWASP Top 10: mitigations implemented and verified via DAST in CI pipeline
- Dependency scanning: every PR scanned by Snyk + the CloudVisor CLI itself (dogfooding)
- SAST: Semgrep runs on every PR in GitHub Actions
- Secrets scanning: TruffleHog runs on every commit
- Container images: Trivy scans every Docker image in CI before push to registry
- Penetration test: commissioned before the first customer is onboarded
- SOC 2 Type I: target certification within 6 months of first customer
- Vulnerability Disclosure Policy (VDP): published at `cloudvisor.io/security`
- Bug bounty program: launched when 10+ customers are active

---

## 9. Build Order

Follow this sequence strictly. Do not start work on a later item before the earlier
item is fully implemented (code complete), tested (80%+ coverage), and documented
(README + OpenAPI spec).

```
═══════════════════════════════════════════════════════════
 PHASE 0 — Foundation (Weeks 1–8)
 Goal: All shared infrastructure. No security features yet.
═══════════════════════════════════════════════════════════

 [1] services/connector   — Cloud connector & asset ingestion (AWS first, then Azure/GCP/OCI)
 [2] services/graph       — Asset graph service (Neo4j)
 [3] services/auth        — Multi-tenant auth & RBAC (Keycloak integration)
 [4] services/policy      — OPA policy engine + initial rule library (100 AWS CSPM rules)
 [5] services/alert       — Alert pipeline & notification engine (Slack + Jira + webhook)
 [6] apps/web + services/api  — Dashboard UI (MVP pages) + Public REST API

 Milestone: Deploy to staging. Connect one AWS account. See resources in dashboard.

═══════════════════════════════════════════════════════════
 PHASE 1 — First Revenue (Weeks 9–18)
 Goal: Ship CSPM. Get first paying customers.
═══════════════════════════════════════════════════════════

 [7] services/cspm        — CSPM module (500+ rules, compliance dashboards, PDF reports)
 [8] rules/rego/cspm/     — Complete rule library for CIS AWS, CIS Azure, CIS GCP

 Milestone: Demo to 5 prospects. Close first paid contract.

═══════════════════════════════════════════════════════════
 PHASE 2 — Expansion (Weeks 19–30)
 Goal: Expand value. Upsell existing customers. Attract DevOps persona.
═══════════════════════════════════════════════════════════

 [9]  services/cicd       — CI/CD security module + cloudvisor CLI (publish to PyPI + GitHub)
 [10] services/cwpp       — CWPP agentless VM + container scanning
 [11] services/ciem       — CIEM identity & entitlements
 [12] Integration configs — Splunk, ServiceNow, PagerDuty, Microsoft Teams

 Milestone: 3 customers using 3+ modules. First enterprise renewal.

═══════════════════════════════════════════════════════════
 PHASE 3 — Intelligence & Moat (Weeks 31–48)
 Goal: Build retention. Competitive differentiation.
═══════════════════════════════════════════════════════════

 [13] services/aiops      — Noise reduction, risk prioritization, attack path analysis
 [14] services/copilot    — LLM security copilot (RAG pipeline, Claude API)
 [15] services/cdr        — Cloud Detection & Response (requires 2+ months of baseline data)
 [16] services/kspm       — Kubernetes security posture
 [17] services/dspm       — Data security & classification

 Milestone: NRR (net revenue retention) > 120%. AIOps reducing alert volume by 80%+.
```

---

## 10. LLM Coder Rules (Mandatory — Apply to Every Session)

1. **Tenant isolation is sacred.** Every DB query that touches tenant data must operate
   under an active RLS session (`SET LOCAL app.current_org_id`). If you write a raw SQL
   query that touches a tenant-scoped table without this context, it is a critical bug.

2. **No security logic in Python.** When you are about to write `if resource['PublicAccessBlockConfiguration']['BlockPublicAcls'] == False:` in Python — stop.
   Write a Rego rule in `/rules/rego/` instead and call the OPA engine.

3. **Services are independent.** `services/cspm/` must never `import` from `services/graph/`.
   Communication is via Kafka events or HTTP API calls only.

4. **Tests first, code second.** Write the test file before implementing the function.
   Unit tests mock all I/O (DB, Kafka, cloud APIs, external HTTP).
   Integration tests use Docker Compose with real PostgreSQL + Kafka + Redis + Neo4j.
   80% line coverage is the minimum bar, not the target.

5. **OpenAPI is generated, not written.** Use FastAPI's built-in OpenAPI generation.
   Decorate every route with full `summary`, `description`, `response_model`, `tags`.
   The spec must be complete enough that a developer can use the API without reading source code.

6. **Emit Kafka events for state changes.** Any time a service creates, updates, or
   resolves a significant object (finding, asset, incident, scan), it must publish a
   Kafka event. This is how AIOps and CDR get their data. Missing events = broken intelligence.

7. **The CLI is a first-class product.** `cloudvisor scan` must work offline without
   any account. Treat it as a product that developers love, not an internal tool.
   It must have a `--help` that explains every flag, clear error messages, and clean output.

8. **Every finding maps to compliance.** Before implementing any rule in Rego, look up
   which CIS controls, SOC 2 criteria, and other framework controls it covers.
   These must be in the rule's metadata annotations. A rule without compliance mappings is incomplete.

9. **Observability is not optional.** Every service must have:
   - Structured JSON logs to stdout with `correlation_id`, `organization_id`, `service_name`, `level`
   - Prometheus metrics exported at `/metrics` (request count, latency histograms, error rate, custom counters)
   - OpenTelemetry traces for all inbound HTTP requests and outbound Kafka publishes

10. **Performance targets are requirements, not aspirations.**
    - Asset graph query (1M nodes): p95 < 500ms
    - Policy evaluation (10K resources × 500 rules): < 30 seconds
    - Alert pipeline throughput: > 10,000 findings/second
    - All public API read endpoints: p95 < 200ms
    - Dashboard initial load: < 2 seconds (Lighthouse > 90)
    - Any endpoint that misses its target must include a GitHub Issue before merging.

---

*CloudVisor Master Engineering Prompt — Version 2.0*
*This document is the single source of truth for the CloudVisor platform.*
*All code written for CloudVisor must be consistent with this document.*
