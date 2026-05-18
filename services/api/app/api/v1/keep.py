"""
Keep AIOps proxy routes — catch-all proxy forwarding /v1/keep/{path} to cv-keep:8007/{path}.

All requests require valid JWT authentication. The gateway injects:
  - X-Tenant-ID: from the authenticated user's organization_id
  - X-Correlation-ID: propagated or generated for distributed tracing
  - X-Source-Service: api-gateway
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import get_api_settings
from app.core.proxy import get_correlation_id

logger = logging.getLogger(__name__)

_settings = get_api_settings()

router = APIRouter(tags=["keep"])

# Headers that should not be forwarded to the upstream service
_HOP_BY_HOP_HEADERS = frozenset(
    {
        "host",
        "connection",
        "keep-alive",
        "transfer-encoding",
        "te",
        "trailer",
        "upgrade",
        "proxy-authorization",
        "proxy-authenticate",
    }
)


def _filter_headers(headers: dict[str, str]) -> dict[str, str]:
    """Remove hop-by-hop and internal headers before forwarding."""
    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in _HOP_BY_HOP_HEADERS
    }


@router.api_route(
    "/keep/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def keep_proxy(
    path: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    """
    Catch-all proxy route for the Keep AIOps service.

    Forwards requests to http://cv-keep:8007/{path} preserving:
      - HTTP method
      - Headers (filtered)
      - Query parameters
      - Request body
    """
    # Build upstream URL
    upstream_url = f"{_settings.keep_service_url.rstrip('/')}/{path}"

    # Preserve query parameters
    if request.url.query:
        upstream_url = f"{upstream_url}?{request.url.query}"

    # Build forwarded headers
    forwarded_headers = _filter_headers(dict(request.headers))

    # Inject required headers
    forwarded_headers["X-Tenant-ID"] = user.organization_id
    forwarded_headers["X-Correlation-ID"] = get_correlation_id()
    forwarded_headers["X-Source-Service"] = "api-gateway"

    # Read request body
    body = await request.body()

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=_settings.upstream_timeout,
                write=10.0,
                pool=5.0,
            ),
        ) as client:
            upstream_response = await client.request(
                method=request.method,
                url=upstream_url,
                headers=forwarded_headers,
                content=body if body else None,
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Keep service request timed out",
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502,
            detail="Keep service unavailable",
        )
    except httpx.HTTPError as exc:
        logger.error(f"Keep proxy error: {exc}")
        raise HTTPException(
            status_code=502,
            detail="Keep service unavailable",
        )

    # Build response headers (filter hop-by-hop from upstream response)
    response_headers = _filter_headers(dict(upstream_response.headers))

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )
