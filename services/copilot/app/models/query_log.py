"""SQLAlchemy ORM models for Copilot query audit log."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, Integer, String, Text, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class CopilotQueryModel(Base):
    """
    Copilot query audit log — append-only, never updated or deleted.
    
    Each row = one user message + one assistant response.
    Rows are grouped into conversations via session_id.
    A session = one chat conversation (multiple back-and-forth messages).
    """

    __tablename__ = "copilot_queries"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)

    # Session grouping — all messages in one chat share the same session_id
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True,
        default=lambda: str(uuid.uuid4())
    )
    # Title of the session — set from the first message in the session
    session_title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Query details
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Response details
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Metadata
    data_sources: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    processing_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_used: Mapped[str] = mapped_column(
        String(100), nullable=False, default="direct"
    )

    # Context
    context_finding_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    context_asset_id: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Streaming
    was_streamed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    __table_args__ = (
        CheckConstraint(
            "intent IN ('POSTURE', 'FINDING', 'COMPLIANCE', 'REMEDIATION', 'THREAT', 'DRIFT', 'GENERAL')",
            name="valid_intent",
        ),
        Index("idx_copilot_queries_session", "session_id"),
        Index("idx_copilot_queries_org_session", "organization_id", "session_id"),
    )
