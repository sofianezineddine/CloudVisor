"""CSPM service — internal auth helper.

The CSPM service is an INTERNAL service called only by the API gateway (cv-api).
The API gateway authenticates the user's JWT, extracts the organization_id,
and passes it as the `org_id` query parameter on every request.

The CSPM service trusts this parameter because:
1. It is only reachable from within the Docker network (not exposed externally)
2. The API gateway has already validated the JWT before forwarding
3. mTLS between services is the production hardening path (not yet implemented)

DO NOT require a Bearer token here — the CSPM service has no access_token
from the user; only the API gateway does.
"""

import logging
from typing import Optional

from fastapi import Query

logger = logging.getLogger(__name__)


def require_org_id(
    org_id: Optional[str] = Query(default=None, alias="org_id"),
) -> str:
    """Extract organization_id from the org_id query parameter.

    The API gateway always sets this after validating the user's JWT.
    Returns 'default' as a fallback for development/testing only.
    """
    return org_id or "default"
