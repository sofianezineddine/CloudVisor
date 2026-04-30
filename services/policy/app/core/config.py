"""Pydantic settings for Policy service."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Service-local .env takes priority; fall back to the monorepo root .env
_service_env = Path(__file__).parent.parent.parent / ".env"               # services/policy/.env
_root_env    = Path(__file__).parent.parent.parent.parent.parent / ".env" # <root>/.env
_env_path    = _service_env if _service_env.exists() else (_root_env if _root_env.exists() else None)


class PolicySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POLICY_",
        extra="ignore",
    )

    service_name: str = Field(default="policy")
    opa_url: str = Field(default="http://localhost:8181")
    opa_check_interval_seconds: int = Field(default=60)
    rules_repo_url: str = Field(default="")
    rules_repo_path: str = Field(default="./rules/rego")
    rules_repo_branch: str = Field(default="main")
    compliance_cache_ttl: int = Field(default=300)

    supported_frameworks: list[str] = Field(
        default_factory=lambda: [
            "CIS-AWS",
            "CIS-Azure",
            "CIS-GCP",
            "CIS-OCI",
            "SOC2",
            "PCI-DSS",
            "HIPAA",
            "ISO27001",
            "NIST-800-53",
            "GDPR",
            "FedRAMP",
            "CCPA",
        ]
    )


def get_policy_settings() -> PolicySettings:
    return PolicySettings()
