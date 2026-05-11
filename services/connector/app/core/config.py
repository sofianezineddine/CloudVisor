"""Pydantic settings specific to the Cloud Connector service."""

import os
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Service-local .env takes priority; fall back to the monorepo root .env
_service_env = Path(__file__).parent.parent.parent / ".env"               # services/connector/.env
_root_env    = Path(__file__).parent.parent.parent.parent.parent / ".env" # <root>/.env
_env_path    = _service_env if _service_env.exists() else (_root_env if _root_env.exists() else None)


class ConnectorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CONNECTOR_",
        extra="ignore",
    )

    service_name: str = Field(default="connector")
    # Spec §3.1: default is 15 min, allowed 5/15/30/60. 1 is dev-only.
    polling_interval_default: int = Field(default=15)
    polling_interval_options: list[int] = Field(default=[1, 5, 15, 30, 60])
    sync_timeout_seconds: int = Field(default=300)
    batch_size: int = Field(default=100)
    # ── Freshness sweep ──────────────────────────────────────────────────────
    # A resource missing from N consecutive full syncs is marked deleted.
    # For fewer than N misses, it's marked ``stale`` but kept visible so
    # transient permission/api issues don't wipe the inventory.
    stale_to_deleted_threshold: int = Field(default=3)
    circuit_breaker_error_threshold: float = Field(default=0.5)
    circuit_breaker_window_seconds: int = Field(default=300)
    circuit_breaker_pause_seconds: int = Field(default=900)
    max_retries: int = Field(default=5)
    base_retry_delay_seconds: float = Field(default=1.0)
    max_retry_delay_seconds: float = Field(default=60.0)
    vault_enabled: bool = Field(default=False)
    vault_url: str = Field(default="http://localhost:8200")
    vault_token: str | None = Field(default=None)
    vault_mount_point: str = Field(default="cloudvisor/credentials")
    event_target_latency_seconds: int = Field(default=60)

    # ── Real-time consumer configuration ──────────────────────────────────────
    # AWS CloudTrail → SQS
    # Set CONNECTOR_REALTIME_ENABLED=true to activate all real-time consumers.
    # Each provider consumer is only started when its required env vars are set.
    realtime_enabled: bool = Field(default=False)

    # ── Kafka / Schema Registry ────────────────────────────────────────────────
    # Confluent Schema Registry URL for Avro serialization.
    # When set and reachable, all Kafka events are serialized as Avro.
    # When unset or unreachable, falls back to plain JSON (dev-friendly).
    schema_registry_url: str = Field(default="")

    aws_cloudtrail_sqs_queue_url: str = Field(default="")
    aws_cloudtrail_region: str = Field(default="us-east-1")

    # Azure: Azure Monitor → Event Hub → Connector
    azure_event_hub_connection_string: str = Field(default="")
    azure_event_hub_name: str = Field(default="cloudvisor-activity-logs")
    azure_event_hub_consumer_group: str = Field(default="$Default")

    # GCP: Cloud Asset Inventory → Pub/Sub → Connector
    gcp_pubsub_subscription: str = Field(default="")

    # OCI: OCI Events → Streaming → Connector
    oci_stream_ocid: str = Field(default="")
    oci_stream_endpoint: str = Field(default="")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Also read VAULT_* env vars (without CONNECTOR_ prefix)
        if not self.vault_enabled:
            self.vault_enabled = os.getenv("VAULT_ENABLED", "false").lower() == "true"
        if self.vault_url == "http://localhost:8200":
            self.vault_url = os.getenv("VAULT_URL", self.vault_url)
        if not self.vault_token:
            self.vault_token = os.getenv("VAULT_TOKEN")

        # Also accept bare env var names (without CONNECTOR_ prefix) for real-time config
        if not self.realtime_enabled:
            self.realtime_enabled = os.getenv("REALTIME_ENABLED", "false").lower() == "true"
        if not self.aws_cloudtrail_sqs_queue_url:
            self.aws_cloudtrail_sqs_queue_url = os.getenv("CLOUDTRAIL_SQS_QUEUE_URL", "")
        if not self.azure_event_hub_connection_string:
            self.azure_event_hub_connection_string = os.getenv(
                "AZURE_EVENT_HUB_CONNECTION_STRING", ""
            )
        if not self.azure_event_hub_name:
            env_val = os.getenv("AZURE_EVENT_HUB_NAME", "")
            if env_val:
                self.azure_event_hub_name = env_val
        if not self.gcp_pubsub_subscription:
            self.gcp_pubsub_subscription = os.getenv("GCP_PUBSUB_SUBSCRIPTION", "")
        if not self.oci_stream_ocid:
            self.oci_stream_ocid = os.getenv("OCI_STREAM_OCID", "")
        if not self.oci_stream_endpoint:
            self.oci_stream_endpoint = os.getenv("OCI_STREAM_ENDPOINT", "")

        # Schema Registry — accept both prefixed and bare env var names
        if not self.schema_registry_url:
            self.schema_registry_url = os.getenv(
                "KAFKA_SCHEMA_REGISTRY_URL",
                os.getenv("SCHEMA_REGISTRY_URL", ""),
            )

    @field_validator("polling_interval_options", mode="before")
    @classmethod
    def parse_interval_options(cls, v: list[int] | str) -> list[int]:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",")]
        return v


def get_connector_settings() -> ConnectorSettings:
    return ConnectorSettings()
