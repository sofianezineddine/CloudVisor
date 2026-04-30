"""Rate limiting service for copilot queries."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for copilot queries using Redis."""

    def __init__(self, redis_client):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client

    async def check_query_rate(self, user_id: str, organization_id: str) -> bool:
        """
        Check if user is within rate limits.

        Args:
            user_id: User ID
            organization_id: Organization ID

        Returns:
            True if within limits, False if rate limited
        """
        # Rate limit: 20 queries per minute per user
        key = f"copilot:ratelimit:{organization_id}:{user_id}:minute"

        try:
            count = await self.redis.incr(key)

            if count == 1:
                # First request in this minute, set expiry
                await self.redis.expire(key, 60)

            if count > 20:
                logger.warning(
                    f"Rate limit exceeded for user {user_id} in org {organization_id}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow the request if Redis is down
            return True
