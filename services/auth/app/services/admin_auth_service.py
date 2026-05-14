"""Admin authentication service.

Security fixes applied:
- S-06/S-14: bcrypt.checkpw runs in thread pool executor (non-blocking)
- S-15/Q-07: AdminUserModel.updated_at is now set correctly (model has the column)
- B-02: Failed login no longer updates last_login_at
- B-03: Specific exception types caught instead of bare Exception
"""

import asyncio
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError
from sqlalchemy import select

from ..core.config import AuthSettings
from ..models.admin import AdminUserModel, AdminSessionModel
from ..services.utils import create_access_token, create_refresh_token, decode_token


class AdminAuthService:
    """Authentication service for platform admins - completely separate from tenant auth."""

    def __init__(self, db: Any, settings: AuthSettings, redis_client: Any = None):
        self._db = db
        self._settings = settings
        self._redis = redis_client

    async def login(
        self,
        email: str,
        password: str,
        device_info: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Authenticate admin and return tokens."""
        result = await self._db.execute(
            select(AdminUserModel).where(AdminUserModel.email == email)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            raise ValueError("Invalid credentials")

        if not admin.is_active:
            raise ValueError("Admin account is disabled")

        # S-14 fix: async bcrypt check (non-blocking)
        if not await self._check_password(password, admin.password_hash):
            # B-02 fix: do NOT update last_login_at on failed login
            raise ValueError("Invalid credentials")

        # Only update timestamps on successful login
        now = datetime.utcnow()
        admin.last_login_at = now
        admin.updated_at = now  # Q-07 fix: model now has updated_at column
        await self._db.commit()

        session = await self._create_session(admin, device_info, ip_address, user_agent)
        tokens = await self._create_tokens(admin, session.id)

        return {
            "admin": admin,
            "session": session,
            "tokens": tokens,
        }

    async def refresh_tokens(self, refresh_token: str) -> dict[str, Any]:
        """Refresh admin access token."""
        try:
            payload = decode_token(
                refresh_token,
                self._settings.secret_key,
                public_key=self._settings.effective_public_key,
            )
            if payload.get("type") != "refresh" or payload.get("scope") != "admin":
                raise ValueError("Invalid token type")

            admin_id = payload.get("sub")
            session_id = payload.get("session_id")

            result = await self._db.execute(
                select(AdminUserModel).where(AdminUserModel.id == admin_id)
            )
            admin = result.scalar_one_or_none()

            if not admin or not admin.is_active:
                raise ValueError("Admin not found or inactive")

            result = await self._db.execute(
                select(AdminSessionModel).where(
                    AdminSessionModel.id == session_id,
                    AdminSessionModel.is_active == True,  # noqa: E712
                )
            )
            session = result.scalar_one_or_none()

            if not session or session.expires_at < datetime.utcnow():
                raise ValueError("Session expired")

            tokens = await self._create_tokens(admin, session.id)
            return {"admin": admin, "tokens": tokens}

        except JWTError as e:
            raise ValueError(f"Invalid or expired refresh token: {e}")
        except ValueError:
            raise
        except Exception as e:
            # B-03 fix: log unexpected errors rather than silently swallowing them
            import logging
            logging.getLogger("auth.admin").error(f"Unexpected error during token refresh: {e}")
            raise ValueError("Token refresh failed")

    async def logout(self, admin_id: str, session_id: str | None = None) -> bool:
        """Logout admin and invalidate session."""
        if session_id:
            result = await self._db.execute(
                select(AdminSessionModel).where(AdminSessionModel.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                session.is_active = False
                await self._db.commit()

        if self._redis:
            await self._redis.delete(f"admin_token:{admin_id}:{session_id}")

        return True

    async def _check_password(self, plain: str, hashed: str | None) -> bool:
        """Verify password in a thread pool to avoid blocking the event loop (S-14 fix)."""
        if not hashed:
            return False
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8")),
        )

    async def _create_tokens(self, admin: AdminUserModel, session_id: str) -> dict[str, str]:
        """Create admin-scoped JWT tokens."""
        access_token = create_access_token(
            data={
                "sub": admin.id,
                "scope": "admin",
                "role": admin.role,
                "session_id": session_id,
            },
            secret_key=self._settings.secret_key,
            algorithm=self._settings.algorithm,
            expires_delta=timedelta(minutes=self._settings.access_token_expire_minutes),
            private_key=self._settings.effective_private_key,
        )

        refresh_token = create_refresh_token(
            data={
                "sub": admin.id,
                "scope": "admin",
                "session_id": session_id,
            },
            secret_key=self._settings.secret_key,
            algorithm=self._settings.algorithm,
            expires_delta=timedelta(days=self._settings.refresh_token_expire_days),
            private_key=self._settings.effective_private_key,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
        }

    async def _create_session(
        self,
        admin: AdminUserModel,
        device_info: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AdminSessionModel:
        """Create admin session."""
        refresh_token = secrets.token_urlsafe(32)
        refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        session = AdminSessionModel(
            id=str(uuid.uuid4()),
            admin_id=admin.id,
            refresh_token_hash=refresh_hash,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
            last_active_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            created_at=datetime.utcnow(),
        )

        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)

        return session
