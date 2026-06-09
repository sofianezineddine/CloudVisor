"""API routes for authentication.

Security fixes applied:
- S-03: OAuth tokens no longer passed in URL fragment — use short-lived one-time code
- S-08: frontend_url no longer accepted from request body — read from server config
- S-09: decode_token now passes public_key for RS256 verification
- S-11: time.sleep() replaced with await asyncio.sleep()
- S-12: OAuth state is a cryptographically random nonce, verified on callback
- B-09: OAuth query string is properly URL-encoded
- B-08: GitHub email fetched only once
"""

import asyncio
import os
import secrets
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ...core.dependencies import get_db, get_redis, get_auth_settings_cached
from ...schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
)
from ...services import AuthService
from ...services.utils import decode_token


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("auth.routes")

# Read FRONTEND_URL from environment — never from request body (S-08 fix)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    """Register a new user and organization.

    Sets HttpOnly cookies so the frontend doesn't need to store tokens
    in localStorage (C-01 fix).
    """
    from ...services.rate_limiter import RateLimiter
    from ...core.cookies import set_auth_cookies
    ip = request.client.host if request.client else "unknown"
    limiter = RateLimiter(redis)
    if not await limiter.check_register_rate(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later.",
        )

    auth_settings = get_auth_settings_cached()
    auth_service = AuthService(db, auth_settings, redis)

    try:
        result = await auth_service.register(
            email=data.email,
            password=data.password,
            organization_name=data.organization_name,
            first_name=data.first_name,
            last_name=data.last_name,
        )
        tokens = result["tokens"]
        # Set HttpOnly cookies so frontend doesn't need localStorage token storage
        set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
        return TokenResponse(**tokens)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    """Login with email and password."""
    # Rate limiting: 10 attempts per minute per IP
    from ...services.rate_limiter import RateLimiter
    ip = request.client.host if request.client else "unknown"
    limiter = RateLimiter(redis)
    if not await limiter.check_login_rate(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again in a minute.",
        )

    # Account lockout: check if account is locked due to failed attempts
    if await limiter.is_account_locked(data.email):
        remaining = await limiter.get_lockout_remaining(data.email)
        minutes = (remaining or 900) // 60
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account temporarily locked due to too many failed attempts. Try again in {minutes} minutes.",
        )

    auth_settings = get_auth_settings_cached()
    auth_service = AuthService(db, auth_settings, redis)

    try:
        result = await auth_service.login(
            email=data.email,
            password=data.password,
            mfa_code=data.mfa_code,
            ip_address=ip,
            user_agent=request.headers.get("User-Agent"),
        )
        tokens = result["tokens"]

        # Successful login — clear any lockout state
        await limiter.clear_failed_logins(data.email)

        # Set HttpOnly cookies (primary auth mechanism — no localStorage needed)
        from ...core.cookies import set_auth_cookies
        set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])

        return TokenResponse(**tokens)
    except ValueError as e:
        # Failed login — record for lockout
        await limiter.record_failed_login(data.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    """Refresh access token. Issues a new refresh token and invalidates the old one."""
    auth_settings = get_auth_settings_cached()
    auth_service = AuthService(db, auth_settings, redis)

    # Read refresh token from cookie (fallback to request body for backward compat)
    from ...core.cookies import get_refresh_token_from_cookie, set_auth_cookies
    token = get_refresh_token_from_cookie(request) or data.refresh_token

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token provided")

    try:
        result = await auth_service.refresh_tokens(token)
        tokens = result["tokens"]

        # Set new HttpOnly cookies
        set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])

        return TokenResponse(**tokens)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Logout and invalidate session."""
    from ...core.cookies import get_access_token_from_cookie, clear_auth_cookies

    # Read token from header OR cookie
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    else:
        token = get_access_token_from_cookie(request)

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    auth_settings = get_auth_settings_cached()
    auth_service = AuthService(db, auth_settings, redis)
    try:
        payload = decode_token(
            token,
            auth_settings.secret_key,
            public_key=auth_settings.effective_public_key,
        )
    except Exception:
        # Even if token is invalid, clear cookies
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    session_id = payload.get("session_id")
    if not user_id:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid token")

    ip = request.client.host if request.client else None
    await auth_service.logout(user_id=user_id, session_id=session_id, ip_address=ip)

    # Clear all auth cookies
    clear_auth_cookies(response)

    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Request a password reset email.

    S-08 fix: frontend_url is read from server config, NOT from the request body.
    """
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    # Rate limit password reset requests
    from ...services.rate_limiter import RateLimiter
    limiter = RateLimiter(redis)
    if not await limiter.check_password_reset_rate(email):
        # Still return success to prevent enumeration
        return {"message": "If an account exists with that email, a password reset link has been sent"}

    auth_settings = get_auth_settings_cached()
    from ...services.password_reset import PasswordResetService

    svc = PasswordResetService(db, redis, auth_settings)
    raw_token = await svc.request_reset(email)

    if raw_token:
        # S-08 fix: use server-side FRONTEND_URL, never from request body
        await svc.send_reset_email(email, raw_token, FRONTEND_URL)

    # Always return success to prevent email enumeration
    return {"message": "If an account exists with that email, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    data: dict,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Reset password with token."""
    token = data.get("token")
    new_password = data.get("password")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and password are required")

    auth_settings = get_auth_settings_cached()
    from ...services.password_reset import PasswordResetService

    svc = PasswordResetService(db, redis, auth_settings)
    try:
        await svc.reset_password(token, new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Password reset successfully. You can now log in with your new password."}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get current user profile.

    Accepts auth via:
    1. Authorization: Bearer <token> header (programmatic access)
    2. cv_access HttpOnly cookie (browser session — C-01 fix)
    """
    from ...models import UserModel
    from ...services.rbac import RBACService
    from ...core.cookies import get_access_token_from_cookie
    from sqlalchemy import select

    # Extract token from Bearer header first, fall back to cv_access cookie
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    elif request:
        token = get_access_token_from_cookie(request)

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    auth_settings = get_auth_settings_cached()

    try:
        payload = decode_token(
            token,
            auth_settings.secret_key,
            public_key=auth_settings.effective_public_key,
        )
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch actual role from user_roles table (B-05 fix)
    rbac = RBACService(db, auth_settings)
    actual_role = await rbac.get_user_role(user_id)

    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        organization_id=user.organization_id,
        role=actual_role,  # B-05 fix: actual role, not hardcoded "Owner"
        mfa_enabled=user.mfa_enabled,
        provider=user.provider,
        created_at=user.created_at,
    )


class UpdateProfileRequest(BaseModel):
    """Request to update user profile."""
    first_name: str | None = None
    last_name: str | None = None


class ChangePasswordRequest(BaseModel):
    """Request to change password."""
    current_password: str
    new_password: str


@router.patch("/me")
async def update_current_user(
    data: UpdateProfileRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update current user profile (name only, email cannot be changed)."""
    from ...models import UserModel
    from sqlalchemy import select

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    auth_settings = get_auth_settings_cached()

    try:
        payload = decode_token(
            authorization.removeprefix("Bearer ").strip(),
            auth_settings.secret_key,
            public_key=auth_settings.effective_public_key,
        )
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name

    user.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Profile updated successfully"}


@router.post("/password")
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Change current user password.

    Spec §3.3: Force-expire all other active sessions after password change.
    """
    from ...models import UserModel
    from ...services import AuthService
    from sqlalchemy import select

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    auth_settings = get_auth_settings_cached()

    try:
        payload = decode_token(
            authorization.removeprefix("Bearer ").strip(),
            auth_settings.secret_key,
            public_key=auth_settings.effective_public_key,
        )
        user_id = payload.get("sub")
        current_session_id = payload.get("session_id")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.provider != "local":
        raise HTTPException(
            status_code=400,
            detail=f"Password is managed by your {user.provider.title()} account.",
        )

    auth_service = AuthService(db, auth_settings, redis)

    # Verify current password using async bcrypt (S-06 fix)
    if not await auth_service._check_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate new password policy
    auth_service._validate_password(data.new_password)

    # Update password using async bcrypt (S-06 fix)
    user.password_hash = await auth_service._hash_password(data.new_password)
    user.updated_at = datetime.utcnow()
    await db.commit()

    # Spec §3.3: Force-expire ALL other active sessions
    invalidated = await auth_service.invalidate_all_sessions(
        user_id=user_id,
        except_session_id=current_session_id,
    )

    return {
        "message": "Password changed successfully",
        "sessions_invalidated": invalidated,
    }


# ─────────────────────────────────────────────────────────────
# OAuth Endpoints (Google & GitHub)
# ─────────────────────────────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"


def _get_oauth_config(provider: str, auth_settings: Any) -> dict:
    """Get OAuth configuration for a provider."""
    if provider == "google":
        return {
            "auth_url": GOOGLE_AUTH_URL,
            "token_url": GOOGLE_TOKEN_URL,
            "userinfo_url": GOOGLE_USERINFO_URL,
            "client_id": auth_settings.oauth_google_client_id,
            "client_secret": getattr(auth_settings, "oauth_google_client_secret", ""),
            "scopes": "openid email profile",
            "redirect_uri": f"{FRONTEND_URL}/auth/callback/google",
        }
    elif provider == "github":
        return {
            "auth_url": GITHUB_AUTH_URL,
            "token_url": GITHUB_TOKEN_URL,
            "userinfo_url": GITHUB_USERINFO_URL,
            "client_id": auth_settings.oauth_github_client_id,
            "client_secret": getattr(auth_settings, "oauth_github_client_secret", ""),
            "scopes": "user:email",
            "redirect_uri": f"{FRONTEND_URL}/auth/callback/github",
        }
    raise ValueError(f"Unknown provider: {provider}")


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: str,
    redis=Depends(get_redis),
) -> RedirectResponse:
    """Redirect user to OAuth provider's authorization page.

    S-12 fix: state is a cryptographically random nonce stored in Redis.
    B-09 fix: query string is properly URL-encoded.
    """
    if provider not in ("google", "github"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    auth_settings = get_auth_settings_cached()

    if provider == "google" and not auth_settings.oauth_google_enabled:
        raise HTTPException(status_code=400, detail="Google OAuth is not enabled")
    if provider == "github" and not auth_settings.oauth_github_enabled:
        raise HTTPException(status_code=400, detail="GitHub OAuth is not enabled")

    config = _get_oauth_config(provider, auth_settings)

    # S-12 fix: generate a random state nonce and store it in Redis (10 min TTL)
    state = secrets.token_urlsafe(32)
    await redis.setex(f"oauth:state:{state}", 600, provider)

    params: dict[str, str] = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": config["scopes"],
        "state": state,
    }

    if provider == "google":
        params["prompt"] = "consent"

    # B-09 fix: use urlencode for proper percent-encoding
    query_string = urlencode(params)
    return RedirectResponse(url=f"{config['auth_url']}?{query_string}")


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> RedirectResponse:
    """Handle OAuth callback.

    S-03 fix: tokens are NOT passed in URL fragment. Instead, a short-lived
    one-time code is stored in Redis and the frontend exchanges it for tokens
    via POST /auth/oauth/exchange.
    S-12 fix: state nonce is verified against Redis before proceeding.
    S-11 fix: uses await asyncio.sleep() instead of time.sleep().
    B-08 fix: GitHub email fetched only once.
    """
    if provider not in ("google", "github"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    auth_settings = get_auth_settings_cached()
    config = _get_oauth_config(provider, auth_settings)

    # S-12 fix: verify state nonce
    if not state:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=missing_state")

    stored_provider = await redis.get(f"oauth:state:{state}")
    if not stored_provider or stored_provider != provider:
        logger.warning(f"OAuth state mismatch for provider={provider}, state={state[:8]}...")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=invalid_state")

    # Consume the state nonce (single-use)
    await redis.delete(f"oauth:state:{state}")

    if provider == "github" and not auth_settings.oauth_github_enabled:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=github_not_enabled")
    if provider == "google" and not auth_settings.oauth_google_enabled:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_not_enabled")

    # Exchange code for access token (with async retry — S-11 fix)
    token_response = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if provider == "google":
                    token_response = await client.post(
                        config["token_url"],
                        data={
                            "code": code,
                            "client_id": config["client_id"],
                            "client_secret": config["client_secret"],
                            "redirect_uri": config["redirect_uri"],
                            "grant_type": "authorization_code",
                        },
                    )
                else:  # github
                    token_response = await client.post(
                        config["token_url"],
                        headers={"Accept": "application/json"},
                        data={
                            "code": code,
                            "client_id": config["client_id"],
                            "client_secret": config["client_secret"],
                            "redirect_uri": config["redirect_uri"],
                        },
                    )

                if token_response.status_code == 200:
                    break

                if attempt < 2:
                    logger.warning(f"Token exchange failed (attempt {attempt+1}): {token_response.status_code}")
                    await asyncio.sleep(0.5 * (attempt + 1))  # S-11 fix: async sleep
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            logger.warning(f"Token exchange network error (attempt {attempt+1}): {e}")
            if attempt < 2:
                await asyncio.sleep(1.0 * (attempt + 1))

    if not token_response or token_response.status_code != 200:
        logger.error(f"Token exchange failed after retries")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=oauth_failed")

    access_token = token_response.json().get("access_token")

    # Fetch user info from provider (with async retry — S-11 fix)
    userinfo = None
    for attempt in range(3):
        async with httpx.AsyncClient(timeout=30.0) as client:
            if provider == "google":
                userinfo_response = await client.get(
                    config["userinfo_url"],
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            else:  # github
                userinfo_response = await client.get(
                    config["userinfo_url"],
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/json",
                        "User-Agent": "CloudVisor-Auth-Service",
                    },
                )

            if userinfo_response.status_code == 200:
                userinfo = userinfo_response.json()
                break

            if attempt < 2:
                logger.warning(f"Userinfo fetch failed (attempt {attempt+1}): {userinfo_response.status_code}")
                await asyncio.sleep(0.5 * (attempt + 1))  # S-11 fix

    if not userinfo:
        logger.error("Userinfo fetch failed after retries")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=userinfo_failed")

    # Extract user info
    if provider == "google":
        email = userinfo.get("email")
        first_name = userinfo.get("given_name", "")
        last_name = userinfo.get("family_name", "")
        organization_name = email.split("@")[1].split(".")[0].title() if email else "GoogleUser"
    else:  # github
        email = userinfo.get("email")

        # B-08 fix: fetch GitHub emails only once if not in profile
        if not email:
            async with httpx.AsyncClient() as client:
                emails_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/json",
                        "User-Agent": "CloudVisor-Auth-Service",
                    },
                )
                if emails_response.status_code == 200:
                    emails_list = emails_response.json()
                    primary = next(
                        (e for e in emails_list if e.get("primary") and e.get("verified")),
                        next((e for e in emails_list if e.get("verified")), None),
                    )
                    email = primary.get("email") if primary else None

        name_parts = (userinfo.get("name") or "").split(" ", 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        organization_name = userinfo.get("login", "GitHubUser")

    if not email:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_email")

    auth_service = AuthService(db, auth_settings, redis)

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            result = await auth_service.oauth_login_or_register(
                email=email,
                provider=provider,
                provider_id=str(userinfo.get("id", email)),
                first_name=first_name,
                last_name=last_name,
                organization_name=organization_name,
            )
            tokens = result["tokens"]

            # S-03 fix: store tokens under a short-lived one-time code in Redis
            # The frontend exchanges this code for tokens via POST /auth/oauth/exchange
            exchange_code = secrets.token_urlsafe(32)
            import json
            await redis.setex(
                f"oauth:exchange:{exchange_code}",
                120,  # 2 minute TTL
                json.dumps(tokens),
            )

            redirect_url = f"{FRONTEND_URL}/auth/callback/success?code={exchange_code}"
            return RedirectResponse(url=redirect_url)

        except ValueError as e:
            logger.warning(f"OAuth login rejected for {email}: {e}")
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=oauth_failed")

        except Exception as e:
            last_error = e
            logger.error(f"OAuth login attempt {attempt + 1} failed for {email}: {type(e).__name__}: {e}")
            if attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))  # S-11 fix
                try:
                    await db.rollback()
                except Exception:
                    pass

    logger.error(f"OAuth login failed after 3 attempts for {email}: {last_error}")
    return RedirectResponse(url=f"{FRONTEND_URL}/login?error=oauth_failed")


@router.post("/oauth/exchange", response_model=TokenResponse)
async def oauth_exchange(
    data: dict,
    response: Response,
    redis=Depends(get_redis),
) -> TokenResponse:
    """Exchange a one-time OAuth code for JWT tokens (S-03 fix).

    The frontend calls this endpoint after the OAuth callback redirects with ?code=...
    This keeps tokens out of URLs, browser history, and server logs.
    """
    code = data.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Exchange code is required")

    import json
    tokens_raw = await redis.get(f"oauth:exchange:{code}")
    if not tokens_raw:
        raise HTTPException(status_code=400, detail="Invalid or expired exchange code")

    # Consume the code (single-use)
    await redis.delete(f"oauth:exchange:{code}")

    try:
        tokens = json.loads(tokens_raw)
    except (ValueError, TypeError):
        raise HTTPException(status_code=500, detail="Token exchange failed")

    # Set HttpOnly cookies
    from ...core.cookies import set_auth_cookies
    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])

    return TokenResponse(**tokens)
