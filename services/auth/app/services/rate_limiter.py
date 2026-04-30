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
