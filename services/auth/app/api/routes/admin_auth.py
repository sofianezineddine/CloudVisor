"""Admin-specific auth endpoints - completely separate from tenant auth."""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...core.dependencies import get_db, get_redis, get_auth_settings_cached
from ...models.admin import AdminUserModel
from ...services.admin_auth_service import AdminAuthService
from ...schemas import TokenResponse

router = APIRouter(prefix="/admin/auth", tags=["admin", "auth"])


class AdminUserResponse:
    id: str
    email: str
    name: str
    role: str
    last_login_at: str | None


@router.post("/login", response_model=TokenResponse)
async def admin_login(
    data: dict,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    """Admin login - uses separate admins table and admin_sessions table."""
    auth_settings = get_auth_settings_cached()
    admin_auth_service = AdminAuthService(db, auth_settings, redis)

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        result = await admin_auth_service.login(
            email=email,
            password=password,
        )
        return TokenResponse(**result["tokens"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def admin_refresh_token(
    data: dict,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    """Refresh admin access token."""
    auth_settings = get_auth_settings_cached()
    admin_auth_service = AdminAuthService(db, auth_settings, redis)

    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token is required")

    try:
        result = await admin_auth_service.refresh_tokens(refresh_token)
        return TokenResponse(**result["tokens"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout")
async def admin_logout(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Admin logout."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    from ...services.utils import decode_token
    auth_settings = get_auth_settings_cached()
    admin_auth_service = AdminAuthService(db, auth_settings, redis)

    try:
        payload = decode_token(
            authorization.removeprefix("Bearer ").strip(),
            auth_settings.secret_key,
            public_key=auth_settings.effective_public_key,
        )
        if payload.get("scope") != "admin":
            raise HTTPException(status_code=401, detail="Not an admin token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    admin_id = payload.get("sub")
    session_id = payload.get("session_id")
    await admin_auth_service.logout(admin_id=admin_id, session_id=session_id)
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_admin_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current admin user profile."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    from ...services.utils import decode_token
    auth_settings = get_auth_settings_cached()

    try:
        payload = decode_token(
            authorization.removeprefix("Bearer ").strip(),
            auth_settings.secret_key,
            public_key=auth_settings.effective_public_key,
        )
        if payload.get("scope") != "admin":
            raise HTTPException(status_code=401, detail="Not an admin token")
        admin_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(AdminUserModel).where(AdminUserModel.id == admin_id)
    )
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    return {
        "id": admin.id,
        "email": admin.email,
        "name": admin.name,
        "role": admin.role,
        "last_login_at": admin.last_login_at,
    }
