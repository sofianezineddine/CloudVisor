"""API key management service."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ApiKeyModel


class ApiKeyService:
    """Service for managing API keys."""

    def __init__(self, db: AsyncSession, settings: Any, redis_client: Any = None):
        self._db = db
        self._settings = settings
        self._redis = redis_client

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Create a new API key."""
        key_value = (
            f"{self._settings.api_key_prefix}{secrets.token_urlsafe(self._settings.api_key_length)}"
        )
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()

        api_key = ApiKeyModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            scopes=scopes or ["read"],
            expires_at=expires_at,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self._db.add(api_key)
        await self._db.commit()
        await self._db.refresh(api_key)

        return {
            "id": api_key.id,
            "name": api_key.name,
            "key": key_value,
            "scopes": api_key.scopes,
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "created_at": api_key.created_at.isoformat(),
        }

    async def verify_api_key(self, key_value: str) -> ApiKeyModel | None:
        """Verify an API key."""
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()

        result = await self._db.execute(
            select(ApiKeyModel).where(
                ApiKeyModel.key_hash == key_hash,
                ApiKeyModel.is_active == True,
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        api_key.last_used_at = datetime.utcnow()
        api_key.updated_at = datetime.utcnow()
        await self._db.commit()

        return api_key

    async def list_api_keys(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """List all API keys for a user."""
        result = await self._db.execute(select(ApiKeyModel).where(ApiKeyModel.user_id == user_id))
        keys = result.scalars().all()

        return [
            {
                "id": k.id,
                "name": k.name,
                "scopes": k.scopes,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat(),
            }
            for k in keys
        ]

    async def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """Revoke an API key."""
        result = await self._db.execute(
            select(ApiKeyModel).where(
                ApiKeyModel.id == key_id,
                ApiKeyModel.user_id == user_id,
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return False

        api_key.is_active = False
        api_key.updated_at = datetime.utcnow()
        await self._db.commit()

        if self._redis:
            await self._redis.delete(f"apikey:{api_key.key_hash}")

        return True

    async def rotate_api_key(self, key_id: str, user_id: str) -> dict[str, Any]:
        """Rotate an API key (deprecate old, create new)."""
        result = await self._db.execute(
            select(ApiKeyModel).where(
                ApiKeyModel.id == key_id,
                ApiKeyModel.user_id == user_id,
            )
        )
        old_key = result.scalar_one_or_none()

        if not old_key:
            raise ValueError("API key not found")

        old_key.is_active = False
        old_key.updated_at = datetime.utcnow()

        new_key_value = (
            f"{self._settings.api_key_prefix}{secrets.token_urlsafe(self._settings.api_key_length)}"
        )
        new_key_hash = hashlib.sha256(new_key_value.encode()).hexdigest()

        new_key = ApiKeyModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=f"{old_key.name} (rotated)",
            key_hash=new_key_hash,
            scopes=old_key.scopes,
            expires_at=old_key.expires_at,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self._db.add(old_key)
        self._db.add(new_key)
        await self._db.commit()

        return {
            "id": new_key.id,
            "key": new_key_value,
            "scopes": new_key.scopes,
            "created_at": new_key.created_at.isoformat(),
        }
