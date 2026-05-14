# CloudVisor Public API Service — Foundation 6

## Purpose

The Public API service is the customer-facing gateway for the CloudVisor CNAPP platform.
It exposes a unified REST API (`/v1/*`) and a GraphQL endpoint (`/graphql`) that aggregate
data from all internal microservices. Enterprise customers integrate CloudVisor into their
existing toolchains, automation workflows, and SIEM systems through this API.

## Architecture

This service is a **thin proxy layer** — it does not own any data. It:
1. Authenticates every request (JWT or API key)
2. Enforces rate limiting (Redis-backed sliding window)
3. Routes requests to the appropriate upstream service
4. Wraps all responses in the standard envelope format
5. Adds observability headers (request ID, timing, rate-limit)

## Auth

Two authentication methods are supported:
- `Authorization: Bearer <JWT>` — short-lived access tokens (15-min expiry)
- `X-API-Key: cv_live_<key>` — long-lived API keys for automation

Token validation is delegated to the Auth service (`/internal/auth/validate`).

## API Standards

- **Base URL:** `https://api.cloudvisor.io/v1`
- **Pagination:** Cursor-based (opaque `cursor` parameter, no offset)
- **Filtering:** `filter[field]=value` query parameters
- **Sorting:** `sort=field,-other_field` (prefix `-` for descending)
- **Field selection:** `fields[resource]=id,name,severity`
- **Rate limiting:** Headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Envelope:** `{ "data": ..., "meta": { ... }, "errors": [] }`

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `API_AUTH_SERVICE_URL` | `http://cv-auth:8002` | Auth service URL |
| `API_CONNECTOR_SERVICE_URL` | `http://cv-connector:8000` | Connector service URL |
| `API_GRAPH_SERVICE_URL` | `http://cv-graph:8001` | Graph service URL |
| `API_POLICY_SERVICE_URL` | `http://cv-policy:8003` | Policy service URL |
| `API_ALERT_SERVICE_URL` | `http://cv-alert:8004` | Alert service URL |
| `API_CSPM_SERVICE_URL` | `http://cv-cspm:8006` | CSPM service URL |
| `API_COPILOT_SERVICE_URL` | `http://cv-copilot:8010` | Copilot service URL |
| `API_RATE_LIMIT_REQUESTS_PER_MINUTE` | `600` | Rate limit per org/key |
| `API_CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `REDIS_URL` | `redis://cv-redis:6379/4` | Redis for rate limiting |
| `AUTH_INTERNAL_SERVICE_TOKEN` | `` | Service-to-service auth token |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `` | OpenTelemetry collector endpoint |

## Setup

```bash
cd services/api
pip install -r requirements.txt
python main.py
# API available at http://localhost:8005/v1/docs
```

## Endpoints

See the full OpenAPI spec at `/v1/docs` when the service is running.

### Key routes:
- `GET /v1/assets` — List cloud assets
- `GET /v1/findings` — List security findings
- `GET /v1/accounts` — List connected cloud accounts
- `GET /v1/compliance` — Compliance posture
- `GET /v1/rules` — Security rules
- `POST /v1/scan` — Trigger on-demand scan
- `POST /graphql` — GraphQL queries
- `POST /v1/copilot/query` — AI security copilot

## Performance Targets

- API list endpoint response: p95 < 200ms
- API detail endpoint response: p95 < 100ms
- GraphQL query: p95 < 500ms
- Report generation: complete within 60 seconds
