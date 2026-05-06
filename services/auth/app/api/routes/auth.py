"""API routes for authentication."""

from fastapi import APIRouter, Depends, Header, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import httpx
import time
import logging

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


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    """Register a new user and organization."""
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
        return TokenResponse(**result["tokens"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
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

    auth_settings = get_auth_settings_cached()
    auth_service = AuthService(db, auth_settings, redis)

    try:
        result = await auth_service.login(
            email=data.email,
            password=data.password,
            mfa_code=data.mfa_code,
            ip_address=ip,
        )
        return TokenResponse(**result["tokens"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    """Refresh access token."""
    auth_settings = get_auth_settings_cached()
    auth_service = AuthService(db, auth_settings, redis)

    try:
        result = await auth_service.refresh_tokens(data.refresh_token)
        return TokenResponse(**result["tokens"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout")
async def logout(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Logout and invalidate session."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    auth_settings = get_auth_settings_cached()
    auth_service = AuthService(db, auth_settings, redis)
    try:
        payload = decode_token(
            token,
            auth_settings.secret_key,
            public_key=auth_settings.effective_public_key,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    session_id = payload.get("session_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    await auth_service.logout(user_id=user_id, session_id=session_id)
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(
    data: dict,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Request a password reset email."""
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    auth_settings = get_auth_settings_cached()
    from ...services.password_reset import PasswordResetService

    svc = PasswordResetService(db, redis, auth_settings)
    raw_token = await svc.request_reset(email)

    if raw_token:
        frontend_url = data.get("frontend_url", "http://localhost:3000")
        await svc.send_reset_email(email, raw_token, frontend_url)

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
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get current user profile."""
    from ...models import UserModel
    from ...services.utils import decode_token
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    auth_settings = get_auth_settings_cached()

    try:
        payload = decode_token(
            authorization.replace("Bearer ", ""),
            auth_settings.secret_key,
            public_key=auth_settings.effective_public_key,
        )
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Load user
    result = await db.execute(
        select(UserModel)
        .where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        organization_id=user.organization_id,
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
    from ...services.utils import decode_token
    from sqlalchemy import select
    from datetime import datetime

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    auth_settings = get_auth_settings_cached()

    try:
        payload = decode_token(
            authorization.replace("Bearer ", ""),
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

    # Update only name fields (email cannot be changed)
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
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Change current user password.

    Spec §3.3: Force-expire all other active sessions after password change.
    """
    from ...models import UserModel
    from ...services import AuthService
    from ...services.utils import decode_token
    from sqlalchemy import select
    from datetime import datetime
    import bcrypt

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    auth_settings = get_auth_settings_cached()

    try:
        payload = decode_token(
            authorization.replace("Bearer ", ""),
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

    # Block OAuth users from changing password via platform
    if user.provider != "local":
        raise HTTPException(
            status_code=400,
            detail=f"Password is managed by your {user.provider.title()} account. Please change it in your {user.provider.title()} account settings."
        )

    # Verify current password
    if not bcrypt.checkpw(data.current_password.encode("utf-8"), user.password_hash.encode("utf-8")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate new password policy
    auth_service = AuthService(db, auth_settings, redis)
    auth_service._validate_password(data.new_password)

    # Update password
    user.password_hash = auth_service._hash_password(data.new_password)
    user.updated_at = datetime.utcnow()
    await db.commit()

    # ── Spec §3.3: Force-expire ALL other active sessions ────────────────────
    invalidated = await auth_service.invalidate_all_sessions(
        user_id=user_id,
        except_session_id=current_session_id,  # keep the current session alive
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

FRONTEND_URL = "http://localhost:3000"


def _get_oauth_config(provider: str, auth_settings) -> dict:
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
):
    """Redirect user to OAuth provider's authorization page."""
    if provider not in ("google", "github"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    auth_settings = get_auth_settings_cached()

    if provider == "google" and not auth_settings.oauth_google_enabled:
        raise HTTPException(status_code=400, detail="Google OAuth is not enabled")
    if provider == "github" and not auth_settings.oauth_github_enabled:
        raise HTTPException(status_code=400, detail="GitHub OAuth is not enabled")

    config = _get_oauth_config(provider, auth_settings)

    # Build authorization URL
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": config["scopes"],
        "state": provider,
    }

    if provider == "google":
        params["prompt"] = "consent"

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{config['auth_url']}?{query_string}")


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Handle OAuth callback, create/login user, and redirect to frontend."""
    if provider not in ("google", "github"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    auth_settings = get_auth_settings_cached()
    config = _get_oauth_config(provider, auth_settings)
    logger = logging.getLogger("auth.oauth")

    # Check if provider is enabled
    if provider == "github" and not auth_settings.oauth_github_enabled:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=github_not_enabled")
    if provider == "google" and not auth_settings.oauth_google_enabled:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_not_enabled")

    # Exchange code for access token (with retry)
    token_response = None
    for attempt in range(3):
        async with httpx.AsyncClient() as client:
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
                time.sleep(0.5 * (attempt + 1))

    if token_response.status_code != 200:
        error_detail = token_response.text
        logger.error(f"Token exchange failed: {error_detail}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=oauth_failed")

    access_token = token_response.json().get("access_token")

    # Fetch user info from provider (with retry)
    userinfo = None
    for attempt in range(3):
        async with httpx.AsyncClient() as client:
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
                time.sleep(0.5 * (attempt + 1))

    if not userinfo:
        error_detail = userinfo_response.text if 'userinfo_response' in locals() else "No response"
        logger.error(f"Userinfo fetch failed: {error_detail}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=userinfo_failed")

    # For GitHub, fetch emails if not in profile
    github_emails = None
    if provider == "github" and not userinfo.get("email"):
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
                primary = next((e for e in emails_list if e.get("primary") and e.get("verified")), None)
                if primary:
                    github_emails = primary.get("email")

    # Extract user info
    if provider == "google":
        email = userinfo.get("email")
        first_name = userinfo.get("given_name", "")
        last_name = userinfo.get("family_name", "")
        organization_name = email.split("@")[1].split(".")[0].title() if email else "GoogleUser"
    else:  # github
        email = userinfo.get("email")
        
        # If email is not in userinfo, fetch /user/emails endpoint
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
                    # Get primary verified email
                    primary = next((e for e in emails_list if e.get("primary") and e.get("verified")), None)
                    if not primary:
                        # Fallback to first verified email
                        primary = next((e for e in emails_list if e.get("verified")), None)
                    email = primary.get("email") if primary else None
        
        first_name = userinfo.get("name", "").split(" ")[0] if userinfo.get("name") else ""
        last_name = " ".join(userinfo.get("name", "").split(" ")[1:]) if userinfo.get("name") else ""
        organization_name = userinfo.get("login", "GitHubUser")

    if not email:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_email")

    # Check if user exists, if not create them
    auth_service = AuthService(db, auth_settings, redis)

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

        # Redirect to frontend with tokens in URL hash (for SPA to pick up)
        redirect_url = (
            f"{FRONTEND_URL}/auth/callback/success"
            f"#access_token={tokens['access_token']}"
            f"&refresh_token={tokens['refresh_token']}"
            f"&token_type={tokens['token_type']}"
        )
        return RedirectResponse(url=redirect_url)

    except ValueError as e:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error={str(e)}")
