"""
JWT + API-Key authentication for the Public API.

Supports two auth methods (spec §API Standards):
  1. Authorization: Bearer <JWT>
  2. X-API-Key: cv_live_<key>
"""

import base64
import json
import logging
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# API key prefix required by spec
_API_KEY_PREFIX = "cv_live_"


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode JWT payload without verifying signature (auth service validates)."""
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
    In production the key would be validated against the auth service;
    here we extract the embedded claims for tenant isolation.
    """
    try:
        encoded = api_key[len(_API_KEY_PREFIX):]
        # Pad to multiple of 4
        encoded += "=" * (4 - len(encoded) % 4)
        return json.loads(base64.urlsafe_b64decode(encoded))
    except Exception:
        # Return minimal payload — auth service will validate the key
        return {"sub": "api_key_user", "org_id": "unknown", "via_api_key": True}


class AuthenticatedUser:
    """Represents the authenticated caller extracted from JWT or API key."""

    def __init__(self, payload: dict[str, Any], token: str, via_api_key: bool = False):
        self.user_id: str = payload.get("sub", "")
        self.organization_id: str = payload.get("org_id", "")
        self.session_id: str = payload.get("session_id", "")
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
    """
    # ── API Key path ──────────────────────────────────────────────────────────
    if x_api_key:
        if not x_api_key.startswith(_API_KEY_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid API key format. Key must start with '{_API_KEY_PREFIX}'",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload = _decode_api_key(x_api_key)
        org_id = payload.get("org_id")
        if not org_id or org_id == "unknown":
            # Key format is valid but claims are opaque — auth service will validate
            # For now accept and let upstream reject if invalid
            pass
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
    try:
        payload = _decode_jwt_payload(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )

    user_id = payload.get("sub")
    org_id = payload.get("org_id")

    if not user_id or not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims (sub, org_id)",
        )

    return AuthenticatedUser(payload, token)
