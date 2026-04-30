"""Configuration for the Public API service."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Service-local .env takes priority; fall back to the monorepo root .env
_service_env = Path(__file__).parent.parent.parent / ".env"               # services/api/.env
_root_env    = Path(__file__).parent.parent.parent.parent.parent / ".env" # <root>/.env
_env_path    = _service_env if _service_env.exists() else (_root_env if _root_env.exists() else None)


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="API_",
        extra="ignore",
    )

    service_name: str = Field(default="api")
    version: str = Field(default="v1")

    # Upstream service URLs (internal Docker network)
    auth_service_url: str = Field(default="http://cv-auth:8002")
    connector_service_url: str = Field(default="http://cv-connector:8000")
    graph_service_url: str = Field(default="http://cv-graph:8001")
    policy_service_url: str = Field(default="http://cv-policy:8003")
    alert_service_url: str = Field(default="http://cv-alert:8004")
    cspm_service_url: str = Field(default="http://cv-cspm:8006")
    copilot_service_url: str = Field(default="http://cv-copilot:8010")

    # Rate limiting
    rate_limit_requests_per_minute: int = Field(default=600)
    rate_limit_burst: int = Field(default=100)

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:3001"])

    # Request timeout to upstream services (seconds)
    upstream_timeout: float = Field(default=30.0)


def get_api_settings() -> APISettings:
    return APISettings()
