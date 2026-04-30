

# CloudVisor CNAPP — Comprehensive Codebase Reference

---

## 1. Repository Layout

```
cloudvisor/
├── apps/
│   ├── web/                    # Next.js 14 main frontend (port 3000)
│   └── admin-web/              # Next.js 14 admin frontend (port 3002)
├── services/
│   ├── auth/                   # Auth & RBAC (port 8002)
│   ├── connector/              # Cloud asset ingestion (port 8000)
│   ├── graph/                  # Asset graph — Neo4j (port 8001)
│   ├── policy/                 # OPA policy engine (port 8003)
│   ├── alert/                  # Findings & notifications (port 8004)
│   ├── api/                    # Public API gateway (port 8005)
│   ├── copilot/                # CloudVisor Q — RAG LLM (port 8010)
│   └── security/
│       ├── cspm/               # CSPM module (port 8006)
│       ├── cwpp/               # stub only
│       ├── cicd/               # stub only
│       ├── ciem/               # stub only
│       ├── kspm/               # stub only
│       ├── dspm/               # stub only
│       ├── cdr/                # stub only
│       └── aiops/              # stub only
├── packages/
│   ├── utils/                  # Shared Python: config, DB, Redis, Kafka, logging, tracing
│   ├── types/                  # Shared Python dataclasses (CloudResource CDM)
│   └── kafka-schemas/          # Avro event schemas
├── rules/rego/                 # OPA Rego policies (cspm, kspm, cdr, cicd, iac)
├── infra/
│   ├── db/postgres/            # Postgres data volume
│   ├── db/neo4j/               # Neo4j data volume
│   └── vault/                  # Vault config + init script
├── Instructions/               # Engineering briefs (backend + UI)
├── docker-compose.yml
└── .env                        # Root env file (all services read from here)
```

Every backend service follows the same internal layout:
```
services/<name>/
├── main.py
├── app/
│   ├── api/routes/     # FastAPI routers
│   ├── consumers/      # Kafka consumers
│   ├── producers/      # Kafka producers
│   ├── models/         # SQLAlchemy ORM (PostgreSQL tables)
│   ├── schemas/        # Pydantic request/response
│   ├── services/       # Business logic
│   ├── repositories/   # DB access layer
│   └── core/           # config.py + dependencies.py
└── tests/unit/ + tests/integration/
```

---

## 2. Infrastructure Stack

| Component | Image | Port | Purpose |
|---|---|---|---|
| PostgreSQL 15 | `postgres:15-alpine` | 5432 | Primary relational DB (all services share one DB, isolated by RLS) |
| Neo4j 5.15 | `neo4j:5.15-community` | 7687 / 7474 | Asset graph (nodes + relationships) |
| Elasticsearch 8.12 | `elasticsearch:8.12.0` | 9200 | Full-text search for assets and findings |
| Kafka 7.5 | `confluentinc/cp-kafka:7.5.0` | 9092 | Async inter-service messaging |
| Zookeeper | `confluentinc/cp-zookeeper:7.5.0` | 2181 | Kafka coordination |
| Redis 7.2 | `redis:7.2-alpine` | 6379 | Cache, rate limiting, sessions |
| OPA | `openpolicyagent/opa:latest` | 8181 | Rego policy evaluation |
| Vault 1.15 | `hashicorp/vault:1.15` | 8200 | Cloud credential secrets storage |
| Ollama | `ollama/ollama:latest` | 11434 | Local LLM inference for Copilot |
| Adminer | `adminer:latest` | 8080 | DB admin UI |

**Redis DB allocation:**
- DB 0 → Auth service
- DB 1 → Graph service
- DB 2 → Policy service
- DB 3 → Alert service
- DB 4 → API gateway
- DB 5 → CSPM service
- DB 6 → Copilot service

---

## 3. Multi-Tenancy & Security Model

**Row-Level Security (RLS)** is the core isolation mechanism. Every tenant-scoped table has a PostgreSQL RLS policy:
```sql
USING (organization_id::text = current_setting('app.current_org_id', true)::text)
```

The `rls_session()` context manager in `packages/utils` sets this before every query:
```python
await session.execute(
    text("SELECT set_config('app.current_org_id', :org_id, true)"),
    {"org_id": str(organization_id)},
)
```

**JWT tokens** are RS256-signed (15-min expiry). Refresh tokens are opaque, stored hashed (SHA-256), 30-day expiry with rotation on every use.

**API keys** format: `cv_live_<32-char-random>`. Only the SHA-256 hash is stored.

---

## 4. PostgreSQL Database Tables

All services share a single `cloudvisor` database. Tables are namespaced by service.

### Auth Service Tables

| Table | Key Columns | Notes |
|---|---|---|
| `organizations` | `id` UUID PK, `name`, `slug` UNIQUE, `plan` (free/starter/growth/enterprise), `billing_email`, `is_deleted` | Tenant root |
| `users` | `id` UUID PK, `organization_id` FK, `email` UNIQUE, `password_hash`, `first_name`, `last_name`, `is_active`, `mfa_enabled`, `mfa_secret`, `mfa_backup_codes`, `provider` (local/google/github), `failed_login_attempts`, `locked_until` | Core user table |
| `sessions` | `id` UUID PK, `user_id` FK, `refresh_token_hash`, `device_info`, `ip_address`, `user_agent`, `is_active`, `last_active_at`, `expires_at` | Active sessions |
| `api_keys` | `id` UUID PK, `user_id` FK, `name`, `key_hash` UNIQUE, `scopes` JSON, `last_used_at`, `expires_at`, `is_active` | API key management |
| `audit_log` | `id` INT PK, `organization_id`, `user_id` FK, `event_type`, `event_data` JSON, `ip_address`, `success`, `failure_reason`, `timestamp` | Auth event log |
| `cv_clients` | `id` UUID PK, `organization_id` FK, `organization_name` UNIQUE, `contact_name`, `contact_email` | Enterprise client metadata |

### Connector Service Tables

| Table | Key Columns | Notes |
|---|---|---|
| `connector_cloud_accounts` | `id` UUID PK, `organization_id`, `provider` (aws/azure/gcp/oci), `name`, `account_id`, `region`, `status`, `sync_status`, `last_sync_at`, `last_successful_sync_at`, `consecutive_errors`, `resource_count`, `polling_interval_minutes`, `vault_secret_path`, `credentials_enc` JSONB | Cloud account registry. Unique on `(org_id, provider, account_id)` |
| `connector_discovered_resources` | `id` UUID PK, `cloud_resource_id`, `provider`, `account_id`, `organization_id`, `region`, `resource_type`, `name`, `tags` JSONB, `raw` JSONB, `is_public`, `environment`, `first_seen_at`, `last_seen_at`, `resource_hash`, `is_deleted`, `deleted_at` | CDM resource store. Unique on `(cloud_resource_id, org_id)` |

### Alert Service Tables

| Table | Key Columns | Notes |
|---|---|---|
| `findings` | `id` UUID PK, `organization_id`, `rule_id`, `resource_id`, `resource_name`, `severity` (CRITICAL/HIGH/MEDIUM/LOW), `status` (open/in_progress/resolved/suppressed/accepted), `title`, `description`, `remediation`, `provider`, `account_id`, `region`, `resource_type`, `fingerprint` UNIQUE, `first_seen_at`, `last_seen_at`, `regression_count` | Core finding table. Deduplicated by SHA-256 fingerprint |
| `finding_history` | `id` UUID PK, `finding_id` FK, `old_status`, `new_status`, `changed_by`, `reason`, `timestamp` | Status change audit trail |
| `incidents` | `id` UUID PK, `organization_id`, `title`, `description`, `severity`, `status`, `finding_ids` UUID[], `assignee_id` | Grouped findings |
| `suppression_rules` | `id` UUID PK, `organization_id`, `rule_id`, `resource_tag_key`, `resource_tag_value`, `account_id`, `region`, `reason`, `created_by`, `expires_at`, `is_active` | Finding suppression |
| `notification_channels` | `id` UUID PK, `organization_id`, `name`, `channel_type` (slack/jira/email/webhook), `config` JSON, `severity_filter` String[], `is_active` | Notification destinations |
| `notification_log` | `id` UUID PK, `finding_id` FK, `channel_id` FK, `status`, `error_message`, `sent_at` | Delivery audit |

### Policy Service Tables

| Table | Key Columns | Notes |
|---|---|---|
| `rules` | `id` UUID PK, `organization_id` (NULL = builtin), `rule_id` STRING, `title`, `description`, `severity`, `category`, `provider`, `resource_type`, `remediation`, `rego_code` TEXT, `version`, `compliance_mapping` JSON, `is_builtin`, `is_custom`, `is_enabled` | OPA rule registry. Unique on `(rule_id, org_id)` |
| `rule_disables` | `id` UUID PK, `rule_id` STRING, `organization_id`, `reason`, `disabled_by`, `disabled_at`, `expires_at` | Per-org rule suppression. Unique on `(rule_id, org_id)` |
| `frameworks` | `id` UUID PK, `name` UNIQUE, `display_name`, `description`, `version`, `controls` JSON | Compliance frameworks (CIS-AWS, SOC2, PCI-DSS, HIPAA, ISO27001, NIST-800-53, GDPR) |
| `evaluation_cache` | `id` INT PK, `rule_id`, `resource_id`, `result` JSON, `evaluated_at`, `expires_at` | OPA result cache |

### Copilot Service Tables

| Table | Key Columns | Notes |
|---|---|---|
| `copilot_queries` | `id` UUID PK, `organization_id`, `user_id`, `query_text`, `intent` (POSTURE/FINDING/COMPLIANCE/REMEDIATION/THREAT/DRIFT), `response_text`, `citations` JSON, `data_sources` String[], `processing_ms`, `model_used`, `context_finding_id`, `context_asset_id`, `was_streamed`, `created_at` | Append-only query audit log |

### CSPM Service Tables (queried by Copilot)

| Table | Key Columns | Notes |
|---|---|---|
| `cspm_findings` | `id`, `organization_id`, `title`, `description`, `severity`, `status`, `resource_name`, `resource_type`, `rule_id`, `created_at` | CSPM-specific findings |
| `cspm_compliance_results` | `id`, `organization_id`, `framework`, `control_id`, `status`, `finding_count`, `last_evaluated_at` | Per-control compliance results |
| `cspm_scans` | `id`, `organization_id`, `scan_type`, `status`, `started_at`, `completed_at`, `resources_scanned`, `findings_created`, `findings_resolved`, `error_message` | Scan history |
| `cspm_posture_snapshots` | `organization_id`, `snapshot_date`, `posture_score`, `critical_count`, `high_count`, `medium_count`, `low_count` | Daily posture trend |
| `cspm_resource_posture` | `resource_id`, `organization_id`, `resource_type`, `provider`, `risk_score`, `is_internet_exposed`, `contains_sensitive_data`, `critical_count`, `high_count`, `medium_count`, `low_count` | Per-resource risk scores |

### Graph Service Tables (PostgreSQL side)

| Table | Key Columns | Notes |
|---|---|---|
| `asset_snapshots` | `asset_id`, `organization_id`, `provider`, `resource_type`, `name`, `risk_score`, `open_findings_count`, `diff_from_previous` JSONB, `snapshot_timestamp` | Historical asset state for drift analysis |

---

## 5. Neo4j Graph Model

**Node labels:** `:Asset` (primary), `:Finding`, `:CIDR`, `:Port`

**Asset node properties:** `id`, `cloud_resource_id`, `provider`, `account_id`, `region`, `resource_type`, `name`, `tags`, `environment`, `is_public`, `risk_score`, `open_findings_count`, `organization_id`, `last_seen_at`

**Relationships:**
```
(:Asset)-[:RUNS_IN]->(:Asset)              # EC2 → Subnet
(:Asset)-[:BELONGS_TO]->(:Asset)           # EC2 → SecurityGroup, Subnet → VPC
(:Asset)-[:HAS_ROLE]->(:Asset)             # EC2/Lambda → IAMRole
(:Asset)-[:HAS_ACCESS_TO]->(:Asset)        # IAMRole → S3/RDS
(:Asset)-[:ASSUMES]->(:Asset)              # IAMRole → IAMRole (cross-account)
(:Asset)-[:ALLOWS_INBOUND_FROM]->(:CIDR)   # SecurityGroup → 0.0.0.0/0
(:Asset)-[:CONNECTS_TO]->(:Asset)          # Lambda → RDS
(:Asset)-[:CONTAINS]->(:Asset)             # EKSCluster → NodeGroup
(:Asset)-[:RUNS_ON]->(:Asset)              # NodeGroup → EC2
(:Asset)-[:HAS_FINDING]->(:Finding)        # Asset → Finding
```

**Elasticsearch index:** `assets` — synced from Neo4j, excludes `raw` field. Used for full-text search.

---

## 6. Kafka Topics

| Topic | Producer | Consumer | Payload |
|---|---|---|---|
| `resource.discovered` | Connector | Graph | New CDM resource |
| `resource.updated` | Connector | Graph | Changed CDM resource |
| `resource.deleted` | Connector | Graph | Deleted resource ID |
| `connector.sync_started` | Connector | — | Sync cycle start |
| `connector.sync_finished` | Connector | — | Sync cycle stats |
| `connector.health_changed` | Connector | — | Account status change |
| `asset.created` | Graph | — | New Neo4j node |
| `asset.updated` | Graph | — | Updated Neo4j node |
| `asset.deleted` | Graph | — | Removed Neo4j node |
| `asset.risk_score_changed` | Graph | — | Risk score delta > 5 |
| `asset.relationship_changed` | Graph | — | Edge added/removed |
| `finding.created` | Alert/CSPM | Graph, Copilot (TODO) | New finding |
| `finding.resolved` | Alert | Graph | Resolved finding |
| `copilot.query_logged` | Copilot | — | Query audit event |

---

## 7. Service API Reference

### Auth Service (port 8002)

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Register user + org, returns JWT |
| POST | `/auth/login` | Email/password login (rate-limited: 10/min/IP) |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Invalidate session |
| GET | `/auth/me` | Get current user profile |
| PATCH | `/auth/me` | Update name |
| POST | `/auth/password` | Change password |
| POST | `/auth/forgot-password` | Request password reset email |
| POST | `/auth/reset-password` | Reset password with token |
| GET | `/auth/oauth/{provider}/authorize` | OAuth redirect (google/github) |
| GET | `/auth/callback/{provider}` | OAuth callback handler |
| POST | `/auth/mfa/enroll` | Begin TOTP enrollment |
| POST | `/auth/mfa/verify` | Confirm TOTP code + enable MFA |
| POST | `/auth/mfa/validate` | Validate MFA during login |
| GET | `/auth/sessions` | List active sessions |
| DELETE | `/auth/sessions/{id}` | Revoke session |
| GET | `/auth/api-keys` | List API keys |
| POST | `/auth/api-keys` | Create API key |
| DELETE | `/auth/api-keys/{id}` | Revoke API key |
| POST | `/auth/api-keys/{id}/rotate` | Rotate API key |
| POST | `/internal/auth/validate` | Token validation (inter-service) |
| POST | `/internal/auth/authorize` | RBAC permission check (inter-service) |
| GET | `/internal/auth/org/{id}` | Get org details + feature flags |
| GET | `/internal/auth/org/{id}/roles` | List roles |
| POST | `/internal/auth/org/{id}/roles` | Create custom role |
| POST | `/internal/auth/users/{id}/role` | Assign role to user |

### Connector Service (port 8000)

| Method | Path | Description |
|---|---|---|
| POST | `/internal/accounts` | Register cloud account (triggers initial sync) |
| GET | `/internal/accounts` | List org's cloud accounts |
| GET | `/internal/accounts/{id}` | Get account details |
| PATCH | `/internal/accounts/{id}` | Update account config |
| DELETE | `/internal/accounts/{id}` | Remove account |
| POST | `/internal/accounts/{id}/sync` | Trigger on-demand sync |
| GET | `/internal/accounts/{id}/health` | Account health + error rate |
| GET | `/internal/onboarding/aws/template` | CloudFormation template |
| GET | `/internal/onboarding/azure/instructions` | Azure SP setup guide |
| GET | `/internal/onboarding/gcp/instructions` | GCP service account guide |
| GET | `/internal/onboarding/oci/instructions` | OCI API key guide |

### Graph Service (port 8001)

| Method | Path | Description |
|---|---|---|
| GET | `/internal/assets` | List assets (paginated, filterable by provider/type/region/env/is_public/risk_score) |
| GET | `/internal/assets/stats` | Asset counts by provider and type |
| GET | `/internal/assets/search` | Full-text search (ES first, Neo4j fallback) |
| GET | `/internal/assets/{id}` | Get single asset |
| GET | `/internal/assets/{id}/related` | Graph neighbors (configurable depth 1-3) |
| GET | `/internal/assets/{id}/history` | Historical snapshots |
| GET | `/internal/assets/{id}/attack-paths` | Attack path computation |
| GET | `/internal/assets/{id}/findings` | Findings linked to asset |
| POST | `/internal/assets/query` | Execute read-only Cypher query |

### Policy Service (port 8003)

| Method | Path | Description |
|---|---|---|
| GET | `/policy/rules` | List rules (filter by category/provider/severity) |
| GET | `/policy/rules/{id}` | Get rule |
| POST | `/policy/rules/custom` | Create custom Rego rule |
| PUT | `/policy/rules/custom/{id}` | Update custom rule |
| DELETE | `/policy/rules/custom/{id}` | Delete custom rule |
| POST | `/policy/rules/{id}/disable` | Disable rule for org |
| POST | `/policy/rules/{id}/enable` | Re-enable rule |
| POST | `/policy/evaluate` | Evaluate rules against resources |
| POST | `/policy/evaluate/dry-run` | Test Rego without creating findings |
| GET | `/policy/compliance` | Compliance summary (all frameworks) |
| GET | `/policy/compliance/{framework}` | Framework posture |
| GET | `/policy/compliance/{framework}/evidence` | Control evidence |

### Alert Service (port 8004)

| Method | Path | Description |
|---|---|---|
| GET | `/findings/stats` | Finding counts by severity/status |
| GET | `/findings` | List findings (filter by severity/status/provider/account/region) |
| GET | `/findings/{id}` | Get finding |
| PATCH | `/findings/{id}` | Update finding status |
| POST | `/findings/bulk` | Bulk status update |
| GET/POST/DELETE | `/suppressions` | Suppression rule CRUD |
| GET/POST/DELETE | `/notifications` | Notification channel CRUD |
| GET/POST/PATCH | `/incidents` | Incident management |

### Copilot Service (port 8010)

| Method | Path | Description |
|---|---|---|
| POST | `/v1/copilot/query` | Natural language query (streaming or complete) |
| GET | `/v1/copilot/history` | Query history for current user |

### API Gateway (port 8005)

Proxies all routes to upstream services. Adds CORS, auth header forwarding, and rate limiting.

---

## 8. Shared Packages (`packages/`)

### `cloudvisor_utils` (installed in every service)

| Module | Purpose |
|---|---|
| `config.py` | `CloudvisorSettings` — nested Pydantic settings for DB, Redis, Kafka, OTel, App, Vault. All services call `get_settings()` |
| `database.py` | `create_engine()`, `create_session_factory()`, `rls_session()` (sets RLS), `system_session()` (no RLS) |
| `logging_utils.py` | Structured JSON logging via structlog |
| `tracing.py` | OpenTelemetry setup + FastAPI instrumentation |
| `metrics.py` | Prometheus metrics setup |

### `cloudvisor_types`

Contains the `CloudResource` CDM dataclass — the normalized representation of any cloud resource across all 4 providers. Also defines `CloudProvider` and `Environment` enums.

### `kafka-schemas`

Avro schema definitions for all Kafka events.

---

## 9. Frontend Architecture (`apps/web`)

**Stack:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, React Query v5, Zustand, Recharts, ReactFlow, Lucide React

**Design system:** AWS Cloudscape-inspired — dark top nav, light side nav, 4px grid, pill buttons (20px radius), 1px borders on containers (no shadows), Open Sans typography.

### Pages

| Route | Page | Status |
|---|---|---|
| `/login` | Login | ✅ Connected to auth API |
| `/signup` | Register | ✅ Connected to auth API |
| `/forgot-password` | Password reset | ✅ |
| `/dashboard` | Main dashboard | ✅ Connected to real data |
| `/findings` | Findings list | ✅ Connected to alert API |
| `/assets` | Asset inventory | ✅ Connected to graph API |
| `/compliance` | Compliance frameworks | ✅ |
| `/cspm` | Cloud security posture | ✅ Connected to CSPM API |
| `/cwpp` | Workload protection | UI only |
| `/cicd` | CI/CD security | UI only |
| `/ciem` | Entitlement management | UI only |
| `/kspm` | Kubernetes security | UI only |
| `/dspm` | Data security | UI only |
| `/cdr` | Detection & response | UI only |
| `/aiops` | AIOps | UI only |
| `/copilot` | CloudVisor Q chat | ✅ Connected to copilot API |
| `/incidents` | Incident management | ✅ |
| `/risk-map` | Visual risk map | ✅ |
| `/settings` | Account settings | ✅ |
| `/settings/api-keys` | API key management | ✅ |
| `/settings/team` | Team management | ✅ |
| `/settings/notifications` | Notification channels | ✅ |
| `/settings/billing` | Billing | UI only |
| `/profile` | User profile | ✅ |
| `/admin/dashboard` | Admin panel | ✅ |

### Key Components (`src/components/ui/`)

| Component | Purpose |
|---|---|
| `severity-badge.tsx` | CRITICAL/HIGH/MEDIUM/LOW/INFO pill badges |
| `status-badge.tsx` | Finding status indicators |
| `provider-badge.tsx` | AWS/Azure/GCP/OCI badges |
| `risk-score.tsx` | Circular gauge (0-100) |
| `finding-card.tsx` | Finding summary card |
| `finding-detail-drawer.tsx` | Full finding detail panel |
| `data-table.tsx` | Sortable, filterable table |
| `asset-graph.tsx` | ReactFlow graph visualization |
| `attack-path-graph.tsx` | Attack path visualization |
| `cloudvisor-q-panel.tsx` | Copilot chat panel |
| `command-palette.tsx` | Cmd+K global search |
| `scope-selector.tsx` | Cloud account/provider scope switcher |
| `flashbar.tsx` | AWS-style page-level notifications |
| `filter-bar.tsx` / `filter-sidebar.tsx` | Filtering controls |
| `compliance-bar.tsx` | Framework pass/fail bar |
| `metric-card.tsx` | KPI metric display |
| `cv-container.tsx` | Cloudscape-style container wrapper |

### State Management

| Store | Purpose |
|---|---|
| `stores/scope.ts` | Active cloud provider/account scope (Zustand) |
| `stores/user-settings.ts` | Theme, density, preferences (Zustand + localStorage) |
| `stores/cloudvisor-q.ts` | Copilot conversation state (Zustand) |

### API Clients (`src/lib/api/`)

| File | Covers |
|---|---|
| `apiClient.ts` | Base axios client with JWT injection + refresh |
| `auth.ts` | Login, register, logout, profile, API keys |
| `connector.ts` | Cloud account CRUD, sync trigger |
| `cspm.ts` | CSPM findings, posture, compliance |

### Custom Hooks

| Hook | Purpose |
|---|---|
| `use-auth.tsx` | Auth state, login/logout, token management |
| `use-dashboard.ts` | Dashboard metrics via React Query |
| `use-findings.ts` | Findings list + stats |
| `use-cspm.ts` | CSPM posture data |
| `use-scope.ts` | Active scope from Zustand store |
| `use-websocket.tsx` | WebSocket connection for real-time updates |

---

## 10. Environment Variables (Root `.env`)

Key groups (values omitted):

```
# Database
DB_URL=postgresql+asyncpg://cvadmin:cvpassword@localhost:5432/cloudvisor

# Redis
REDIS_URL=redis://localhost:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Auth
AUTH_SECRET_KEY=...
AUTH_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=15
AUTH_REFRESH_TOKEN_EXPIRE_DAYS=30
AUTH_OAUTH_GITHUB_CLIENT_ID=...
AUTH_OAUTH_GITHUB_CLIENT_SECRET=...
AUTH_OAUTH_GOOGLE_CLIENT_ID=...

# Vault
VAULT_URL=http://localhost:8200
VAULT_TOKEN=cloudvisor-root-token

# Copilot LLM
COPILOT_LLM_PROVIDER=ollama|google|openrouter
COPILOT_OLLAMA_BASE_URL=http://localhost:11434
COPILOT_OLLAMA_MODEL=qwen2.5:0.5b
COPILOT_OPENROUTER_API_KEY=...
COPILOT_OPENROUTER_MODEL=google/gemma-4-31b-it:free
COPILOT_GOOGLE_API_KEY=...
COPILOT_GOOGLE_MODEL=gemini-2.0-flash-lite

# Graph
GRAPH_NEO4J_URI=bolt://localhost:7687
GRAPH_NEO4J_USER=neo4j
GRAPH_NEO4J_PASSWORD=password
GRAPH_ELASTICSEARCH_URL=http://localhost:9200

# Policy
POLICY_OPA_URL=http://localhost:8181

# Observability
OTEL_ENABLED=false
```

---

## 11. What's Fully Implemented vs. Stub

### Fully Implemented ✅
- Auth service (register, login, MFA, OAuth, RBAC, sessions, API keys)
- Connector service (account CRUD, AWS/Azure/GCP/OCI onboarding, sync scheduler, Vault integration, CDM normalization)
- Graph service (Neo4j CRUD, Elasticsearch sync, asset listing/search/attack paths, risk scoring)
- Policy service (OPA integration, rule management, compliance frameworks, evaluation engine)
- Alert service (finding CRUD, deduplication by fingerprint, status state machine, suppression rules, notification channels, incidents)
- Copilot service (6-step RAG pipeline, 7 intent types, multi-provider LLM, multi-source retrieval, audit logging)
- API gateway (proxy routing to all services)
- Frontend (all pages, full design system, connected to real APIs for auth/connector/graph/alert/cspm/copilot)
- Shared packages (config, DB with RLS, logging, tracing, metrics)

### Stub Only ❌
- CWPP, CI/CD, CIEM, KSPM, DSPM, CDR, AIOps — `main.py` exists, no business logic
- Copilot: query embedding (Step 2 commented out), citation parsing (returns empty list), streaming audit log, Kafka consumer for `finding.created`
- `GENERAL` intent missing from `copilot_queries` DB constraint (will fail on insert)
- `_format_asset_snapshots()` missing from `prompt_builder.py` (runtime error on DRIFT queries)
- OpenAI LLM client raises `NotImplementedError`
- No tests anywhere (unit/ and integration/ directories are empty)
- No CI/CD pipelines, no Helm charts, no Terraform modules

---

## 12. Key Patterns to Know Before Editing

1. **RLS is mandatory** — never query tenant tables without `rls_session()`. Use `system_session()` only for seeding/migrations.

2. **Service isolation** — services never import from each other. Cross-service calls go through HTTP (sync) or Kafka (async).

3. **Credentials in Vault** — `connector_cloud_accounts.credentials_enc` is a fallback for dev only. In production, `vault_secret_path` is set and credentials live in Vault.

4. **Kafka topics** — defined as constants in `packages/utils/src/cloudvisor_utils/config.py` under `KafkaSettings`. Always use those constants, not hardcoded strings.

5. **LLM provider switching** — controlled by `COPILOT_LLM_PROVIDER` env var. Factory in `llm_client.py` returns the right client. Default is `ollama` (local).

6. **Finding deduplication** — `findings.fingerprint` is a SHA-256 hash. Duplicate findings update `last_seen_at` and