"""Repository for copilot query audit log."""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

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
        context_finding_id: str | None = None,
        context_asset_id: str | None = None,
        was_streamed: bool = False,
        session_id: str | None = None,
    ) -> CopilotQueryModel:
        """Create a new query log entry (append-only — never updated or deleted)."""
        query_log = CopilotQueryModel(
            organization_id=organization_id,
            user_id=user_id,
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
            session_id=session_id,
            created_at=datetime.utcnow(),
        )

        self.db.add(query_log)
        await self.db.commit()
        await self.db.refresh(query_log)

        logger.info(f"Created query log entry: {query_log.id}")
        return query_log

    async def get_org_history(
        self,
        organization_id: str,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get query history for an organization (all users).
        Optionally filter by user_id to show only the current user's queries.

        Returns full history including query, response, intent, model, latency, timestamps.
        """
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
                "query": q.query_text,
                "intent": q.intent,
                # Truncate response for history list — full response on detail endpoint
                "response_preview": (q.response_text or "")[:300] + ("..." if q.response_text and len(q.response_text) > 300 else ""),
                "response": q.response_text or "",
                "model_used": q.model_used,
                "processing_ms": q.processing_ms,
                "data_sources": q.data_sources or [],
                "was_streamed": q.was_streamed,
                "context_finding_id": q.context_finding_id,
                "context_asset_id": q.context_asset_id,
                "created_at": q.created_at.isoformat(),
            }
            for q in queries
        ]

    async def get_user_history(
        self, user_id: str, organization_id: str, limit: int = 50
    ) -> list[dict]:
        """Get query history for a specific user (backward-compatible wrapper)."""
        return await self.get_org_history(
            organization_id=organization_id,
            user_id=user_id,
            limit=limit,
        )

    async def get_by_id(self, query_id: str, organization_id: str) -> dict | None:
        """Get a single query by ID (tenant-scoped)."""
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
            "query": q.query_text,
            "intent": q.intent,
            "response": q.response_text or "",
            "citations": q.citations,
            "model_used": q.model_used,
            "processing_ms": q.processing_ms,
            "data_sources": q.data_sources or [],
            "was_streamed": q.was_streamed,
            "context_finding_id": q.context_finding_id,
            "context_asset_id": q.context_asset_id,
            "created_at": q.created_at.isoformat(),
        }
