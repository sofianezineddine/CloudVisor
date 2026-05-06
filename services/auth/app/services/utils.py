"""JWT token utilities — RS256 (spec §3.3) with HS256 fallback."""

import logging
from datetime import datetime, timedelta
from typing import Any

from jose import jwt

logger = logging.getLogger(__name__)


def create_access_token(
    data: dict[str, Any],
    secret_key: str,
    algorithm: str = "RS256",
    expires_delta: timedelta | None = None,
    private_key: str | None = None,
) -> str:
    """Create JWT access token.

    Uses RS256 (asymmetric) when a private_key is provided — spec requirement.
    Falls back to HS256 with secret_key when no RSA key is configured.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})

    sign_key = private_key if (algorithm == "RS256" and private_key) else secret_key
    effective_alg = algorithm if (algorithm == "RS256" and private_key) else "HS256"
    return jwt.encode(to_encode, sign_key, algorithm=effective_alg)


def create_refresh_token(
    data: dict[str, Any],
    secret_key: str,
    algorithm: str = "RS256",
    expires_delta: timedelta | None = None,
    private_key: str | None = None,
) -> str:
    """Create JWT refresh token (same signing strategy as access token)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=30))
    to_encode.update({"exp": expire, "type": "refresh"})

    sign_key = private_key if (algorithm == "RS256" and private_key) else secret_key
    effective_alg = algorithm if (algorithm == "RS256" and private_key) else "HS256"
    return jwt.encode(to_encode, sign_key, algorithm=effective_alg)


def decode_token(
    token: str,
    secret_key: str,
    public_key: str | None = None,
) -> dict[str, Any]:
    """Decode and verify JWT token.

    Tries RS256 with public_key first (spec), falls back to HS256 with secret_key.
    Accepts both algorithms so tokens issued before a key rotation still work.
    """
    if public_key:
        try:
            return jwt.decode(token, public_key, algorithms=["RS256"])
        except Exception:
            pass  # fall through to HS256

    return jwt.decode(token, secret_key, algorithms=["HS256"])


def create_api_key_token(
    data: dict[str, Any],
    secret_key: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT token for API key authentication (always HS256 — no user session)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=365))
    to_encode.update({"exp": expire, "type": "api_key"})
    return jwt.encode(to_encode, secret_key, algorithm="HS256")
