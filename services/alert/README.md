# CloudVisor Alert Service

Alert Pipeline & Notification Engine - Foundation 5 of the CloudVisor CNAPP platform.

## Features

- **Finding ingestion**: Process findings from Policy Engine via Kafka or REST
- **Deduplication**: SHA-256 fingerprinting to prevent noise
- **Enrichment**: Query Asset Graph, Policy Engine, and AIOps for context
- **Suppression**: Auto-suppress by rule, tag, account, region (evaluated before persistence)
- **State machine**: open → in_progress → resolved, suppressed, accepted_risk
- **Incidents**: Group related findings (by rule+account, resource, CDR time-window)
- **SLA tracking**: CRITICAL: 4h ack / 24h resolve, HIGH: 24h ack / 7d resolve
- **Notifications**: Slack, Jira, Email, PagerDuty, Microsoft Teams, Webhooks
- **Routing rules**: Filter by severity, module, account, tags
- **Metrics**: Pre-aggregated Redis counters for dashboard (by severity, status, provider, account, region, daily trends, MTTR)

## Finding States

```
[open] → [in_progress] → [resolved]
[open] → [suppressed]
[open] → [accepted_risk]
[resolved] → [open] (regression)
```

## Notification Channels

- **Slack**: Webhook with severity routing and emoji indicators
- **Jira**: Auto-create issues with bi-directional sync
- **Email**: Real-time for CRITICAL/HIGH, daily digest for MEDIUM/LOW
- **PagerDuty**: CRITICAL severity triggers on-call escalation
- **Microsoft Teams**: Adaptive Card format
- **Webhook**: Generic JSON with HMAC-SHA256 signing

## API Endpoints

### Findings
- GET /internal/findings - List findings (with extensive filters)
- GET /internal/findings/{id} - Get finding detail
- PATCH /internal/findings/{id} - Update status
- POST /internal/findings/bulk - Bulk update (max 500)
- POST /internal/findings/submit - Direct REST submission (CI/CD)
- POST /internal/findings/{id}/suppress - Suppress with reason
- POST /internal/findings/{id}/accept-risk - Accept risk with justification
- POST /internal/findings/{id}/acknowledge - Acknowledge (SLA tracking)
- GET /internal/findings/stats - Statistics
- GET /internal/findings/sla-violations - SLA violations
- GET /internal/findings/metrics - Pre-aggregated metrics from Redis

### Suppressions
- GET /internal/suppressions - List rules
- POST /internal/suppressions - Create rule
- DELETE /internal/suppressions/{id} - Delete

### Notifications
- GET /internal/notifications/channels - List
- POST /internal/notifications/channels - Create
- PUT /internal/notifications/channels/{id} - Update
- DELETE /internal/notifications/channels/{id} - Delete
- POST /internal/notifications/channels/{id}/test - Test
- POST /internal/notifications/test - Test by body

### Incidents
- GET /internal/incidents - List incidents
- GET /internal/incidents/{id} - Get incident detail
- PATCH /internal/incidents/{id} - Update incident

## Kafka Events

### Consumed
- `finding.raw` - Raw findings from Policy Engine
- `resource.deleted` - Auto-resolve findings for deleted resources

### Produced
- `finding.created` - New finding persisted
- `finding.updated` - Finding status/context changed
- `finding.resolved` - Finding resolved
- `finding.seen_again` - Duplicate detected
- `finding.suppressed` - Finding matched suppression rule
- `incident.created` - Incident created
- `incident.updated` - Incident updated

## Performance Targets

- Ingestion throughput: 10,000 findings/second sustained
- Deduplication check: p99 < 5ms
- End-to-end latency (Kafka → Slack): p95 < 10 seconds
- Bulk operations: 500 findings in < 5 seconds

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cloudvisor

# Redis
REDIS_URL=redis://localhost:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# External services (for enrichment)
GRAPH_SERVICE_URL=http://graph:8001
POLICY_SERVICE_URL=http://policy:8003
AIOPS_SERVICE_URL=http://aiops:8010

# Alert service config
ALERT_NOTIFICATION_RATE_LIMIT=10
ALERT_NOTIFICATION_DEDUP_WINDOW_SECONDS=300
ALERT_SLA_CRITICAL_ACKNOWLEDGE_HOURS=4
ALERT_SLA_CRITICAL_RESOLVE_HOURS=24
ALERT_BULK_OPERATION_BATCH_SIZE=500
```