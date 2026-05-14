"""Session repository — all session-related DB queries."""

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import SessionModel


class SessionRepository:
    """Database access layer for user sessions."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, session_id: str) -> SessionModel | None:
        """Get session by ID."""
        return await self._db.get(SessionModel, session_id)

    async def get_active_by_user(self, user_id: str) -> list[SessionModel]:
        """Get all active sessions for a user."""
        result = await self._db.execute(
            select(SessionModel).where(
                SessionModel.user_id == user_id,
                SessionModel.is_active == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> SessionModel:
        """Create a new session."""
        session = SessionModel(**kwargs)
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def deactivate(self, session_id: str) -> bool:
        """Deactivate a specific session."""
        session = await self.get_by_id(session_id)
        if not session:
            return False
        session.is_active = False
        await self._db.commit()
        return True

    async def deactivate_all_for_user(
        self,
        user_id: str,
        except_session_id: str | None = None,
    ) -> int:
        """Deactivate all active sessions for a user. Returns count deactivated."""
        stmt = (
            update(SessionModel)
            .where(
                SessionModel.user_id == user_id,
                SessionModel.is_active == True,  # noqa: E712
            )
        )
        if except_session_id:
            stmt = stmt.where(SessionModel.id != except_session_id)
        stmt = stmt.values(is_active=False)
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount or 0

    async def update_last_active(self, session_id: str) -> None:
        """Update session last_active_at timestamp (M-11 fix)."""
        await self._db.execute(
            update(SessionModel)
            .where(SessionModel.id == session_id, SessionModel.is_active == True)  # noqa: E712
            .values(last_active_at=datetime.utcnow())
        )
        await self._db.commit()

    async def expire_inactive(self, cutoff: datetime) -> int:
        """Expire sessions that have passed their expiry time. Returns count expired."""
        stmt = (
            update(SessionModel)
            .where(
                SessionModel.is_active == True,  # noqa: E712
                SessionModel.expires_at < cutoff,
            )
            .values(is_active=False)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount or 0
