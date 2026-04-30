import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


async def check_rate_limit(channel_id: str, redis: Any) -> bool:
    """Returns True if message should be sent, False if rate limited (max 10/min)."""
    if not redis:
        return True  # No Redis = no rate limiting
    minute_key = f"notifier:{channel_id}:minute:{int(time.time() // 60)}"
    try:
        count = await redis.incr(minute_key)
        if count == 1:
            await redis.expire(minute_key, 120)  # 2 min TTL for safety
        if count > 10:
            logger.warning(
                f"Rate limit exceeded for channel {channel_id}: {count}/min"
            )
            return False
        return True
    except Exception as e:
        logger.error(f"Rate limiter error: {e}")
        return True  # Fail open
