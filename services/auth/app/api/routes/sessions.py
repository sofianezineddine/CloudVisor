"""API routes for sessions and API keys."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...core.dependencies import get_db, get_redis, get_auth_settings_cached
from ...schemas import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
    ApiKeyListResponse,
    SessionResponse,
    SessionListResponse,
)
from ...services import ApiKeyService
from ...models import UserModel, SessionModel
from ...services.utils import decode_token


router = APIRouter(prefix="/auth", tags=["sessions", "api-keys"])


def get_current_user_id(
    authorization: str | None = Header(default=None, alias="Authorization"),
    request: Request = None,
) -> str:
    """Extract user ID from authorization token or cv_access cookie (C-01 fix).

    Accepts auth via:
    1. Authorization: Bearer <token> header (programmatic access)
    2. cv_access HttpOnly cookie (browser session — C-01 fix)
    """
    from ...core.cookies import get_access_token_from_cookie

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    elif request:
        token = get_access_token_from_cookie(request)

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        auth_settings = get_auth_settings_cached()
        payload = decode_token(
            token,
            auth_settings.secret_key,
            public_key=auth_settings.effective_public_key,  # S-09 fix
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    authorization: str | None = Header(default=None, alias="Authorization"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """List active sessions."""
    user_id = get_current_user_id(authorization, request)

    result = await db.execute(
        select(SessionModel).where(
            SessionModel.user_id == user_id,
            SessionModel.is_active == True,
        )
    )
    sessions = result.scalars().all()

    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                device_info=s.device_info,
                ip_address=s.ip_address,
                last_active_at=s.last_active_at,
                created_at=s.created_at,
            )
            for s in sessions
        ]
    )


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke a specific session."""
    user_id = get_current_user_id(authorization, request)

    result = await db.execute(
        select(SessionModel).where(
            SessionModel.id == session_id,
            SessionModel.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    await db.commit()

    return {"message": "Session revoked"}


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    authorization: str | None = Header(default=None, alias="Authorization"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ApiKeyListResponse:
    """List API keys."""
    user_id = get_current_user_id(authorization, request)
    auth_settings = get_auth_settings_cached()

    api_key_service = ApiKeyService(db, auth_settings, redis)
    keys = await api_key_service.list_api_keys(user_id)

    return ApiKeyListResponse(keys=keys)


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ApiKeyCreatedResponse:
    """Create a new API key. Returns the key value only once — store it securely."""
    user_id = get_current_user_id(authorization, request)
    auth_settings = get_auth_settings_cached()

    api_key_service = ApiKeyService(db, auth_settings, redis)
    key = await api_key_service.create_api_key(
        user_id=user_id,
        name=data.name,
        scopes=data.scopes,
        expires_at=data.expires_at,
    )

    return ApiKeyCreatedResponse(**key)


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Revoke an API key."""
    user_id = get_current_user_id(authorization, request)
    auth_settings = get_auth_settings_cached()

    api_key_service = ApiKeyService(db, auth_settings, redis)
    success = await api_key_service.revoke_api_key(key_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"message": "API key revoked"}


@router.post("/api-keys/{key_id}/rotate", response_model=ApiKeyCreatedResponse)
async def rotate_api_key(
    key_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ApiKeyCreatedResponse:
    """Rotate an API key. Returns the new key value only once — store it securely."""
    user_id = get_current_user_id(authorization, request)
    auth_settings = get_auth_settings_cached()

    api_key_service = ApiKeyService(db, auth_settings, redis)
    key = await api_key_service.rotate_api_key(key_id, user_id)

    return ApiKeyCreatedResponse(**key)
