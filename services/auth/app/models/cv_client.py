"""CV client model for first-time enterprise data."""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from .auth import Base


class CvClientModel(Base):
    __tablename__ = "cv_clients"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=True
    )
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
