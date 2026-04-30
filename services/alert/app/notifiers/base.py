import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, finding: dict[str, Any], channel: dict[str, Any]) -> bool:
        """Send a notification. Returns True on success."""
        ...

    async def send_with_retry(
        self,
        finding: dict[str, Any],
        channel: dict[str, Any],
        max_retries: int = 3,
    ) -> bool:
        for attempt in range(max_retries):
            try:
                result = await self.send(finding, channel)
                if result:
                    return True
            except Exception as e:
                logger.warning(f"Notifier attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1 * (2 ** attempt))  # 1s, 2s, 4s
        logger.error(f"Notifier failed after {max_retries} attempts")
        return False
