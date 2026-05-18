"""
Multi-Tenant Middleware for Keep API

Reads the X-Tenant-ID header injected by the CloudVisor API gateway and
sets it as the Keep tenant context for the request. This ensures all
database queries are scoped to the correct tenant.

When running in NOAUTH mode within CloudVisor, the API gateway handles
JWT validation and injects X-Tenant-ID before forwarding to Keep.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Endpoints that don't require tenant context
EXEMPT_PATHS = {"/healthcheck", "/", "/docs", "/redoc", "/openapi.json"}


class TenantMiddleware(BaseHTTPMiddleware):
    """Extracts X-Tenant-ID header and sets it on request state."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip tenant check for exempt paths
        if path in EXEMPT_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # Extract tenant ID from header
        tenant_id = request.headers.get("X-Tenant-ID") or request.headers.get("x-tenant-id")

        if not tenant_id:
            logger.warning(f"Missing X-Tenant-ID header for {request.method} {path}")
            return JSONResponse(
                status_code=400,
                content={"detail": "Missing X-Tenant-ID header. All requests must include tenant context."},
            )

        # Set tenant_id on request state for downstream use
        request.state.tenant_id = tenant_id

        response = await call_next(request)
        return response
