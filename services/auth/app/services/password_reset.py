"""Password reset service — token generation, storage in Redis, email delivery."""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserModel

logger = logging.getLogger(__name__)

# Token TTL: 1 hour
RESET_TOKEN_TTL_SECONDS = 3600
RESET_TOKEN_PREFIX = "pwd_reset:"


class PasswordResetService:
    """Handles password reset flow: request → token → verify → reset."""

    def __init__(self, db: AsyncSession, redis_client: Any, settings: Any):
        self._db = db
        self._redis = redis_client
        self._settings = settings

    async def request_reset(self, email: str) -> str | None:
        """
        Generate a password reset token for the given email.

        Returns the raw token (to be sent via email).
        Returns None if user not found (caller should NOT reveal this to client).
        """
        result = await self._db.execute(
            select(UserModel).where(UserModel.email == email, UserModel.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        if user.provider != "local":
            # OAuth users don't have passwords managed here
            return None

        # Generate a cryptographically secure token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Store in Redis: hash → user_id, TTL = 1 hour
        key = f"{RESET_TOKEN_PREFIX}{token_hash}"
        await self._redis.setex(key, RESET_TOKEN_TTL_SECONDS, user.id)

        logger.info(f"Password reset token generated for user {user.id}")
        return raw_token

    async def verify_token(self, raw_token: str) -> str | None:
        """
        Verify a reset token and return the user_id if valid.
        Does NOT consume the token — call reset_password to consume it.
        """
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        key = f"{RESET_TOKEN_PREFIX}{token_hash}"
        user_id = await self._redis.get(key)
        return user_id

    async def reset_password(self, raw_token: str, new_password: str) -> bool:
        """
        Reset the user's password using a valid token.
        Consumes the token (single-use).
        """
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        key = f"{RESET_TOKEN_PREFIX}{token_hash}"

        user_id = await self._redis.get(key)
        if not user_id:
            raise ValueError("Invalid or expired reset token")

        user = await self._db.get(UserModel, user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # Validate new password policy
        from .auth_service import AuthService
        svc = AuthService(self._db, self._settings, self._redis)
        svc._validate_password(new_password)

        # Update password
        import bcrypt
        user.password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"), bcrypt.gensalt(rounds=self._settings.bcrypt_rounds)
        ).decode("utf-8")
        user.updated_at = datetime.utcnow()
        await self._db.commit()

        # Consume the token (delete from Redis)
        await self._redis.delete(key)

        logger.info(f"Password reset completed for user {user_id}")
        return True

    async def send_reset_email(self, email: str, raw_token: str, frontend_url: str = "http://localhost:3000") -> bool:
        """
        Send password reset email via SMTP.

        Falls back to logging the reset link if SMTP is not configured.
        """
        reset_url = f"{frontend_url}/reset-password?token={raw_token}"

        # Try SMTP delivery
        smtp_host = getattr(self._settings, "smtp_host", None)
        if smtp_host:
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart

                smtp_port = getattr(self._settings, "smtp_port", 587)
                smtp_user = getattr(self._settings, "smtp_user", "")
                smtp_pass = getattr(self._settings, "smtp_password", "")
                smtp_from = getattr(self._settings, "smtp_from", "noreply@cloudvisor.io")

                msg = MIMEMultipart("alternative")
                msg["Subject"] = "CloudVisor — Reset your password"
                msg["From"] = smtp_from
                msg["To"] = email

                text_body = f"""
Hi,

You requested a password reset for your CloudVisor account.

Click the link below to reset your password (valid for 1 hour):
{reset_url}

If you didn't request this, you can safely ignore this email.

— The CloudVisor Team
"""
                html_body = f"""
<html><body>
<p>Hi,</p>
<p>You requested a password reset for your CloudVisor account.</p>
<p><a href="{reset_url}" style="background:#1a73e8;color:#fff;padding:10px 20px;border-radius:4px;text-decoration:none;">Reset Password</a></p>
<p>This link expires in 1 hour. If you didn't request this, ignore this email.</p>
<p>— The CloudVisor Team</p>
</body></html>
"""
                msg.attach(MIMEText(text_body, "plain"))
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.ehlo()
                    if smtp_port == 587:
                        server.starttls()
                    if smtp_user and smtp_pass:
                        server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_from, [email], msg.as_string())

                logger.info(f"Password reset email sent to {email}")
                return True

            except Exception as e:
                logger.error(f"SMTP delivery failed: {e}")

        # Fallback: log the reset link (dev/local mode)
        logger.info(
            f"[DEV MODE] Password reset link for {email}: {reset_url}"
        )
        return True
