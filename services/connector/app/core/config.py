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
    polling_interval_default: int = Field(default=1)  # 1 minute for near-real-time
    polling_interval_options: list[int] = Field(default=[1, 5, 15, 30, 60])
    sync_timeout_seconds: int = Field(default=300)
    batch_size: int = Field(default=100)
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Also read VAULT_* env vars (without CONNECTOR_ prefix)
        if not self.vault_enabled:
            self.vault_enabled = os.getenv("VAULT_ENABLED", "false").lower() == "true"
        if self.vault_url == "http://localhost:8200":
            self.vault_url = os.getenv("VAULT_URL", self.vault_url)
        if not self.vault_token:
            self.vault_token = os.getenv("VAULT_TOKEN")

    @field_validator("polling_interval_options", mode="before")
    @classmethod
    def parse_interval_options(cls, v: list[int] | str) -> list[int]:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",")]
        return v


def get_connector_settings() -> ConnectorSettings:
    return ConnectorSettings()
