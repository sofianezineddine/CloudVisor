"""Repository for copilot query audit log."""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, distinct

from ..models import CopilotQueryModel

logger = logging.getLogger(__name__)


class QueryLogRepository:
    """Repository for copilot query audit log operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        organization_id: str,
        user_id: str,
        query_text: str,
        intent: str | None,
        response_text: str | None,
        citations: dict | None,
        data_sources: list[str] | None,
        processing_ms: int | None,
        model_used: str,
        session_id: str | None = None,
        context_finding_id: str | None = None,
        context_asset_id: str | None = None,
        was_streamed: bool = False,
    ) -> CopilotQueryModel:
        """Create a new query log entry (append-only — never updated or deleted)."""
        import uuid as _uuid

        # If no session_id provided, generate a new one (new conversation)
        if not session_id:
            session_id = str(_uuid.uuid4())

        # Session title = first 80 chars of the first message in this session
        session_title = query_text[:80] + ("..." if len(query_text) > 80 else "")

        query_log = CopilotQueryModel(
            organization_id=organization_id,
            user_id=user_id,
            session_id=session_id,
            session_title=session_title,
            query_text=query_text,
            intent=intent,
            response_text=response_text,
            citations=citations,
            data_sources=data_sources,
            processing_ms=processing_ms,
            model_used=model_used,
            context_finding_id=context_finding_id,
            context_asset_id=context_asset_id,
            was_streamed=was_streamed,
            created_at=datetime.utcnow(),
        )

        self.db.add(query_log)
        await self.db.commit()
        await self.db.refresh(query_log)

        logger.info(f"Created query log entry: {query_log.id} (session: {session_id})")
        return query_log

    async def get_sessions(
        self,
        organization_id: str,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get chat sessions for an org — one entry per session_id.
        Each session shows: session_id, title (first message), message count,
        last message time, last intent.
        """
        # Subquery: get latest message per session
        stmt = (
            select(
                CopilotQueryModel.session_id,
                CopilotQueryModel.session_title,
                func.count(CopilotQueryModel.id).label("message_count"),
                func.max(CopilotQueryModel.created_at).label("last_message_at"),
                func.min(CopilotQueryModel.created_at).label("first_message_at"),
            )
            .where(CopilotQueryModel.organization_id == organization_id)
        )

        if user_id:
            stmt = stmt.where(CopilotQueryModel.user_id == user_id)

        stmt = (
            stmt
            .group_by(CopilotQueryModel.session_id, CopilotQueryModel.session_title)
            .order_by(desc(func.max(CopilotQueryModel.created_at)))
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        sessions = []
        for row in rows:
            # Get the last intent for this session
            last_msg_stmt = (
                select(CopilotQueryModel.intent)
                .where(
                    CopilotQueryModel.session_id == row.session_id,
                    CopilotQueryModel.organization_id == organization_id,
                )
                .order_by(desc(CopilotQueryModel.created_at))
                .limit(1)
            )
            last_msg_result = await self.db.execute(last_msg_stmt)
            last_intent = last_msg_result.scalar_one_or_none()

            sessions.append({
                "session_id": row.session_id,
                "title": row.session_title or "Untitled conversation",
                "message_count": row.message_count,
                "last_message_at": row.last_message_at.isoformat() if row.last_message_at else None,
                "first_message_at": row.first_message_at.isoformat() if row.first_message_at else None,
                "last_intent": last_intent,
            })

        return sessions

    async def get_session_messages(
        self,
        session_id: str,
        organization_id: str,
    ) -> list[dict]:
        """Get all messages in a session, ordered by time."""
        stmt = (
            select(CopilotQueryModel)
            .where(
                CopilotQueryModel.session_id == session_id,
                CopilotQueryModel.organization_id == organization_id,
            )
            .order_by(CopilotQueryModel.created_at)
        )

        result = await self.db.execute(stmt)
        queries = result.scalars().all()

        messages = []
        for q in queries:
            # Each DB row = one user message + one assistant response
            messages.append({
                "id": q.id,
                "role": "user",
                "content": q.query_text,
                "created_at": q.created_at.isoformat(),
            })
            if q.response_text:
                messages.append({
                    "id": f"{q.id}-response",
                    "role": "assistant",
                    "content": q.response_text,
                    "intent": q.intent,
                    "model_used": q.model_used,
                    "processing_ms": q.processing_ms,
                    "data_sources": q.data_sources or [],
                    "created_at": q.created_at.isoformat(),
                })

        return messages

    # ── Backward-compatible methods ────────────────────────────────────────────

    async def get_org_history(
        self,
        organization_id: str,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get individual query history (backward-compatible)."""
        stmt = (
            select(CopilotQueryModel)
            .where(CopilotQueryModel.organization_id == organization_id)
        )
        if user_id:
            stmt = stmt.where(CopilotQueryModel.user_id == user_id)
        stmt = stmt.order_by(desc(CopilotQueryModel.created_at)).limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        queries = result.scalars().all()

        return [
            {
                "id": q.id,
                "session_id": q.session_id,
                "query": q.query_text,
                "intent": q.intent,
                "response_preview": (q.response_text or "")[:300] + ("..." if q.response_text and len(q.response_text or "") > 300 else ""),
                "response": q.response_text or "",
                "model_used": q.model_used,
                "processing_ms": q.processing_ms,
                "data_sources": q.data_sources or [],
                "was_streamed": q.was_streamed,
                "created_at": q.created_at.isoformat(),
            }
            for q in queries
        ]

    async def get_user_history(
        self, user_id: str, organization_id: str, limit: int = 50
    ) -> list[dict]:
        return await self.get_org_history(organization_id=organization_id, user_id=user_id, limit=limit)

    async def get_by_id(self, query_id: str, organization_id: str) -> dict | None:
        result = await self.db.execute(
            select(CopilotQueryModel).where(
                CopilotQueryModel.id == query_id,
                CopilotQueryModel.organization_id == organization_id,
            )
        )
        q = result.scalar_one_or_none()
        if not q:
            return None
        return {
            "id": q.id,
            "session_id": q.session_id,
            "query": q.query_text,
            "intent": q.intent,
            "response": q.response_text or "",
            "citations": q.citations,
            "model_used": q.model_used,
            "processing_ms": q.processing_ms,
            "data_sources": q.data_sources or [],
            "was_streamed": q.was_streamed,
            "created_at": q.created_at.isoformat(),
        }
