"""API routes for copilot chat sessions."""

import logging
import re
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_db
from ..repositories.chat_session_repo import ChatSessionRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/copilot/sessions", tags=["copilot-sessions"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


# Request schemas
class CreateSessionRequest(BaseModel):
    title: str
    description: str | None = None


class UpdateSessionRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    is_active: bool | None = None


def _extract_org_and_user(
    authorization: str | None,
    x_org_id: str | None,
) -> tuple[str, str]:
    """Extract organization and user IDs from headers."""
    import uuid
    
    extracted_org_id: str | None = None
    extracted_user_id: str | None = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token != "dev-token":
            try:
                import base64
                import json as _json

                payload_b64 = token.split(".")[1]
                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
                extracted_org_id = payload.get("organization_id") or payload.get("org_id")
                extracted_user_id = payload.get("sub") or payload.get("user_id")
            except Exception as jwt_err:
                logger.warning(f"Failed to decode JWT payload: {jwt_err}")

    org_id = extracted_org_id if extracted_org_id and _UUID_RE.match(extracted_org_id) else x_org_id
    # For dev-token, use a consistent dev user ID
    if not extracted_user_id or not _UUID_RE.match(extracted_user_id):
        user_id = "550e8400-e29b-41d4-a716-446655440001"  # Consistent dev user ID
    else:
        user_id = extracted_user_id

    if not org_id or not _UUID_RE.match(org_id):
        raise HTTPException(status_code=401, detail="Cannot determine organization.")

    return org_id, user_id


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
    description="Start a new conversation session",
)
async def create_session(
    request: CreateSessionRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new chat session."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    org_id, user_id = _extract_org_and_user(authorization, x_org_id)

    session_repo = ChatSessionRepository(db)
    session = await session_repo.create(
        organization_id=org_id,
        user_id=user_id,
        title=request.title,
        description=request.description,
    )

    return {
        "id": session.id,
        "title": session.title,
        "description": session.description,
        "message_count": session.message_count,
        "is_active": session.is_active,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


@router.get(
    "",
    summary="List chat sessions",
    description="Get all chat sessions for the current user",
)
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    active_only: bool = True,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all chat sessions for the current user."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    org_id, user_id = _extract_org_and_user(authorization, x_org_id)

    session_repo = ChatSessionRepository(db)
    sessions = await session_repo.get_user_sessions(
        user_id=user_id,
        organization_id=org_id,
        limit=limit,
        offset=offset,
        active_only=active_only,
    )

    return {
        "sessions": sessions,
        "total": len(sessions),
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{session_id}",
    summary="Get session details",
    description="Get a specific chat session with all messages",
)
async def get_session(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a specific chat session with all messages."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    org_id, user_id = _extract_org_and_user(authorization, x_org_id)

    session_repo = ChatSessionRepository(db)
    session = await session_repo.get_by_id(session_id, org_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify user owns this session
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    messages = await session_repo.get_session_messages(
        session_id=session_id,
        organization_id=org_id,
        limit=limit,
        offset=offset,
    )

    return {
        "id": session.id,
        "title": session.title,
        "description": session.description,
        "message_count": session.message_count,
        "is_active": session.is_active,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "last_message_at": session.last_message_at.isoformat() if session.last_message_at else None,
        "messages": messages,
    }


@router.patch(
    "/{session_id}",
    summary="Update session",
    description="Update session title or description",
)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a chat session."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    org_id, user_id = _extract_org_and_user(authorization, x_org_id)

    session_repo = ChatSessionRepository(db)
    session = await session_repo.get_by_id(session_id, org_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify user owns this session
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    updated_session = await session_repo.update_session(
        session_id=session_id,
        organization_id=org_id,
        title=request.title,
        description=request.description,
        is_active=request.is_active,
    )

    return {
        "id": updated_session.id,
        "title": updated_session.title,
        "description": updated_session.description,
        "is_active": updated_session.is_active,
        "updated_at": updated_session.updated_at.isoformat(),
    }


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete session",
    description="Delete (soft delete) a chat session",
)
async def delete_session(
    session_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a chat session."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    org_id, user_id = _extract_org_and_user(authorization, x_org_id)

    session_repo = ChatSessionRepository(db)
    session = await session_repo.get_by_id(session_id, org_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify user owns this session
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    await session_repo.delete_session(session_id, org_id)
