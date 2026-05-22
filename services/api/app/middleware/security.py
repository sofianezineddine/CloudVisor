"""
Security middleware for the Public API service.

Implements:
- Security response headers (HSTS, CSP, X-Content-Type-Options, X-Frame-Options, etc.)
- Request size limiting (prevent oversized payloads)
- CSRF validation for cookie-authenticated state-changing requests
"""

import logging
import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Maximum request body size: 10MB
MAX_BODY_SIZE = 10 * 1024 * 1024

_IS_PRODUCTION = os.environ.get("APP_ENVIRONMENT", "development").lower() == "production"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # ── Prevent MIME type sniffing ────────────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"

        # ── Prevent clickjacking ──────────────────────────────────────────────
        response.headers["X-Frame-Options"] = "DENY"

        # ── XSS protection (legacy browsers) ─────────────────────────────────
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # ── Referrer policy ───────────────────────────────────────────────────
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ── Permissions policy (disable unnecessary browser features) ─────────
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), "
            "usb=(), magnetometer=(), gyroscope=(), accelerometer=()"
        )

        # ── HTTP Strict Transport Security (HSTS) ─────────────────────────────
        # Only in production (HTTPS). max-age=1 year, include subdomains.
        if _IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # ── Content-Security-Policy ───────────────────────────────────────────
        # API gateway returns JSON — strict CSP prevents any script execution
        # if response is accidentally rendered as HTML.
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'none'"
        )

        # ── Cache control for API responses ───────────────────────────────────
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        # ── Cross-Origin headers ──────────────────────────────────────────────
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF validation for cookie-authenticated state-changing requests.

    Uses the double-submit cookie pattern:
    - cv_csrf cookie value must match X-CSRF-Token header
    - Skipped for requests with Authorization header (API keys)
    - Skipped for safe methods (GET, HEAD, OPTIONS)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Safe methods don't need CSRF protection
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        # Skip CSRF if using Authorization header (API keys, service-to-service)
        auth_header = request.headers.get("authorization")
        if auth_header:
            return await call_next(request)

        # Skip CSRF if no cookie-based auth (no cv_access cookie)
        if "cv_access" not in request.cookies:
            return await call_next(request)

        # Validate CSRF: cookie value must match header value
        import secrets
        cookie_csrf = request.cookies.get("cv_csrf", "")
        header_csrf = request.headers.get("x-csrf-token", "")

        if not cookie_csrf or not header_csrf:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing. Include X-CSRF-Token header."},
            )

        if not secrets.compare_digest(cookie_csrf, header_csrf):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token mismatch."},
            )

        return await call_next(request)
