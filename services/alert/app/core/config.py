from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Service-local .env takes priority; fall back to the monorepo root .env
_service_env = Path(__file__).parent.parent.parent / ".env"               # services/alert/.env
_root_env    = Path(__file__).parent.parent.parent.parent.parent / ".env" # <root>/.env
_env_path    = _service_env if _service_env.exists() else (_root_env if _root_env.exists() else None)


class AlertSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ALERT_",
        extra="ignore",
    )

    service_name: str = Field(default="alert")
    notification_rate_limit: int = Field(default=10)
    notification_dedup_window_seconds: int = Field(default=300)
    sla_critical_acknowledge_hours: int = Field(default=4)
    sla_critical_resolve_hours: int = Field(default=24)
    sla_high_acknowledge_hours: int = Field(default=24)
    sla_high_resolve_days: int = Field(default=7)
    sla_medium_acknowledge_days: int = Field(default=7)
    sla_medium_resolve_days: int = Field(default=30)
    bulk_operation_batch_size: int = Field(default=500)


def get_alert_settings() -> AlertSettings:
    return AlertSettings()
