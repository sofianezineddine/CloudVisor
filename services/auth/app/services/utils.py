"""JWT token utilities."""

from datetime import datetime, timedelta
from typing import Any

from jose import jwt


def create_access_token(
    data: dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def create_refresh_token(
    data: dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=30)

    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def decode_token(token: str, secret_key: str) -> dict[str, Any]:
    """Decode and verify JWT token."""
    return jwt.decode(token, secret_key, algorithms=["RS256", "HS256"])


def create_api_key_token(
    data: dict[str, Any],
    secret_key: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT token for API key authentication."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=365)

    to_encode.update({"exp": expire, "type": "api_key"})
    return jwt.encode(to_encode, secret_key, algorithm="HS256")
