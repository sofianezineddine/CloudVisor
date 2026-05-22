"""Rate limiting service using Redis sliding window counter."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter backed by Redis.

    Limits:
    - Login attempts: 10 per minute per IP
    - Password reset requests: 3 per hour per email
    - API requests: configurable per-key limit
    """

    def __init__(self, redis_client: Any):
        self._redis = redis_client

    async def check_login_rate(self, ip_address: str) -> bool:
        """
        Check if login attempts from this IP are within limit.
        Returns True if allowed, False if rate limited.
        Limit: 10 attempts per minute per IP.
        """
        return await self._check(
            key=f"rate:login:{ip_address}",
            limit=10,
            window_seconds=60,
        )

    async def check_password_reset_rate(self, email: str) -> bool:
        """
        Check if password reset requests for this email are within limit.
        Limit: 3 requests per hour per email.
        """
        return await self._check(
            key=f"rate:pwd_reset:{email}",
            limit=3,
            window_seconds=3600,
        )

    async def check_api_rate(self, key_id: str, limit_per_minute: int = 60) -> bool:
        """
        Check if API key requests are within limit.
        Limit: configurable per key, default 60/min.
        """
        return await self._check(
            key=f"rate:api:{key_id}",
            limit=limit_per_minute,
            window_seconds=60,
        )

    async def check_register_rate(self, ip_address: str) -> bool:
        """
        Check if registration attempts from this IP are within limit.
        Limit: 5 registrations per hour per IP.
        """
        return await self._check(
            key=f"rate:register:{ip_address}",
            limit=5,
            window_seconds=3600,
        )

    # ─── Account Lockout ──────────────────────────────────────────────────────

    async def record_failed_login(self, email: str) -> int:
        """
        Record a failed login attempt for an account.
        Returns the current failure count.
        
        After 5 failed attempts, the account is locked for 15 minutes.
        After 10 failed attempts, locked for 1 hour.
        After 20 failed attempts, locked for 24 hours.
        """
        key = f"lockout:failures:{email}"
        try:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, 86400)  # Track failures for 24 hours
            results = await pipe.execute()
            count = results[0]

            # Set lockout based on failure count
            if count >= 20:
                await self._redis.setex(f"lockout:locked:{email}", 86400, "1")  # 24 hours
            elif count >= 10:
                await self._redis.setex(f"lockout:locked:{email}", 3600, "1")  # 1 hour
            elif count >= 5:
                await self._redis.setex(f"lockout:locked:{email}", 900, "1")  # 15 minutes

            return count
        except Exception as e:
            logger.warning(f"Account lockout Redis error: {e}")
            return 0

    async def is_account_locked(self, email: str) -> bool:
        """Check if an account is currently locked due to failed login attempts."""
        try:
            locked = await self._redis.get(f"lockout:locked:{email}")
            return locked is not None
        except Exception as e:
            logger.warning(f"Account lockout check Redis error: {e}")
            return False

    async def clear_failed_logins(self, email: str) -> None:
        """Clear failed login counter on successful login."""
        try:
            await self._redis.delete(f"lockout:failures:{email}")
            await self._redis.delete(f"lockout:locked:{email}")
        except Exception as e:
            logger.warning(f"Clear lockout Redis error: {e}")

    async def get_lockout_remaining(self, email: str) -> int | None:
        """Get remaining lockout time in seconds, or None if not locked."""
        try:
            ttl = await self._redis.ttl(f"lockout:locked:{email}")
            return ttl if ttl > 0 else None
        except Exception:
            return None

    async def _check(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Sliding window counter using Redis INCR + EXPIRE.
        Returns True if within limit, False if exceeded.
        """
        try:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()
            count = results[0]
            return count <= limit
        except Exception as e:
            # If Redis is unavailable, allow the request (fail open)
            logger.warning(f"Rate limiter Redis error (fail open): {e}")
            return True

    async def get_remaining(self, key: str, limit: int) -> int:
        """Get remaining requests for a rate limit key."""
        try:
            count = await self._redis.get(key)
            current = int(count) if count else 0
            return max(0, limit - current)
        except Exception:
            return limit
