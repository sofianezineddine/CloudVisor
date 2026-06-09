"""Pydantic settings specific to the Graph service."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Service-local .env takes priority; fall back to the monorepo root .env
_service_env = Path(__file__).parent.parent.parent / ".env"               # services/graph/.env
_root_env    = Path(__file__).parent.parent.parent.parent.parent / ".env" # <root>/.env
_env_path    = _service_env if _service_env.exists() else (_root_env if _root_env.exists() else None)


class GraphSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GRAPH_",
        extra="ignore",
        populate_by_name=True,
    )

    service_name: str = Field(default="graph")
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="password")
    neo4j_database: str = Field(default="neo4j")
    neo4j_max_connection_lifetime: int = Field(default=3600)
    neo4j_max_connection_pool_size: int = Field(default=50)
    connection_timeout: int = Field(default=30)
    query_timeout: int = Field(default=60)
    elasticsearch_url: str = Field(default="http://localhost:9200")
    elasticsearch_index_prefix: str = Field(default="cloudvisor")
    # Credentials are passed without the GRAPH_ prefix from docker-compose
    elasticsearch_username: str = Field(default="", alias="ELASTICSEARCH_USERNAME")
    elasticsearch_password: str = Field(default="", alias="ELASTICSEARCH_PASSWORD")
    snapshot_retention_days: int = Field(default=90)
    risk_score_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "critical_findings": 40,
            "high_findings": 20,
            "medium_findings": 5,
            "max_findings_score": 60,
            "public_exposure": 20,
            "data_sensitivity": 15,
            "privilege_level": 10,
            "production_multiplier": 1.5,
        }
    )
    cache_ttl_seconds: int = Field(default=60)


def get_graph_settings() -> GraphSettings:
    return GraphSettings()
