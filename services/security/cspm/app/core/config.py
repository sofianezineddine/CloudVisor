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


def get_cspm_settings() -> CSPMSettings:
    return CSPMSettings()
