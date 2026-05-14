"""CSPM service configuration — base settings and module-specific configuration."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Service-local .env takes priority; fall back to the monorepo root .env
_service_env = Path(__file__).parent.parent.parent / ".env"               # services/security/cspm/.env
_root_env    = Path(__file__).parent.parent.parent.parent.parent.parent / ".env"  # <root>/.env
_env_path    = _service_env if _service_env.exists() else (_root_env if _root_env.exists() else None)


class CSPMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CSPM_",
        extra="ignore",
    )

    service_name: str = "cspm"
    policy_service_url: str = "http://localhost:8003"
    kafka_bootstrap_servers: str = "localhost:9092"
    scan_interval_hours: int = 24

    # ── Service URLs ──────────────────────────────────────────────────────────
    graph_service_url: str = "http://cv-graph:8002"
    opa_service_url: str = "http://cv-policy:8003"
    # Auth service URL for JWT validation — read from AUTH_SERVICE_URL env var
    # (no CSPM_ prefix since it's a shared infrastructure URL)
    auth_service_url: str = "http://cv-auth:8002"

    # ── IAM Analyzer ──────────────────────────────────────────────────────────
    iam_lookback_days: int = 90
    iam_dormant_threshold_days: int = 90
    iam_key_rotation_threshold_days: int = 90
    iam_excess_privilege_threshold: float = 0.3  # 30% excess triggers finding

    # ── Attack Path Engine ────────────────────────────────────────────────────
    attack_path_max_hops: int = 6
    attack_path_critical_hop_threshold: int = 3
    blast_radius_max_depth: int = 4

    # ── Drift Detector ────────────────────────────────────────────────────────
    drift_baseline_retention_days: int = 90
    drift_behavioral_window_days: int = 30
    drift_anomaly_stddev_threshold: float = 2.0
    drift_correlation_window_seconds: int = 900  # 15 minutes
    drift_alert_suppression_seconds: int = 3600  # 1 hour

    # ── Policy Engine ─────────────────────────────────────────────────────────
    policy_exception_max_days: int = 365

    # ── Kafka Topics ──────────────────────────────────────────────────────────
    kafka_topic_resource_discovered: str = "resource.discovered"
    kafka_topic_resource_updated: str = "resource.updated"
    kafka_topic_finding_created: str = "finding.created"
    kafka_topic_drift_detected: str = "drift.detected"
    kafka_topic_drift_security_relevant: str = "drift.security_relevant"
    kafka_topic_anomaly_detected: str = "anomaly.detected"
    kafka_topic_cspm_alerts: str = "cspm.alerts"
    kafka_topic_policy_auto_remediate: str = "policy.auto_remediate"
    kafka_topic_iam_analysis_complete: str = "iam.analysis_complete"

    # ── Timeouts (seconds) ────────────────────────────────────────────────────
    http_timeout: float = 30.0
    graph_query_timeout: float = 60.0


def get_cspm_settings() -> CSPMSettings:
    return CSPMSettings()
