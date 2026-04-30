"""Auth helpers for the connector service — extracts org_id from JWT."""

import logging
from typing import Any

from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode JWT payload without verifying signature (connector trusts the auth service)."""
    import base64
    import json

    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        # Add padding if needed
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)
    except Exception as e:
        raise ValueError(f"Failed to decode JWT: {e}")


def get_org_id_from_token(authorization: str | None) -> str | None:
    """Extract organization_id from Bearer JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.replace("Bearer ", "").strip()
    try:
        payload = _decode_jwt_payload(token)
        return payload.get("org_id")
    except Exception:
        return None


async def require_org_id(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
) -> str:
    """
    FastAPI dependency: extract and return the organization_id.

    Priority:
    1. X-Org-ID header (explicit, set by API gateway)
    2. org_id claim in JWT Bearer token
    """
    # Try explicit header first (set by API gateway or frontend)
    if x_org_id and x_org_id.strip():
        return x_org_id.strip()

    # Fall back to JWT claim
    org_id = get_org_id_from_token(authorization)
    if org_id:
        return org_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Organization ID could not be determined. Ensure you are authenticated.",
    )
