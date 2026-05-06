"""Authentication service - handles login, registration, tokens."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
import bcrypt
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import AuthSettings
from ..models import UserModel, OrganizationModel, SessionModel, AuditLogModel, CvClientModel
from .utils import create_access_token, create_refresh_token, decode_token


class AuthService:
    """Authentication service for user login/registration."""

    def __init__(self, db: AsyncSession, settings: AuthSettings, redis_client: Any = None, kafka_producer: Any = None):
        self._db = db
        self._settings = settings
        self._redis = redis_client
        self._kafka_producer = kafka_producer

    async def oauth_login_or_register(
        self,
        email: str,
        provider: str,
        provider_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        organization_name: str | None = None,
    ) -> dict[str, Any]:
        """Login or register user via OAuth provider."""
        # Check if user exists
        existing = await self._db.execute(select(UserModel).where(UserModel.email == email))
        user = existing.scalar_one_or_none()

        if user:
            # Existing user - just log them in
            user.last_login_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            await self._db.commit()
        else:
            # New user via OAuth - create org + user
            if not organization_name:
                organization_name = email.split("@")[1].split(".")[0].title()

            org_id = str(uuid.uuid4())
            slug_base = organization_name.strip().lower().replace(" ", "-")
            slug = slug_base[:50]
            i = 1
            while True:
                existing_slug = await self._db.execute(
                    select(OrganizationModel).where(OrganizationModel.slug == slug)
                )
                if not existing_slug.scalar_one_or_none():
                    break
                slug = f"{slug_base}-{i}"
                i += 1

            org = OrganizationModel(
                id=org_id,
                name=organization_name,
                slug=slug,
                plan="free",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self._db.add(org)

            user_id = str(uuid.uuid4())
            user = UserModel(
                id=user_id,
                organization_id=org_id,
                email=email,
                password_hash=None,  # No password for OAuth users
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                is_superuser=True,
                provider=provider,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self._db.add(user)
            await self._db.commit()
            await self._db.refresh(user)

            # Create cv_clients record
            existing_cv = await self._db.execute(
                select(CvClientModel).where(CvClientModel.organization_name == organization_name)
            )
            if not existing_cv.scalar_one_or_none():
                contact_name = f"{first_name or ''} {last_name or ''}".strip() or email.split("@")[0]
                cv_client = CvClientModel(
                    organization_id=org_id,
                    organization_name=organization_name,
                    contact_name=contact_name,
                    contact_email=email,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self._db.add(cv_client)
                await self._db.commit()
                await self._db.refresh(cv_client)
                user.cv_client_id = cv_client.id
                await self._db.commit()

        session = await self._create_session(user, None, None, None)
        tokens = await self._create_tokens(user, session.id)

        await self._audit_log(
            user.organization_id, user.id, f"auth.oauth.{provider}", {"email": email}, success=True
        )

        return {"user": user, "session": session, "tokens": tokens}

    async def register(
        self,
        email: str,
        password: str,
        organization_name: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> dict[str, Any]:
        """Register a new user and organization."""
        # Validate password policy
        self._validate_password(password)

        existing = await self._db.execute(select(UserModel).where(UserModel.email == email))
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")

        org_id = str(uuid.uuid4())
        slug_base = organization_name.strip().lower().replace(" ", "-")
        slug_candidate = slug_base[:50]
        i = 1
        while True:
            existing_slug = await self._db.execute(
                select(OrganizationModel).where(OrganizationModel.slug == slug_candidate)
            )
            if not existing_slug.scalar_one_or_none():
                slug = slug_candidate
                break
            slug_candidate = f"{slug_base}-{i}"
            i += 1
        org = OrganizationModel(
            id=org_id,
            name=organization_name,
            slug=slug,
            plan="free",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self._db.add(org)

        user_id = str(uuid.uuid4())
        user = UserModel(
            id=user_id,
            organization_id=org_id,
            email=email,
            password_hash=self._hash_password(password),
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_superuser=True,
            provider="local",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)

        # Link user to cv_clients record
        existing_cv = await self._db.execute(
            select(CvClientModel).where(CvClientModel.organization_name == organization_name)
        )
        if not existing_cv.scalar_one_or_none():
            contact_name = f"{first_name or ''} {last_name or ''}".strip() or email.split("@")[0]
            cv_client = CvClientModel(
                organization_id=org_id,
                organization_name=organization_name,
                contact_name=contact_name,
                contact_email=email,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self._db.add(cv_client)
            await self._db.commit()
            await self._db.refresh(cv_client)
            
            # Link user to cv_client
            user.cv_client_id = cv_client.id
            await self._db.commit()

        session = await self._create_session(user, None, None, None)

        await self._audit_log(org_id, user_id, "user.registered", {"email": email}, success=True)

        # Emit org.created Kafka event
        if self._kafka_producer:
            try:
                await self._kafka_producer.emit_org_event(
                    organization_id=org_id,
                    event_type="org.created",
                    data={"name": organization_name, "plan": "free", "slug": slug},
                )
            except Exception as e:
                import logging
                logging.getLogger("auth").debug(f"org.created event failed (non-fatal): {e}")

        tokens = await self._create_tokens(user, session.id)
        return {"user": user, "session": session, "tokens": tokens}

    async def login(
        self,
        email: str,
        password: str,
        mfa_code: str | None = None,
        device_info: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Authenticate user and return tokens."""
        user = await self._get_user_by_email(email)

        if not user:
            raise ValueError("Invalid credentials")

        if not await self._check_password(password, user.password_hash):
            await self._record_failed_login(user)
            await self._audit_log(
                user.organization_id,
                user.id,
                "auth.login.failed",
                {"email": email, "reason": "invalid_password"},
                success=False,
            )
            raise ValueError("Invalid credentials")

        if user.mfa_enabled and not mfa_code:
            raise ValueError("MFA required")

        if user.mfa_enabled:
            from .mfa import verify_totp

            if not verify_totp(user.mfa_secret, mfa_code):
                await self._audit_log(
                    user.organization_id,
                    user.id,
                    "auth.login.failed",
                    {"email": email, "reason": "invalid_mfa"},
                    success=False,
                )
                raise ValueError("Invalid MFA code")

        if user.locked_until and user.locked_until > datetime.utcnow():
            raise ValueError("Account is locked")

        user.failed_login_attempts = 0
        user.last_login_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        await self._db.commit()

        session = await self._create_session(user, device_info, ip_address, user_agent)
        tokens = await self._create_tokens(user, session.id)

        await self._audit_log(
            user.organization_id, user.id, "auth.login.success", {"email": email}, success=True
        )

        return {"user": user, "session": session, "tokens": tokens}

    async def refresh_tokens(
        self,
        refresh_token: str,
    ) -> dict[str, Any]:
        """Refresh access token using refresh token."""
        try:
            payload = decode_token(
                refresh_token,
                self._settings.secret_key,
                public_key=self._settings.effective_public_key,
            )
            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")

            user_id = payload.get("sub")
            session_id = payload.get("session_id")

            user = await self._db.get(UserModel, user_id)
            if not user or not user.is_active:
                raise ValueError("User not found or inactive")

            session = await self._db.get(SessionModel, session_id)
            if not session or not session.is_active:
                raise ValueError("Session expired")

            tokens = await self._create_tokens(user, session.id)
            return {"user": user, "tokens": tokens}

        except JWTError:
            raise ValueError("Invalid or expired refresh token")

    async def logout(
        self,
        user_id: str,
        session_id: str | None = None,
    ) -> bool:
        """Logout user and invalidate session."""
        if session_id:
            session = await self._db.get(SessionModel, session_id)
            if session:
                session.is_active = False
                await self._db.commit()

        if self._redis:
            await self._redis.delete(f"token:{user_id}:{session_id}")

        return True

    async def invalidate_all_sessions(self, user_id: str, except_session_id: str | None = None) -> int:
        """Invalidate all active sessions for a user — called on password change.

        Spec §3.3: Force-expire all sessions on password change or suspicious activity.
        Returns the number of sessions invalidated.
        """
        from sqlalchemy import update

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

        # Also purge any cached tokens in Redis
        if self._redis:
            try:
                pattern = f"token:{user_id}:*"
                keys = await self._redis.keys(pattern)
                if keys:
                    await self._redis.delete(*keys)
            except Exception:
                pass

        count = result.rowcount or 0
        import logging
        logging.getLogger("auth").info(
            f"Invalidated {count} session(s) for user {user_id} after password change"
        )
        return count

    def _validate_password(self, password: str) -> None:
        """Validate password against configured policy."""
        if len(password) < self._settings.password_min_length:
            raise ValueError(
                f"Password must be at least {self._settings.password_min_length} characters"
            )
        if self._settings.password_require_uppercase and not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        if self._settings.password_require_lowercase and not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter")
        if self._settings.password_require_digit and not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit")
        if self._settings.password_require_special and not any(
            not c.isalnum() for c in password
        ):
            raise ValueError("Password must contain at least one special character")

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    async def _check_password(self, plain: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    async def _get_user_by_email(self, email: str) -> UserModel | None:
        """Get user by email."""
        result = await self._db.execute(select(UserModel).where(UserModel.email == email))
        return result.scalar_one_or_none()

    async def _create_tokens(self, user: UserModel, session_id: str) -> dict[str, str]:
        """Create access and refresh tokens — RS256 when keys configured, HS256 fallback."""
        access_token = create_access_token(
            data={"sub": user.id, "org_id": user.organization_id, "session_id": session_id},
            secret_key=self._settings.secret_key,
            algorithm=self._settings.algorithm,
            expires_delta=timedelta(minutes=self._settings.access_token_expire_minutes),
            private_key=self._settings.effective_private_key,
        )

        refresh_token = create_refresh_token(
            data={"sub": user.id, "session_id": session_id},
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
        user: UserModel,
        device_info: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> SessionModel:
        """Create a new session."""
        refresh_token = secrets.token_urlsafe(32)
        refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        session = SessionModel(
            id=str(uuid.uuid4()),
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
            last_active_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=self._settings.session_expire_days),
            created_at=datetime.utcnow(),
        )

        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)

        return session

    async def _record_failed_login(self, user: UserModel) -> None:
        """Record failed login attempt and lock if necessary."""
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)

        user.updated_at = datetime.utcnow()
        await self._db.commit()

    async def _audit_log(
        self,
        organization_id: str,
        user_id: str | None,
        event_type: str,
        event_data: dict,
        success: bool = True,
        failure_reason: str | None = None,
    ) -> None:
        """Create audit log entry in PostgreSQL and publish to Kafka audit.events topic."""
        log = AuditLogModel(
            organization_id=organization_id,
            user_id=user_id,
            event_type=event_type,
            event_data=event_data,
            success=success,
            failure_reason=failure_reason,
            timestamp=datetime.utcnow(),
        )
        self._db.add(log)
        await self._db.commit()

        # Publish to Kafka audit.events (non-fatal if unavailable)
        if self._kafka_producer:
            try:
                import json
                event = {
                    "event_type": event_type,
                    "organization_id": organization_id,
                    "user_id": user_id,
                    "event_data": event_data,
                    "success": success,
                    "failure_reason": failure_reason,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                await self._kafka_producer.send_and_wait(
                    "audit.events",
                    key=(user_id or organization_id).encode("utf-8"),
                    value=json.dumps(event, default=str).encode("utf-8"),
                )
            except Exception as e:
                import logging
                logging.getLogger("auth").debug(f"Kafka audit publish failed (non-fatal): {e}")
