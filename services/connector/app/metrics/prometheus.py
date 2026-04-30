"""Prometheus metrics exporter for Connector service."""

from prometheus_client import Counter, Gauge, Histogram, generate_latest

# ─── Gauges (instantaneous values) ──────────────────────────────────────────

connector_last_sync_age_seconds = Gauge(
    "cloudvisor_connector_last_sync_age_seconds",
    "Seconds since last successful sync for an account",
    ["organization_id", "account_id", "provider"],
)

connector_resources_total = Gauge(
    "cloudvisor_connector_resources_total",
    "Total number of resources discovered for an account",
    ["organization_id", "account_id", "provider"],
)

connector_sync_status = Gauge(
    "cloudvisor_connector_sync_status",
    "Current sync status (1=active, 0=error, -1=idle)",
    ["organization_id", "account_id", "provider"],
)

connector_error_rate = Gauge(
    "cloudvisor_connector_error_rate",
    "Current error rate for an account (0.0 - 1.0)",
    ["organization_id", "account_id", "provider"],
)

# ─── Counters (cumulative values) ───────────────────────────────────────────

connector_discovered_resources_total = Counter(
    "cloudvisor_connector_discovered_resources_total",
    "Total number of resources discovered across all syncs",
    ["organization_id", "account_id", "provider", "resource_type"],
)

connector_updated_resources_total = Counter(
    "cloudvisor_connector_updated_resources_total",
    "Total number of resources updated across all syncs",
    ["organization_id", "account_id", "provider", "resource_type"],
)

connector_deleted_resources_total = Counter(
    "cloudvisor_connector_deleted_resources_total",
    "Total number of resources deleted across all syncs",
    ["organization_id", "account_id", "provider", "resource_type"],
)

connector_errors_total = Counter(
    "cloudvisor_connector_errors_total",
    "Total number of errors encountered during sync",
    ["organization_id", "account_id", "provider", "error_type"],
)

connector_syncs_total = Counter(
    "cloudvisor_connector_syncs_total",
    "Total number of sync operations completed",
    ["organization_id", "account_id", "provider", "sync_type", "status"],
)

connector_events_published_total = Counter(
    "cloudvisor_connector_events_published_total",
    "Total number of Kafka events published",
    ["event_type", "provider"],
)

# ─── Histograms (distribution values) ───────────────────────────────────────

connector_sync_duration_seconds = Histogram(
    "cloudvisor_connector_sync_duration_seconds",
    "Duration of sync operations in seconds",
    ["organization_id", "account_id", "provider", "sync_type"],
    buckets=[1, 5, 15, 30, 60, 120, 300, 600],
)

connector_api_latency_seconds = Histogram(
    "cloudvisor_connector_api_latency_seconds",
    "Latency of cloud provider API calls in seconds",
    ["provider", "api_service", "operation"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

connector_resource_processing_seconds = Histogram(
    "cloudvisor_connector_resource_processing_seconds",
    "Time to process and normalize a resource",
    ["provider", "resource_type"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 5],
)


class ConnectorMetrics:
    """Helper class for recording connector metrics."""

    @staticmethod
    def record_sync_start(
        organization_id: str,
        account_id: str,
        provider: str,
        sync_type: str,
    ) -> None:
        """Record start of a sync operation."""
        connector_sync_status.labels(
            organization_id=organization_id,
            account_id=account_id,
            provider=provider,
        ).set(1)

    @staticmethod
    def record_sync_complete(
        organization_id: str,
        account_id: str,
        provider: str,
        sync_type: str,
        status: str,
        duration_seconds: float,
        discovered: int = 0,
        updated: int = 0,
        deleted: int = 0,
        errors: int = 0,
        resource_count: int = 0,
    ) -> None:
        """Record completion of a sync operation."""
        # Update status gauge
        status_value = 1 if status == "completed" else 0
        connector_sync_status.labels(
            organization_id=organization_id,
            account_id=account_id,
            provider=provider,
        ).set(status_value)

        # Update sync age
        connector_last_sync_age_seconds.labels(
            organization_id=organization_id,
            account_id=account_id,
            provider=provider,
        ).set(0)

        # Update resource counts
        connector_resources_total.labels(
            organization_id=organization_id,
            account_id=account_id,
            provider=provider,
        ).set(resource_count)

        # Record sync counter
        connector_syncs_total.labels(
            organization_id=organization_id,
            account_id=account_id,
            provider=provider,
            sync_type=sync_type,
            status=status,
        ).inc()

        # Record duration histogram
        connector_sync_duration_seconds.labels(
            organization_id=organization_id,
            account_id=account_id,
            provider=provider,
            sync_type=sync_type,
        ).observe(duration_seconds)

    @staticmethod
    def record_error(
        organization_id: str,
        account_id: str,
        provider: str,
        error_type: str,
    ) -> None:
        """Record an error occurrence."""
        connector_errors_total.labels(
            organization_id=organization_id,
            account_id=account_id,
            provider=provider,
            error_type=error_type,
        ).inc()

    @staticmethod
    def record_event_published(
        event_type: str,
        provider: str,
    ) -> None:
        """Record a Kafka event publication."""
        connector_events_published_total.labels(
            event_type=event_type,
            provider=provider,
        ).inc()

    @staticmethod
    def record_api_latency(
        provider: str,
        api_service: str,
        operation: str,
        duration_seconds: float,
    ) -> None:
        """Record cloud provider API call latency."""
        connector_api_latency_seconds.labels(
            provider=provider,
            api_service=api_service,
            operation=operation,
        ).observe(duration_seconds)
