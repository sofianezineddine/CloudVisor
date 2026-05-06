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

    # ── JWT algorithm — spec §3.3 requires RS256 ─────────────────────────────
    # Set algorithm=RS256 and provide rsa_private_key / rsa_public_key in .env
    # to enable asymmetric signing.  Falls back to HS256 when keys are absent.
    algorithm: str = Field(default="RS256")
    # PEM-encoded RSA private key (used to sign tokens).
    # Set AUTH_RSA_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..." in .env
    rsa_private_key: str = Field(default="")
    # PEM-encoded RSA public key (used to verify tokens by other services).
    # Set AUTH_RSA_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n..." in .env
    rsa_public_key: str = Field(default="")

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

    # ── Audit log retention — spec §3.3: 365 days minimum ────────────────────
    audit_log_retention_days: int = Field(default=365)

    @property
    def effective_private_key(self) -> str | None:
        """Return RSA private key if configured, else None (triggers HS256 fallback).
        
        Handles both real newlines and escaped \\n sequences from .env files.
        """
        key = self.rsa_private_key.strip()
        if not key:
            return None
        # Replace escaped \n sequences with real newlines (common in .env files)
        if '\\n' in key:
            key = key.replace('\\n', '\n')
        return key

    @property
    def effective_public_key(self) -> str | None:
        """Return RSA public key if configured, else None.
        
        Handles both real newlines and escaped \\n sequences from .env files.
        """
        key = self.rsa_public_key.strip()
        if not key:
            return None
        if '\\n' in key:
            key = key.replace('\\n', '\n')
        return key


def get_auth_settings() -> AuthSettings:
    return AuthSettings()
