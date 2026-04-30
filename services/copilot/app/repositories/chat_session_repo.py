"""Repository for copilot chat sessions."""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update

from ..models.chat_session import ChatSessionModel
from ..models.query_log import CopilotQueryModel

logger = logging.getLogger(__name__)


class ChatSessionRepository:
    """Repository for chat session operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        organization_id: str,
        user_id: str,
        title: str,
        description: str | None = None,
    ) -> ChatSessionModel:
        """Create a new chat session."""
        session = ChatSessionModel(
            organization_id=organization_id,
            user_id=user_id,
            title=title,
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.info(f"Created chat session: {session.id}")
        return session

    async def get_by_id(self, session_id: str, organization_id: str) -> ChatSessionModel | None:
        """Get a chat session by ID (tenant-scoped)."""
        result = await self.db.execute(
            select(ChatSessionModel).where(
                ChatSessionModel.id == session_id,
                ChatSessionModel.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self,
        user_id: str,
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True,
    ) -> list[dict]:
        """Get all chat sessions for a user."""
        stmt = (
            select(ChatSessionModel)
            .where(
                ChatSessionModel.organization_id == organization_id,
                ChatSessionModel.user_id == user_id,
            )
        )

        if active_only:
            stmt = stmt.where(ChatSessionModel.is_active == True)

        stmt = stmt.order_by(desc(ChatSessionModel.last_message_at)).limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "message_count": s.message_count,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
            }
            for s in sessions
        ]

    async def get_session_messages(
        self,
        session_id: str,
        organization_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get all messages (queries) in a session."""
        result = await self.db.execute(
            select(CopilotQueryModel)
            .where(
                CopilotQueryModel.session_id == session_id,
                CopilotQueryModel.organization_id == organization_id,
            )
            .order_by(CopilotQueryModel.created_at)
            .limit(limit)
            .offset(offset)
        )
        queries = result.scalars().all()

        return [
            {
                "id": q.id,
                "query": q.query_text,
                "response": q.response_text or "",
                "intent": q.intent,
                "model_used": q.model_used,
                "processing_ms": q.processing_ms,
                "data_sources": q.data_sources or [],
                "was_streamed": q.was_streamed,
                "created_at": q.created_at.isoformat(),
            }
            for q in queries
        ]

    async def update_session(
        self,
        session_id: str,
        organization_id: str,
        title: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> ChatSessionModel | None:
        """Update a chat session."""
        session = await self.get_by_id(session_id, organization_id)
        if not session:
            return None

        if title is not None:
            session.title = title
        if description is not None:
            session.description = description
        if is_active is not None:
            session.is_active = is_active

        session.updated_at = datetime.utcnow()

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.info(f"Updated chat session: {session_id}")
        return session

    async def increment_message_count(
        self,
        session_id: str,
        organization_id: str,
    ) -> None:
        """Increment message count and update last_message_at."""
        await self.db.execute(
            update(ChatSessionModel)
            .where(
                ChatSessionModel.id == session_id,
                ChatSessionModel.organization_id == organization_id,
            )
            .values(
                message_count=ChatSessionModel.message_count + 1,
                last_message_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.commit()

    async def delete_session(
        self,
        session_id: str,
        organization_id: str,
    ) -> bool:
        """Soft delete a chat session (mark as inactive)."""
        session = await self.get_by_id(session_id, organization_id)
        if not session:
            return False

        session.is_active = False
        session.updated_at = datetime.utcnow()

        self.db.add(session)
        await self.db.commit()

        logger.info(f"Deleted chat session: {session_id}")
        return True
