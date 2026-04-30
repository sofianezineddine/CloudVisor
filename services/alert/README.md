# CloudVisor Alert Service

Alert Pipeline & Notification Engine - Foundation 5 of the CloudVisor CNAPP platform.

## Features

- **Finding ingestion**: Process findings from Policy Engine
- **Deduplication**: SHA-256 fingerprinting to prevent noise
- **State machine**: open → in_progress → resolved, suppressed, accepted_risk
- **Incidents**: Group related findings
- **Suppressions**: Auto-suppress by rule, tag, account, region
- **Notifications**: Slack, Jira, Email, Webhooks
- **SLA tracking**: CRITICAL: 4h ack / 24h resolve

## Finding States

```
[open] → [in_progress] → [resolved]
[open] → [suppressed]
[open] → [accepted_risk]
[resolved] → [open] (regression)
```

## Notification Channels

- **Slack**: Webhook with severity routing
- **Jira**: Auto-create issues
- **Email**: Real-time + digest
- **Webhook**: Generic JSON

## API Endpoints

### Findings
- GET /internal/findings - List findings
- GET /internal/findings/{id} - Get finding
- PATCH /internal/findings/{id} - Update status
- POST /internal/findings/bulk - Bulk update
- GET /internal/findings/stats - Statistics

### Suppressions
- GET /internal/suppressions - List rules
- POST /internal/suppressions - Create rule
- DELETE /internal/suppressions/{id} - Delete

### Notifications
- GET /internal/notifications/channels - List
- POST /internal/notifications/channels - Create
- DELETE /internal/notifications/channels/{id} - Delete
- POST /internal/notifications/channels/{id}/test - Test