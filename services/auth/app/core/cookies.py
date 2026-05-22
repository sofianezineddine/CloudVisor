"""
HttpOnly Cookie Utilities for CloudVisor Auth Service.

Sets authentication tokens as HttpOnly cookies instead of returning them
in JSON response bodies. This prevents XSS-based token theft.

Cookie Specification:
  - cv_access:  HttpOnly, Secure*, SameSite=Lax, Path=/, Max-Age=900 (15 min)
  - cv_refresh: HttpOnly, Secure*, SameSite=Lax, Path=/auth/refresh, Max-Age=2592000 (30 days)
  - cv_csrf:    NOT HttpOnly (JS-readable for double-submit), Secure*, SameSite=Lax, Path=/, Max-Age=900
  - cv_session: NOT HttpOnly (JS-readable session indicator), SameSite=Lax, Path=/, Max-Age=900

  * Secure=True only in production (HTTPS). In development (localhost HTTP), Secure=False.
"""

import os
import secrets

from fastapi.responses import Response


# ─── Constants ────────────────────────────────────────────────────────────────

COOKIE_ACCESS_NAME = "cv_access"
COOKIE_REFRESH_NAME = "cv_refresh"
COOKIE_CSRF_NAME = "cv_csrf"
COOKIE_SESSION_NAME = "cv_session"

# Durations
ACCESS_TOKEN_MAX_AGE = 900          # 15 minutes
REFRESH_TOKEN_MAX_AGE = 2_592_000   # 30 days
CSRF_TOKEN_MAX_AGE = 900            # 15 minutes (matches access token)

# Paths
REFRESH_COOKIE_PATH = "/auth/refresh"


def _is_production() -> bool:
    """Check if running in production (HTTPS required for Secure cookies)."""
    return os.environ.get("APP_ENVIRONMENT", "development").lower() == "production"


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


# ─── Set Cookies ──────────────────────────────────────────────────────────────

def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str | None = None,
) -> str:
    """
    Set authentication cookies on the response.

    Args:
        response: FastAPI Response object
        access_token: JWT access token
        refresh_token: JWT refresh token
        csrf_token: CSRF token (generated if not provided)

    Returns:
        The CSRF token that was set (for inclusion in response body if needed)
    """
    is_secure = _is_production()
    csrf = csrf_token or generate_csrf_token()

    # Access token — HttpOnly, sent on every request
    response.set_cookie(
        key=COOKIE_ACCESS_NAME,
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/",
        max_age=ACCESS_TOKEN_MAX_AGE,
    )

    # Refresh token — HttpOnly, only sent to /auth/refresh endpoint
    response.set_cookie(
        key=COOKIE_REFRESH_NAME,
        value=refresh_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=REFRESH_TOKEN_MAX_AGE,
    )

    # CSRF token — readable by JavaScript for double-submit pattern
    response.set_cookie(
        key=COOKIE_CSRF_NAME,
        value=csrf,
        httponly=False,
        secure=is_secure,
        samesite="lax",
        path="/",
        max_age=CSRF_TOKEN_MAX_AGE,
    )

    # Session indicator — readable by JavaScript to check if user is logged in
    # (without exposing the actual token)
    response.set_cookie(
        key=COOKIE_SESSION_NAME,
        value="1",
        httponly=False,
        secure=False,  # Allow on HTTP in dev
        samesite="lax",
        path="/",
        max_age=ACCESS_TOKEN_MAX_AGE,
    )

    return csrf


# ─── Clear Cookies ────────────────────────────────────────────────────────────

def clear_auth_cookies(response: Response) -> None:
    """
    Clear all authentication cookies (on logout or session invalidation).

    Sets Max-Age=0 to immediately expire the cookies in the browser.
    """
    response.delete_cookie(key=COOKIE_ACCESS_NAME, path="/")
    response.delete_cookie(key=COOKIE_REFRESH_NAME, path=REFRESH_COOKIE_PATH)
    response.delete_cookie(key=COOKIE_CSRF_NAME, path="/")
    response.delete_cookie(key=COOKIE_SESSION_NAME, path="/")


# ─── Read Cookies ─────────────────────────────────────────────────────────────

def get_access_token_from_cookie(request) -> str | None:
    """Extract the access token from the cv_access cookie."""
    return request.cookies.get(COOKIE_ACCESS_NAME)


def get_refresh_token_from_cookie(request) -> str | None:
    """Extract the refresh token from the cv_refresh cookie."""
    return request.cookies.get(COOKIE_REFRESH_NAME)


def get_csrf_token_from_cookie(request) -> str | None:
    """Extract the CSRF token from the cv_csrf cookie."""
    return request.cookies.get(COOKIE_CSRF_NAME)


# ─── CSRF Validation ──────────────────────────────────────────────────────────

def validate_csrf(request) -> bool:
    """
    Validate CSRF token using double-submit cookie pattern.

    The cv_csrf cookie value must match the X-CSRF-Token header.
    Returns True if valid, False if invalid.

    Skip validation if:
    - Request uses Authorization header (API key / programmatic access)
    - Request method is GET, HEAD, or OPTIONS (safe methods)
    """
    # Safe methods don't need CSRF protection
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True

    # Skip CSRF if using Authorization header (API keys, service-to-service)
    auth_header = request.headers.get("authorization")
    if auth_header:
        return True

    cookie_csrf = request.cookies.get(COOKIE_CSRF_NAME)
    header_csrf = request.headers.get("x-csrf-token")

    if not cookie_csrf or not header_csrf:
        return False

    return secrets.compare_digest(cookie_csrf, header_csrf)
