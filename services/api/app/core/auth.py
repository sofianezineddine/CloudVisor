"""JWT authentication for the Public API — validates tokens via Auth service."""

import base64
import json
import logging
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


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


class AuthenticatedUser:
    """Represents the authenticated caller extracted from JWT."""

    def __init__(self, payload: dict[str, Any], token: str):
        self.user_id: str = payload.get("sub", "")
        self.organization_id: str = payload.get("org_id", "")
        self.session_id: str = payload.get("session_id", "")
        self.token: str = token

    @property
    def auth_headers(self) -> dict[str, str]:
        """Headers to forward to upstream services."""
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Org-ID": self.organization_id,
            "X-User-ID": self.user_id,
        }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthenticatedUser:
    """
    FastAPI dependency: extract and validate the authenticated user from JWT.
    The token is decoded locally for speed; the auth service validates it
    for sensitive operations via /internal/auth/validate.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Authorization: Bearer <token>",
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
