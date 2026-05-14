"""User repository — all user-related DB queries."""

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserModel


class UserRepository:
    """Database access layer for users."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, user_id: str) -> UserModel | None:
        """Get user by ID."""
        return await self._db.get(UserModel, user_id)

    async def get_by_email(self, email: str) -> UserModel | None:
        """Get user by email address."""
        result = await self._db.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_email_and_org(self, email: str, organization_id: str) -> UserModel | None:
        """Get user by email within a specific organization."""
        result = await self._db.execute(
            select(UserModel).where(
                UserModel.email == email,
                UserModel.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: Any) -> UserModel:
        """Create a new user."""
        user = UserModel(**kwargs)
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)
        return user

    async def update(self, user_id: str, **kwargs: Any) -> UserModel | None:
        """Update user fields."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            setattr(user, key, value)
        user.updated_at = datetime.utcnow()
        await self._db.commit()
        await self._db.refresh(user)
        return user

    async def increment_failed_logins(self, user_id: str) -> int:
        """Increment failed login counter and return new count."""
        user = await self.get_by_id(user_id)
        if not user:
            return 0
        user.failed_login_attempts += 1
        user.updated_at = datetime.utcnow()
        await self._db.commit()
        return user.failed_login_attempts

    async def reset_failed_logins(self, user_id: str) -> None:
        """Reset failed login counter after successful login."""
        await self._db.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(failed_login_attempts=0, updated_at=datetime.utcnow())
        )
        await self._db.commit()

    async def list_by_org(self, organization_id: str) -> list[UserModel]:
        """List all users in an organization."""
        result = await self._db.execute(
            select(UserModel).where(UserModel.organization_id == organization_id)
        )
        return list(result.scalars().all())
