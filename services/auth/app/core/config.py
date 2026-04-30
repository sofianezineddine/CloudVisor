"""Pydantic settings specific to the Auth service."""

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Service-local .env takes priority; fall back to the monorepo root .env
_service_env = Path(__file__).parent.parent.parent / ".env"          # services/auth/.env
_root_env    = Path(__file__).parent.parent.parent.parent.parent / ".env"  # <root>/.env
_env_path    = _service_env if _service_env.exists() else (_root_env if _root_env.exists() else None)


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        extra="ignore",
    )

    service_name: str = Field(default="auth")
    secret_key: str = Field(default="change-me-in-production-min-32-chars!")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15)
    refresh_token_expire_days: int = Field(default=30)
    bcrypt_rounds: int = Field(default=12)
    mfa_issuer: str = Field(default="CloudVisor")
    session_expire_days: int = Field(default=7)
    session_inactive_days: int = Field(default=7)
    api_key_prefix: str = Field(default="cv_live_")
    api_key_length: int = Field(default=32)
    rate_limit_per_minute: int = Field(default=60)

    # CORS configuration
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:3001")

    default_role: str = Field(default="viewer")
    enterprise_role: str = Field(default="admin")

    require_mfa_enterprise: bool = Field(default=False)
    password_min_length: int = Field(default=8)
    password_require_uppercase: bool = Field(default=True)
    password_require_lowercase: bool = Field(default=True)
    password_require_digit: bool = Field(default=True)
    password_require_special: bool = Field(default=False)

    oauth_google_enabled: bool = Field(default=False)
    oauth_google_client_id: str = Field(default="")
    oauth_google_client_secret: str = Field(default="")

    oauth_github_enabled: bool = Field(default=False)
    oauth_github_client_id: str = Field(default="")
    oauth_github_client_secret: str = Field(default="")

    saml_enabled: bool = Field(default=False)
    oidc_enabled: bool = Field(default=False)


def get_auth_settings() -> AuthSettings:
    return AuthSettings()
