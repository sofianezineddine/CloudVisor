# CloudVisor Q (Copilot) Service

RAG-powered Security Intelligence Assistant for the CloudVisor CNAPP Platform.

## Overview

CloudVisor Q is a natural language interface to your cloud security data. It uses Retrieval-Augmented Generation (RAG) powered by Anthropic Claude to answer questions grounded in your actual environment — never from generic security knowledge.

**Key Features:**
- 🔍 Natural language queries about cloud security posture
- 📊 Multi-source context retrieval (8 data sources)
- 🎯 Intent-based routing (6 capability domains)
- 📝 Citation-backed answers
- 🔄 Streaming responses (SSE)
- 🔒 Read-only, tenant-scoped, fully audited

## Quick Start

### Run with Docker Compose

```bash
# Build and start the copilot service
docker-compose up -d --build copilot-service

# View logs
docker-compose logs -f copilot-service

# Check health
curl http://localhost:8010/health
```

### Run Locally (Development)

```bash
# Install dependencies
cd services/copilot
pip install -r requirements.txt

# Install shared utils package
pip install -e ../../packages/utils

# Set environment variables
export COPILOT_ANTHROPIC_API_KEY="your-api-key"
export COPILOT_OPENAI_API_KEY="your-api-key"
export DB_URL="postgresql+asyncpg://cvadmin:cvpassword@localhost:5432/cloudvisor"
export REDIS_URL="redis://localhost:6379/0"

# Start the service
python -m uvicorn main:app --reload --port 8010
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/copilot/query` | POST | Query CloudVisor Q with natural language |
| `/v1/copilot/history` | GET | Get query history for current user |
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |
| `/metrics` | GET | Prometheus metrics |
| `/v1/docs` | GET | OpenAPI documentation |

## Example Query

```bash
curl -X POST http://localhost:8010/v1/copilot/query \
  -H "Authorization: Bearer <token>" \
  -H "X-Org-ID: <org-id>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which production workloads have critical CVEs and are internet-facing?",
    "stream": false
  }'
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `COPILOT_ANTHROPIC_API_KEY` | Anthropic API key (required) | |
| `COPILOT_ANTHROPIC_MODEL` | Claude model to use | `claude-sonnet-4` |
| `COPILOT_OPENAI_API_KEY` | OpenAI API key for embeddings | |
| `COPILOT_EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |
| `COPILOT_MAX_CONTEXT_TOKENS` | Max context window | `100000` |
| `COPILOT_ENABLE_STREAMING` | Enable SSE streaming | `true` |
| `COPILOT_RATE_LIMIT_PER_MINUTE` | Rate limit per user | `20` |
| `COPILOT_GRAPH_SERVICE_URL` | Graph service URL | `http://localhost:8001` |
| `COPILOT_POLICY_SERVICE_URL` | Policy service URL | `http://localhost:8003` |
| `COPILOT_ELASTICSEARCH_URL` | Elasticsearch URL | `http://localhost:9200` |
| `DB_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |

## RAG Pipeline (6 Steps)

```
User Query
    ↓
[1] Intent Classification
    ↓
[2] Query Embedding
    ↓
[3] Multi-Source Retrieval (8 data sources)
    ↓
[4] Prompt Construction
    ↓
[5] Claude API Call
    ↓
[6] Response Parsing + Audit Logging
```

## 6 Capability Domains

1. **POSTURE** - Risk and exposure queries
2. **FINDING** - Finding explanation and details
3. **COMPLIANCE** - Compliance status and reports
4. **REMEDIATION** - Auto-fix code generation
5. **THREAT** - Threat investigation and CDR
6. **DRIFT** - Change and drift analysis

## Data Sources

CloudVisor Q retrieves context from:
- Asset graph (Neo4j)
- Findings (Elasticsearch)
- Compliance posture (Policy API)
- Audit & change log (PostgreSQL)
- CIEM permissions (CIEM service)
- CVE / vuln data (CWPP service)
- CDR log events (CDR service)
- SBOM / CI results (CI/CD service)

## Database Tables

| Table | Purpose |
|-------|---------|
| `copilot_queries` | Audit log for all queries (append-only) |

## Kafka Events

### Produced
- `copilot.query_logged` - After every query completes

### Consumed
- `finding.created` - Warm embedding cache for new findings

## Performance Targets

- Intent classification: p95 < 300ms
- All retrieval calls: p95 < 2s
- Claude API call: p95 < 8s
- End-to-end: p95 < 10s
- Streaming first token: p95 < 3s

## Security

- **Read-only**: Never modifies cloud resources
- **Tenant-scoped**: All queries enforce RLS via organization_id
- **Fully audited**: Every query logged to copilot_queries table
- **Rate limited**: 20 queries/minute per user

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests (requires Docker Compose)
pytest tests/integration -v

# All tests with coverage
pytest --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
black app/

# Lint
ruff check app/

# Type check
mypy app/
```

## Architecture

```
services/copilot/
├── main.py                      # FastAPI app
├── app/
│   ├── api/
│   │   └── query.py            # POST /v1/copilot/query
│   ├── services/
│   │   ├── rag_pipeline.py     # Main orchestration
│   │   ├── intent_classifier.py # Intent detection
│   │   ├── retriever.py        # Multi-source retrieval
│   │   ├── prompt_builder.py   # Prompt construction
│   │   ├── llm_client.py       # Claude API wrapper
│   │   └── rate_limiter.py     # Rate limiting
│   ├── models/
│   │   └── query_log.py        # Database models
│   ├── schemas/
│   │   ├── request.py          # Request schemas
│   │   └── response.py         # Response schemas
│   ├── repositories/
│   │   └── query_log_repo.py   # DB access layer
│   └── core/
│       ├── config.py           # Configuration
│       └── dependencies.py     # Dependency injection
└── tests/
    ├── unit/
    └── integration/
```

## What CloudVisor Q Never Does

- Never modifies cloud resources
- Never applies fixes autonomously
- Never creates, deletes, or updates anything in the customer's cloud
- Never answers from general knowledge when specific tenant data is available
- Never opens a PR without explicit user request and approval

## Troubleshooting

### Claude API Errors

```bash
# Check API key
echo $COPILOT_ANTHROPIC_API_KEY

# Test API connectivity
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $COPILOT_ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql $DB_URL -c "SELECT 1"

# Check if tables exist
psql $DB_URL -c "\dt copilot_queries"
```

### Service Dependencies

Ensure these services are running:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Elasticsearch (port 9200)
- Graph service (port 8001)
- Policy service (port 8003)

## License

Copyright © 2026 CloudVisor. All rights reserved.
