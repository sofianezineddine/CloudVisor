# CloudVisor Architecture Diagrams

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                   External Cloud Providers                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │   AWS    │  │  Azure   │  │   GCP    │  │   OCI    │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└────────────────────┬──────────────────────────────────────────────┘
                     │
                     │ Cloud APIs (read-only)
                     │
        ┌────────────▼──────────────────────┐
        │  CloudVisor Platform (Docker)     │
        │                                    │
        ├────────────────────────────────────┤
        │  Presentation Layer                │
        │  ┌──────────────────────────────┐ │
        │  │  Next.js Frontend (3000)     │ │
        │  │  - Dashboard, Findings, etc. │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │  Nginx Reverse Proxy (8080)  │ │
        │  │  - HTTPS, routing, security  │ │
        │  └──────────────────────────────┘ │
        │                                    │
        ├────────────────────────────────────┤
        │  Microservices Layer               │
        │  ┌──────────────────────────────┐ │
        │  │ Connector (8000)              │ │
        │  │ - Cloud asset discovery       │ │
        │  │ - Multi-cloud resource sync   │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Auth (8002)                   │ │
        │  │ - JWT + API key auth          │ │
        │  │ - Multi-tenant RBAC           │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Graph (8001)                  │ │
        │  │ - Asset relationship graph    │ │
        │  │ - Risk scoring                │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Policy (8003)                 │ │
        │  │ - OPA/Rego rule evaluation    │ │
        │  │ - Security checks             │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Alert (8004)                  │ │
        │  │ - Finding deduplication       │ │
        │  │ - Notifications               │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ API Gateway (8005)            │ │
        │  │ - REST/GraphQL endpoints      │ │
        │  │ - Rate limiting               │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ CSPM (8006)                   │ │
        │  │ - Cloud posture checks        │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Copilot (8010)                │ │
        │  │ - RAG pipeline + Claude       │ │
        │  │ - AI security Q&A             │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ AI Router (8015)              │ │
        │  │ - LLM provider gateway        │ │
        │  │ - OpenAI/OpenRouter/NVIDIA   │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Keep (8007)                   │ │
        │  │ - Alert correlation           │ │
        │  │ - Incident grouping           │ │
        │  └──────────────────────────────┘ │
        │                                    │
        ├────────────────────────────────────┤
        │  Message Bus & Caching             │
        │  ┌──────────────────────────────┐ │
        │  │ Kafka (9092) - 20+ topics    │ │
        │  │ - assets, findings, events   │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Redis (6379) - 9 databases   │ │
        │  │ - Sessions, rate limiting    │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Soketi WebSocket (6001)      │ │
        │  │ - Real-time updates          │ │
        │  └──────────────────────────────┘ │
        │                                    │
        ├────────────────────────────────────┤
        │  Data Layer                        │
        │  ┌──────────────────────────────┐ │
        │  │ PostgreSQL (5432)            │ │
        │  │ - Multi-tenant data store    │ │
        │  │ - RLS policies               │ │
        │  │ - 15+ tables                 │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Neo4j (7687)                 │ │
        │  │ - Asset relationship graph   │ │
        │  │ - 2-5M nodes                 │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Elasticsearch (9200)         │ │
        │  │ - Full-text finding search   │ │
        │  │ - Aggregations               │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ OPA (8181)                   │ │
        │  │ - Policy evaluation engine   │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Vault (8200)                 │ │
        │  │ - Credential management      │ │
        │  │ - Encryption at rest         │ │
        │  └──────────────────────────────┘ │
        │                                    │
        └────────────────────────────────────┘
```

## Data Flow: Asset Discovery to Finding

```
User adds AWS account
        │
        ├─ Post /v1/accounts
        │
        ▼
┌─────────────────────────────────────┐
│  Auth Service (validate JWT)        │
│  - Check user permissions           │
│  - Verify organization              │
└────────────────┬────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Connector Service  │
        │ (port 8000)        │
        └────────┬───────────┘
                 │
                 ├─ 1. Read credentials from Vault
                 │   (e.g., /cloudvisor/credentials/aws-prod)
                 │
                 ├─ 2. Initialize AWS SDK
                 │
                 ├─ 3. Discover resources
                 │   - EC2 instances
                 │   - Security groups
                 │   - S3 buckets
                 │   - IAM roles
                 │   - RDS instances
                 │   - ...
                 │
                 ├─ 4. Normalize to Common Data Model
                 │   {
                 │     resource_id: "i-123",
                 │     resource_type: "aws::ec2::instance",
                 │     provider: "aws",
                 │     tags: {Environment: "prod"},
                 │     raw: {...full AWS response...}
                 │   }
                 │
                 ├─ 5. Publish to Kafka topic: assets.discovered
                 │
                 ▼
         ┌──────────────────┐
         │ Kafka Topic      │
         │ assets.discovered│
         └────┬─────────────┘
              │
              ├──────────────────────────┬─────────────────────────────┐
              │                          │                             │
              ▼                          ▼                             ▼
    ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
    │ Graph Service       │  │ Policy Service      │  │ (Future: ML Engine) │
    │ (port 8001)         │  │ (port 8003)         │  │                     │
    └────────┬────────────┘  └────────┬────────────┘  └─────────────────────┘
             │                        │
             │                        ├─ 1. Load Rego rules from disk
             │                        │
             │                        ├─ 2. Package asset as JSON
             │                        │
             │                        ├─ 3. Call OPA POST /v1/compile
             │                        │
             │                        ├─ 4. OPA evaluates rules
             │                        │    deny[finding] {
             │                        │      input.resource_type == "aws::ec2"
             │                        │      input.raw.SecurityGroups[*].IpPermissions[?fromPort == 22 && cidrIp == "0.0.0.0/0"]
             │                        │      finding := {...}
             │                        │    }
             │                        │
             │                        ├─ 5. Return violations
             │                        │
             │                        └─ 6. Publish to Kafka: finding.raw
             │                               [
             │                                 {rule_id: "ec2-ssh-open", severity: "HIGH"}
             │                               ]
             │
             ├─ 1. Create Neo4j node
             │    (:EC2Instance {resource_id: "i-123", ...})
             │
             ├─ 2. Create relationships
             │    EC2Instance -[:ATTACHED_TO]-> SecurityGroup
             │    SecurityGroup -[:ALLOWS_INBOUND]-> CIDR(0.0.0.0/0)
             │
             ├─ 3. Compute risk score
             │    exposure=40 (public), criticality=20, likelihood=25
             │    risk = (40 × 20 × 25) / 100 = 200 → 100 (capped)
             │
             ├─ 4. Index in Elasticsearch
             │
             └─ 6. Publish graph.updated event
                               │
         ┌─────────────────────┴────────────┐
         │                                  │
         │                    ┌─────────────────────────┐
         │                    │ Kafka Topic             │
         │                    │ finding.raw             │
         │                    └────────────┬────────────┘
         │                                 │
         │                                 ▼
         │                        ┌──────────────────────────┐
         │                        │ Alert Service            │
         │                        │ (port 8004)              │
         │                        └─────────┬────────────────┘
         │                                  │
         │                                  ├─ 1. Compute fingerprint
         │                                  │    sha256(rule_id + resource + region)
         │                                  │
         │                                  ├─ 2. Check for duplicates
         │                                  │    SELECT * FROM findings WHERE fingerprint = ?
         │                                  │
         │                                  ├─ 3. Deduplicate or create
         │                                  │    IF found:
         │                                  │      UPDATE findings SET last_seen_at = now
         │                                  │    ELSE:
         │                                  │      INSERT new finding
         │                                  │
         │                                  ├─ 4. Enrich with graph context
         │                                  │    POST /internal/finding/{id}/enrich
         │◄─────────────────────────────────┤    (calls Graph Service)
         │    Returns attack paths          │
         │                                  ├─ 5. Trigger notifications
         │                                  │    POST Slack webhook
         │                                  │    POST Jira API
         │                                  │    Send email
         │                                  │
         │                                  ├─ 6. Publish finding.created event
         │                                  │
         │                                  └─ 7. Update WebSocket subscribers
         │                                       pusher.trigger('cloudvisor', 'finding.created', {...})
         │
         └─────────────────────────────────────┐
                                               │
                                        ┌──────▼──────────┐
                                        │ Frontend        │
                                        │ Dashboard       │
                                        │ (React)         │
                                        │                 │
                                        │ 1. Receive WS   │
                                        │    event        │
                                        │ 2. Update state │
                                        │ 3. Re-render    │
                                        │                 │
                                        │ User sees       │
                                        │ new finding ✓   │
                                        └─────────────────┘
```

## Authentication & Authorization Flow

```
┌─────────────────────────────────────┐
│  User                               │
│  email: user@org.com                │
│  password: correct-horse-battery... │
└────────────┬────────────────────────┘
             │
             │ POST /auth/login
             │ {email, password}
             │
             ▼
┌─────────────────────────────────────┐
│  Auth Service (8002)                │
│                                     │
│  1. Find user by email              │
│  2. Verify password (bcrypt)        │
│  3. Check if MFA enabled            │
│  4. Generate JWT + refresh token    │
│  5. Create session in DB            │
│  6. Set HttpOnly cookie             │
│  7. Log: user.logged_in event       │
└────────────┬────────────────────────┘
             │
             │ Response (200)
             │ {
             │   access_token: "eyJhbGc...",
             │   refresh_token: "...",
             │   expires_in: 900
             │ }
             │ Set-Cookie: session=... (HttpOnly)
             │
             ▼
┌─────────────────────────────────────┐
│  Browser                            │
│                                     │
│  localStorage.setItem(              │
│    'access_token',                  │
│    'eyJhbGc...'                     │
│  )                                  │
│                                     │
│  HTTP requests now include:         │
│  Authorization: Bearer eyJhbGc...   │
│  Cookie: session=...                │
└────────────┬────────────────────────┘
             │
             │ GET /v1/findings (with JWT)
             │
             ▼
┌─────────────────────────────────────┐
│  Nginx (Reverse Proxy)              │
│                                     │
│  1. Forward to API Gateway          │
│  2. Preserve Authorization header   │
│  3. Preserve Cookie header          │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  API Gateway (8005)                 │
│                                     │
│  1. Extract JWT from header         │
│  2. Validate signature (HS256)      │
│  3. Check expiration                │
│  4. Extract org_id + user_id        │
│  5. Verify scopes (findings:read)   │
│  6. Call Auth service to validate   │
│     POST /internal/auth/validate    │
│     {token: "eyJhbGc..."}           │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Auth Service Validates             │
│                                     │
│  1. Decode JWT                      │
│  2. Verify signature                │
│  3. Check if token in allowlist     │
│  4. Return user + org context       │
│     {                               │
│       valid: true,                  │
│       user_id: "user_123",          │
│       org_id: "org_456",            │
│       scopes: ["findings:read"]     │
│     }                               │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  API Gateway Routes Request         │
│                                     │
│  1. Query findings from PostgreSQL  │
│  2. Apply RLS filter:               │
│     WHERE org_id = 'org_456'        │
│  3. Apply permission check:         │
│     IF 'findings:read' in scopes    │
│       PROCEED                       │
│     ELSE                            │
│       RETURN 403 Forbidden          │
│  4. Return findings only visible    │
│     to this organization            │
└────────────┬────────────────────────┘
             │
             │ Response 200
             │ {
             │   "data": [...findings...],
             │   "meta": {...}
             │ }
             │
             ▼
┌─────────────────────────────────────┐
│  Browser Receives Response          │
│  & Updates UI                       │
└─────────────────────────────────────┘
```

## RAG Pipeline: Copilot Query

```
User: "Which prod workloads are internet-facing?"
        │
        ▼
┌──────────────────────────────────────┐
│  Copilot Service (8010)              │
│                                      │
│  [STEP 1] Intent Classification      │
│  ├─ Keyword matching                 │
│  ├─ Detect: "prod" → production env  │
│  ├─ Detect: "internet-facing" → exp  │
│  └─ INTENT = "POSTURE"               │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  [STEP 2] Query Embedding            │
│  ├─ Call OpenAI text-embedding-3-sm  │
│  └─ Embedding: 1536-dim vector       │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  [STEP 3] Multi-Source Retrieval     │
│                                      │
│  Parallel calls to 6 data sources:   │
│                                      │
│  1. Neo4j Graph Query                │
│     MATCH (res {env: "prod"})        │
│     -[:EXPOSED_TO]->                 │
│     (internet:InternetGateway)       │
│     RETURN res                       │
│                                      │
│  2. Elasticsearch Full-Text Search   │
│     {                                │
│       "query": {                     │
│         "bool": {                    │
│           "must": [                  │
│             {match: {tags: "prod"}}, │
│             {match: {internet: true}}│
│           ]                          │
│         }                            │
│       }                              │
│     }                                │
│                                      │
│  3. PostgreSQL Compliance             │
│     SELECT * FROM compliance_controls│
│     WHERE framework = 'CIS'          │
│     AND desc ILIKE 'internet'        │
│                                      │
│  4. CIEM Permission API              │
│     GET /permissions?env=prod        │
│                                      │
│  5. CWPP Vulnerability API           │
│     GET /vulnerabilities?env=prod    │
│                                      │
│  6. CDR Threat Log                   │
│     GET /threats?env=prod            │
│                                      │
│  Results:                            │
│  - 3 EC2 instances exposed           │
│  - 1 ALB load balancer exposed       │
│  - 2 Lambda functions exposed        │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  [STEP 4] Prompt Construction        │
│                                      │
│  SYSTEM: "You are CloudVisor Q..."  │
│                                      │
│  CONTEXT:                            │
│  - Asset Graph Results (sources)     │
│  - Finding Results (citations)       │
│  - Compliance mappings               │
│  - IAM permissions                   │
│  - CVE data                          │
│  - Threat events                     │
│                                      │
│  USER QUERY:                         │
│  "Which prod workloads are internet?"│
│                                      │
│  Instructions:                       │
│  - Answer only from context          │
│  - No hallucinations                 │
│  - Always cite sources               │
│  - Suggest remediation               │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  [STEP 5] Claude API Call (Streaming)│
│                                      │
│  POST https://api.anthropic.com/... │
│  model: claude-3-sonnet              │
│  max_tokens: 1024                    │
│  stream: true                        │
│                                      │
│  Streaming Response:                 │
│  {                                   │
│    "type": "content_block_delta",   │
│    "delta": {                        │
│      "type": "text_delta",          │
│      "text": "I found 3 production"  │
│    }                                 │
│  }                                   │
│  {                                   │
│    "type": "content_block_delta",   │
│    "delta": {                        │
│      "type": "text_delta",          │
│      "text": " workloads..."        │
│    }                                 │
│  }                                   │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  [STEP 6] Audit Logging              │
│                                      │
│  INSERT INTO copilot_queries {       │
│    org_id: "org_456",                │
│    user_id: "user_123",              │
│    query: "Which prod workloads...", │
│    intent: "POSTURE",                │
│    context_sources: [                │
│      "neo4j", "elasticsearch",       │
│      "postgresql", "ciem", "cwpp"    │
│    ],                                │
│    response: "I found 3...",         │
│    tokens_used: 324,                 │
│    response_time_ms: 2150,           │
│    created_at: now()                 │
│  }                                   │
│                                      │
│  Then stream to frontend via SSE     │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Browser receives streaming response │
│  & displays in real-time             │
│                                      │
│  "I found 3 production workloads ... │
│   1. Production-Web-Server (EC2)     │
│   2. API-Gateway (ALB)               │
│   3. Auth-Lambda (Lambda)            │
│                                      │
│   [source: finding_789]              │
│   [source: asset_123]"               │
└──────────────────────────────────────┘
```

## Kafka Event Flow

```
Kafka Topics (Event Bus)
├─ assets.discovered          ← Connector publishes
│  └─ Consumer: Graph Service
│  └─ Consumer: Policy Service
│
├─ assets.updated
│  └─ Consumer: Graph Service
│  └─ Consumer: Policy Service
│
├─ finding.raw               ← Policy Service publishes
│  └─ Consumer: Alert Service
│
├─ finding.created            ← Alert Service publishes
│  ├─ Consumer: WebSocket notifier
│  ├─ Consumer: Email notifier
│  ├─ Consumer: Slack notifier
│  ├─ Consumer: Jira notifier
│  └─ Consumer: Copilot (warm embedding cache)
│
├─ finding.seen_again
│  └─ Consumer: SLA tracker
│
├─ finding.resolved
│  ├─ Consumer: Dashboard metrics
│  └─ Consumer: Jira (auto-close)
│
├─ incident.created           ← Alert Service publishes
│  └─ Consumer: WebSocket notifier
│
├─ notification.sent          ← Alert Service publishes
│  └─ Audit trail
│
├─ audit.events               ← All services publish
│  └─ Consumer: Audit logger
│
└─ copilot.query_logged       ← Copilot Service publishes
   └─ Analytics / ML training

Kafka Consumer Groups:
├─ graph-service             (offset tracking per partition)
├─ policy-service
├─ alert-service
├─ websocker-notifier
├─ email-notifier
├─ slack-notifier
└─ audit-logger
```

## Database Schema Relationships

```
PostgreSQL Multi-Tenant Schema
(Row-Level Security enforced per organization_id)

organizations (PK: id)
    ├─ 1:N users
    ├─ 1:N cloud_accounts
    ├─ 1:N findings
    ├─ 1:N incidents
    ├─ 1:N notification_channels
    ├─ 1:N suppression_rules
    ├─ 1:N audit_log
    └─ 1:N copilot_queries

users (PK: id, FK: organization_id)
    ├─ 1:N sessions
    ├─ 1:N api_keys
    ├─ 1:N findings (assignee)
    └─ 1:N audit_log (user_id)

findings (PK: id, FK: organization_id, UNIQUE: fingerprint)
    ├─ N:1 findings_history (FD)
    ├─ N:1 notification_log (FK)
    ├─ N:1 incidents (FK: array of finding_ids)
    └─ Indexed: org_id, status, severity, created_at, fingerprint

Neo4j Graph Schema

(:Resource {resource_id, resource_type, provider, risk_score})
    ├─ [:IN_ACCOUNT]→ (:Account)
    ├─ [:IN_REGION]→ (:Region)
    ├─ [:HAS_TAG]→ (:Tag {key, value})
    ├─ [:ALLOWS_INBOUND_FROM]→ (:CIDR {value})
    ├─ [:CONNECTED_TO]→ (:Resource)
    ├─ [:HAS_FINDING]→ (:Finding {severity, status})
    └─ [:ATTACKED_BY]→ (:Finding)

Attack Paths:
    (:InternetGateway)
        -[:ROUTES_TO]→ (:SecurityGroup)
        -[:ATTACHED_TO]→ (:EC2Instance)
        -[:CONNECTED_TO]→ (:RDSInstance)
        WHERE (:RDSInstance).contains_pii = true

Elasticsearch Index Mappings

findings index:
├─ id (keyword)
├─ organization_id (keyword)
├─ rule_id (keyword)
├─ resource_id (keyword)
├─ severity (keyword)
├─ status (keyword)
├─ title (text + keyword)
├─ description (text)
├─ provider (keyword)
├─ account_id (keyword)
├─ region (keyword)
├─ tags (object)
├─ first_seen_at (date)
├─ last_seen_at (date)
└─ fingerprint (keyword, unique)
```

---

## Deployment Topology (Kubernetes)

```
Kubernetes Cluster (1.28+)
└─ cloudvisor namespace

StatefulSets (state persisted):
├─ postgres-0 (replicas: 1)
│  └─ PVC: postgres-data (100GB)
├─ neo4j-0 (replicas: 1)
│  └─ PVC: neo4j-data (50GB)
├─ elasticsearch-0 (replicas: 1)
│  └─ PVC: elasticsearch-data (200GB)
└─ kafka-0, kafka-1, kafka-2 (replicas: 3)
   └─ PVC: kafka-data (500GB)

Deployments (stateless, auto-scaling):
├─ auth (replicas: 3)
├─ connector (replicas: 2)
├─ graph (replicas: 2)
├─ policy (replicas: 2)
├─ alert (replicas: 3)
├─ api (replicas: 3)
├─ cspm (replicas: 2)
├─ copilot (replicas: 2)
├─ ai-router (replicas: 2)
├─ keep (replicas: 1)
├─ web (replicas: 2)
└─ nginx (replicas: 2)

Services:
├─ nginx-service (LoadBalancer, port 443)
├─ api-service (ClusterIP, port 8005)
├─ auth-service (ClusterIP, port 8002)
├─ postgres-service (ClusterIP, port 5432)
├─ neo4j-service (ClusterIP, port 7687)
├─ kafka-service (ClusterIP, port 9092)
└─ redis-service (ClusterIP, port 6379)

ConfigMaps:
├─ nginx-config
├─ opa-rules
└─ kafka-topics

Secrets:
├─ db-credentials
├─ api-keys
├─ ssl-cert
└─ vault-token

Ingress:
└─ cloudvisor-ingress
   ├─ cloudvisor.io → nginx-service
   └─ TLS: Let's Encrypt
```

---

**End of Architecture Diagrams**
