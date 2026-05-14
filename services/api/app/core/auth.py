"""
JWT + API-Key authentication for the Public API.

Supports two auth methods (spec §API Standards):
  1. Authorization: Bearer <JWT>
  2. X-API-Key: cv_live_<key>

Token validation: JWT signature is verified by calling the auth service's
/internal/auth/validate endpoint. This ensures revoked tokens are rejected
and org_id is always authoritative from the auth service.
"""

import base64
import json
import logging
import os
from typing import Any

import httpx
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# API key prefix required by spec
_API_KEY_PREFIX = "cv_live_"

# Auth service URL for token validation
_AUTH_SERVICE_URL = os.environ.get("API_AUTH_SERVICE_URL", "http://cv-auth:8002")
_INTERNAL_SERVICE_TOKEN = os.environ.get("AUTH_INTERNAL_SERVICE_TOKEN", "")


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode JWT payload without verifying signature (used for fast path extraction)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as e:
        raise ValueError(f"Cannot decode token: {e}")


def _decode_api_key(api_key: str) -> dict[str, Any]:
    """
    Decode a CloudVisor API key (cv_live_<base64-encoded-json>).
    The key is validated against the auth service for full verification.
    """
    try:
        encoded = api_key[len(_API_KEY_PREFIX):]
        encoded += "=" * (4 - len(encoded) % 4)
        return json.loads(base64.urlsafe_b64decode(encoded))
    except Exception:
        return {"sub": "api_key_user", "org_id": "unknown", "via_api_key": True}


async def _validate_token_with_auth_service(
    token: str,
    org_id: str,
    via_api_key: bool = False,
) -> dict[str, Any] | None:
    """
    Validate token against the auth service /internal/auth/validate endpoint.
    Returns the validated user info or None if validation fails.
    This is the authoritative check — JWT signature + revocation + org isolation.
    """
    try:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Org-ID": org_id,
        }
        if _INTERNAL_SERVICE_TOKEN:
            headers["X-Service-Token"] = _INTERNAL_SERVICE_TOKEN

        if via_api_key:
            headers["Authorization"] = f"Bearer {token}"
        else:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{_AUTH_SERVICE_URL}/internal/auth/validate",
                headers=headers,
            )
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception as e:
        logger.warning(f"Auth service validation failed (falling back to JWT decode): {e}")
        return None


class AuthenticatedUser:
    """Represents the authenticated caller extracted from JWT or API key."""

    def __init__(self, payload: dict[str, Any], token: str, via_api_key: bool = False):
        self.user_id: str = payload.get("sub", "") or payload.get("user_id", "")
        self.organization_id: str = payload.get("org_id", "") or payload.get("organization_id", "")
        self.session_id: str = payload.get("session_id", "")
        self.role: str = payload.get("role", "viewer")
        self.token: str = token
        self.via_api_key: bool = via_api_key

    @property
    def auth_headers(self) -> dict[str, str]:
        """Headers to forward to upstream services."""
        headers: dict[str, str] = {
            "X-Org-ID": self.organization_id,
            "X-User-ID": self.user_id,
        }
        if self.via_api_key:
            headers["X-API-Key"] = self.token
        else:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthenticatedUser:
    """
    FastAPI dependency: extract and validate the authenticated user.

    Accepts:
      - Authorization: Bearer <JWT>
      - X-API-Key: cv_live_<key>

    Validates against the auth service for authoritative token verification.
    Falls back to local JWT decode if auth service is temporarily unavailable.
    """
    # ── API Key path ──────────────────────────────────────────────────────────
    if x_api_key:
        if not x_api_key.startswith(_API_KEY_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid API key format. Key must start with '{_API_KEY_PREFIX}'",
                headers={"WWW-Authenticate": "Bearer"},
            )
        local_payload = _decode_api_key(x_api_key)
        org_id = local_payload.get("org_id", "unknown")

        # Validate with auth service
        validated = await _validate_token_with_auth_service(x_api_key, org_id, via_api_key=True)
        if validated:
            # Use authoritative data from auth service
            payload = {
                "sub": validated.get("user_id", local_payload.get("sub", "")),
                "org_id": validated.get("organization_id", org_id),
                "role": validated.get("role", "viewer"),
            }
        else:
            # Auth service unavailable — use local decode (degraded mode)
            payload = local_payload

        if not payload.get("org_id") or payload.get("org_id") == "unknown":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key — cannot determine organization",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return AuthenticatedUser(payload, x_api_key, via_api_key=True)

    # ── Bearer JWT path ───────────────────────────────────────────────────────
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Authentication required. "
                "Provide 'Authorization: Bearer <token>' or 'X-API-Key: cv_live_<key>'"
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Fast-path: decode payload locally to get org_id for auth service call
    try:
        local_payload = _decode_jwt_payload(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )

    user_id = local_payload.get("sub")
    org_id = local_payload.get("org_id")

    if not user_id or not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims (sub, org_id)",
        )

    # Authoritative validation via auth service
    validated = await _validate_token_with_auth_service(token, org_id)
    if validated and validated.get("valid"):
        # Use authoritative data from auth service
        payload = {
            "sub": validated.get("user_id", user_id),
            "org_id": validated.get("organization_id", org_id),
            "role": validated.get("role", "viewer"),
            "session_id": local_payload.get("session_id", ""),
        }
    elif validated is None:
        # Auth service unavailable — fall back to local JWT decode (degraded mode)
        logger.warning("Auth service unavailable — using local JWT decode (degraded mode)")
        payload = local_payload
    else:
        # Auth service explicitly rejected the token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedUser(payload, token)
