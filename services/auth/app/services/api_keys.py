"""API key management service.

Fixes applied:
- M-05: Emit api_key.created, api_key.rotated, api_key.revoked Kafka audit events
- M-09: Audit log written on API key usage
- M-15: Per-key rate limits enforced via Redis
"""

import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ApiKeyModel, AuditLogModel


class ApiKeyService:
    """Service for managing API keys."""

    def __init__(
        self,
        db: AsyncSession,
        settings: Any,
        redis_client: Any = None,
        kafka_producer: Any = None,
    ):
        self._db = db
        self._settings = settings
        self._redis = redis_client
        self._kafka_producer = kafka_producer

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
        organization_id: str | None = None,
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

        # M-05 fix: emit api_key.created audit event
        if organization_id:
            await self._audit_log(
                organization_id=organization_id,
                user_id=user_id,
                event_type="api_key.created",
                event_data={"key_id": api_key.id, "name": name, "scopes": scopes or ["read"]},
            )
            await self._emit_kafka_event(
                organization_id=organization_id,
                user_id=user_id,
                event_type="api_key.created",
                key_id=api_key.id,
            )

        return {
            "id": api_key.id,
            "name": api_key.name,
            "key": key_value,  # Only returned once on creation
            "scopes": api_key.scopes,
            "expires_at": api_key.expires_at,
            "created_at": api_key.created_at,
        }

    async def verify_api_key(
        self,
        key_value: str,
        organization_id: str | None = None,
    ) -> ApiKeyModel | None:
        """Verify an API key and enforce per-key rate limits (M-15 fix)."""
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()

        result = await self._db.execute(
            select(ApiKeyModel).where(
                ApiKeyModel.key_hash == key_hash,
                ApiKeyModel.is_active == True,  # noqa: E712
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        # M-15 fix: enforce per-key rate limit
        if self._redis:
            from .rate_limiter import RateLimiter
            limiter = RateLimiter(self._redis)
            allowed = await limiter.check_api_rate(api_key.id)
            if not allowed:
                return None  # Rate limited — treat as invalid for this window

        api_key.last_used_at = datetime.utcnow()
        api_key.updated_at = datetime.utcnow()
        await self._db.commit()

        # M-09 fix: audit log for API key usage
        if organization_id:
            await self._audit_log(
                organization_id=organization_id,
                user_id=api_key.user_id,
                event_type="api_key.used",
                event_data={"key_id": api_key.id, "scopes": api_key.scopes},
            )

        return api_key

    async def list_api_keys(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """List all API keys for a user (never returns the key value)."""
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

    async def revoke_api_key(
        self,
        key_id: str,
        user_id: str,
        organization_id: str | None = None,
    ) -> bool:
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

        # M-05 fix: emit api_key.revoked audit event
        if organization_id:
            await self._audit_log(
                organization_id=organization_id,
                user_id=user_id,
                event_type="api_key.revoked",
                event_data={"key_id": key_id},
            )
            await self._emit_kafka_event(
                organization_id=organization_id,
                user_id=user_id,
                event_type="api_key.revoked",
                key_id=key_id,
            )

        return True

    async def rotate_api_key(
        self,
        key_id: str,
        user_id: str,
        organization_id: str | None = None,
    ) -> dict[str, Any]:
        """Rotate an API key (deprecate old, create new).

        M-14 note: The old key is immediately deactivated. A configurable grace period
        can be added by setting old_key.expires_at = now + grace_period instead.
        """
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

        self._db.add(new_key)
        await self._db.commit()

        # M-05 fix: emit api_key.rotated audit event
        if organization_id:
            await self._audit_log(
                organization_id=organization_id,
                user_id=user_id,
                event_type="api_key.rotated",
                event_data={"old_key_id": key_id, "new_key_id": new_key.id},
            )
            await self._emit_kafka_event(
                organization_id=organization_id,
                user_id=user_id,
                event_type="api_key.rotated",
                key_id=new_key.id,
            )

        return {
            "id": new_key.id,
            "name": new_key.name,
            "key": new_key_value,  # Only returned once on rotation
            "scopes": new_key.scopes,
            "expires_at": new_key.expires_at,
            "created_at": new_key.created_at,
        }

    async def _audit_log(
        self,
        organization_id: str,
        user_id: str,
        event_type: str,
        event_data: dict,
    ) -> None:
        """Write audit log entry for API key events."""
        log = AuditLogModel(
            organization_id=organization_id,
            user_id=user_id,
            event_type=event_type,
            event_data=event_data,
            success=True,
            timestamp=datetime.utcnow(),
        )
        self._db.add(log)
        await self._db.commit()

    async def _emit_kafka_event(
        self,
        organization_id: str,
        user_id: str,
        event_type: str,
        key_id: str,
    ) -> None:
        """Emit API key lifecycle event to Kafka (M-05 fix)."""
        if not self._kafka_producer:
            return
        try:
            await self._kafka_producer.emit_api_key_event(
                organization_id=organization_id,
                user_id=user_id,
                event_type=event_type,
                key_id=key_id,
            )
        except Exception as e:
            import logging
            logging.getLogger("auth").debug(f"API key Kafka event failed (non-fatal): {e}")
