"""Prometheus metrics for the Graph service."""

from prometheus_client import Counter, Gauge, Histogram

# ─── Gauges ──────────────────────────────────────────────────────────────────

graph_node_count = Gauge(
    "cloudvisor_graph_node_count",
    "Total number of asset nodes in the graph",
    ["organization_id"],
)

graph_edge_count = Gauge(
    "cloudvisor_graph_edge_count",
    "Total number of edges in the graph",
    ["organization_id"],
)

graph_high_risk_assets = Gauge(
    "cloudvisor_graph_high_risk_assets",
    "Number of assets with risk_score > 70",
    ["organization_id", "provider"],
)

graph_public_assets = Gauge(
    "cloudvisor_graph_public_assets",
    "Number of internet-exposed assets",
    ["organization_id", "provider"],
)

# ─── Counters ─────────────────────────────────────────────────────────────────

graph_nodes_created_total = Counter(
    "cloudvisor_graph_nodes_created_total",
    "Total asset nodes created",
    ["provider", "resource_type"],
)

graph_nodes_updated_total = Counter(
    "cloudvisor_graph_nodes_updated_total",
    "Total asset nodes updated",
    ["provider", "resource_type"],
)

graph_nodes_deleted_total = Counter(
    "cloudvisor_graph_nodes_deleted_total",
    "Total asset nodes deleted",
    ["provider"],
)

graph_edges_created_total = Counter(
    "cloudvisor_graph_edges_created_total",
    "Total edges created",
    ["relationship_type"],
)

graph_events_consumed_total = Counter(
    "cloudvisor_graph_events_consumed_total",
    "Total Kafka events consumed",
    ["event_type"],
)

graph_es_index_errors_total = Counter(
    "cloudvisor_graph_es_index_errors_total",
    "Total Elasticsearch indexing errors",
    ["operation"],
)

# ─── Histograms ───────────────────────────────────────────────────────────────

graph_query_duration_seconds = Histogram(
    "cloudvisor_graph_query_duration_seconds",
    "Duration of Neo4j query execution",
    ["query_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)

graph_risk_score_distribution = Histogram(
    "cloudvisor_graph_risk_score_distribution",
    "Distribution of asset risk scores",
    ["provider", "environment"],
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

graph_attack_path_length = Histogram(
    "cloudvisor_graph_attack_path_length",
    "Length of discovered attack paths",
    buckets=[1, 2, 3, 4, 5, 6],
)


class GraphMetrics:
    """Helper class for recording graph metrics."""

    @staticmethod
    def record_node_created(provider: str, resource_type: str) -> None:
        graph_nodes_created_total.labels(
            provider=provider, resource_type=resource_type
        ).inc()

    @staticmethod
    def record_node_updated(provider: str, resource_type: str) -> None:
        graph_nodes_updated_total.labels(
            provider=provider, resource_type=resource_type
        ).inc()

    @staticmethod
    def record_node_deleted(provider: str) -> None:
        graph_nodes_deleted_total.labels(provider=provider).inc()

    @staticmethod
    def record_edge_created(relationship_type: str) -> None:
        graph_edges_created_total.labels(relationship_type=relationship_type).inc()

    @staticmethod
    def record_event_consumed(event_type: str) -> None:
        graph_events_consumed_total.labels(event_type=event_type).inc()

    @staticmethod
    def record_query_duration(query_type: str, duration: float) -> None:
        graph_query_duration_seconds.labels(query_type=query_type).observe(duration)

    @staticmethod
    def record_risk_score(provider: str, environment: str, score: int) -> None:
        graph_risk_score_distribution.labels(
            provider=provider, environment=environment
        ).observe(score)
