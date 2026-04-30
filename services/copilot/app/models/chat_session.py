"""SQLAlchemy ORM models for Copilot chat sessions."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .query_log import Base


class ChatSessionModel(Base):
    """Chat session model - groups related queries into conversations."""

    __tablename__ = "copilot_chat_sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)

    # Session metadata
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Session state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
