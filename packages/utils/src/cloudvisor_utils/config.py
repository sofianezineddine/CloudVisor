"""Structured configuration for CloudVisor services using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")

    url: str = Field(default="postgresql+asyncpg://cvadmin:cvpassword@localhost:5432/cloudvisor")
    pool_size: int = Field(default=20)
    max_overflow: int = Field(default=10)
    echo: bool = Field(default=False)


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")

    url: str = Field(default="redis://localhost:6379/0")
    password: str | None = Field(default=None)
    db: int = Field(default=0)
    ssl: bool = Field(default=False)


class KafkaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KAFKA_", extra="ignore")

    bootstrap_servers: str = Field(default="localhost:9092")
    schema_registry_url: str = Field(default="http://localhost:8081")
    consumer_group_prefix: str = Field(default="cloudvisor")
    sasl_mechanism: str = Field(default="PLAIN")
    sasl_username: str | None = Field(default=None)
    sasl_password: str | None = Field(default=None)
    security_protocol: str = Field(default="PLAINTEXT")

    resource_discovered_topic: str = Field(default="resource.discovered")
    resource_updated_topic: str = Field(default="resource.updated")
    resource_deleted_topic: str = Field(default="resource.deleted")
    connector_sync_started_topic: str = Field(default="connector.sync_started")
    connector_sync_finished_topic: str = Field(default="connector.sync_finished")
    connector_health_changed_topic: str = Field(default="connector.health_changed")


class OTelSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OTEL_", extra="ignore")

    service_name: str = Field(default="cloudvisor-service")
    otlp_endpoint: str = Field(default="http://localhost:4317")
    enabled: bool = Field(default=True)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    service_name: str = Field(default="cloudvisor")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    api_prefix: str = Field(default="/internal")
    workers: int = Field(default=1)


class VaultSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VAULT_", extra="ignore")

    url: str = Field(default="http://localhost:8200")
    token: str | None = Field(default=None)
    mount_point: str = Field(default="cloudvisor")
    enabled: bool = Field(default=False)


class CloudvisorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    otel: OTelSettings = Field(default_factory=OTelSettings)
    vault: VaultSettings = Field(default_factory=VaultSettings)


def get_settings() -> CloudvisorSettings:
    return CloudvisorSettings()
