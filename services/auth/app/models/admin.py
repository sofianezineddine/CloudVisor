"""Admin-specific models and auth.

Security note: The default admin password is read from the environment variable
ADMIN_DEFAULT_PASSWORD. It is never hardcoded in source code (S-05 fix).
"""

import os
import uuid
from datetime import datetime
from typing import Any

import bcrypt
from sqlalchemy import Boolean, DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class AdminBase(DeclarativeBase):
    pass


class AdminUserModel(AdminBase):
    """Platform admin user - separate from tenant users."""

    __tablename__ = "admins"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="super_admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # Q-07 fix


class AdminSessionModel(AdminBase):
    """Admin sessions - separate from tenant sessions."""

    __tablename__ = "admin_sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    admin_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    device_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


async def create_admin_tables(engine: Any) -> None:
    """Create admin-specific tables."""
    async with engine.begin() as conn:
        await conn.run_sync(AdminBase.metadata.create_all)


async def seed_default_admin(engine: Any) -> None:
    """Create default super admin if not exists.

    S-05 fix: Password is read from ADMIN_DEFAULT_PASSWORD env var.
    If not set, a random password is generated and printed ONCE to stdout.
    The password is never hardcoded in source code.
    """
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id FROM admins WHERE email = 'admin@cloudvisor.io'")
        )
        existing = result.scalar_one_or_none()

        if not existing:
            from datetime import datetime as dt

            # Read password from environment — never hardcode (S-05 fix)
            default_password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "")
            if not default_password:
                import secrets as _secrets
                default_password = _secrets.token_urlsafe(24)
                print(  # noqa: T201
                    f"\n⚠️  ADMIN_DEFAULT_PASSWORD not set. "
                    f"Generated one-time admin password: {default_password}\n"
                    f"   Store this securely — it will not be shown again.\n"
                )

            admin_id = str(uuid.uuid4())
            password_hash = bcrypt.hashpw(
                default_password.encode("utf-8"), bcrypt.gensalt(rounds=12)
            ).decode("utf-8")

            now = dt.utcnow()
            await conn.execute(
                text("""
                    INSERT INTO admins (id, email, password_hash, name, role, is_active, created_at, updated_at)
                    VALUES (:id, :email, :password_hash, :name, :role, :is_active, :created_at, :updated_at)
                """),
                {
                    "id": admin_id,
                    "email": "admin@cloudvisor.io",
                    "password_hash": password_hash,
                    "name": "Super Admin",
                    "role": "super_admin",
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            await conn.commit()
            print("✅ Default admin user created: admin@cloudvisor.io")  # noqa: T201
