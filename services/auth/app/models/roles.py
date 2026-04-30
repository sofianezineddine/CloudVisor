"""Custom roles and resource-level scoping models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .auth import Base


class RoleModel(Base):
    """Custom role definition (enterprise tier)."""

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_roles_org_name"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions or [],
            "is_builtin": self.is_builtin,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserRoleModel(Base):
    """Maps users to roles with optional resource-level scoping."""

    __tablename__ = "user_roles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False, index=True
    )
    role_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Resource-level scoping: restrict this role to specific cloud accounts or regions
    # e.g. {"account_ids": ["acc-123"], "regions": ["us-east-1"]}
    scope: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "role_name", "organization_id", name="uq_user_role_org"),
    )
