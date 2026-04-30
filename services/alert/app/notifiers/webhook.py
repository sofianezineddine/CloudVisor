import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

from .base import BaseNotifier

logger = logging.getLogger(__name__)


class WebhookNotifier(BaseNotifier):
    async def send(self, finding: dict[str, Any], channel: dict[str, Any]) -> bool:
        config = channel.get("config", {})
        url = config.get("url")
        secret = config.get("secret", "")
        if not url:
            logger.error("Webhook channel missing url")
            return False

        payload_bytes = json.dumps(finding, default=str).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8") if secret else b"",
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-CloudVisor-Signature": f"sha256={signature}",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, content=payload_bytes, headers=headers)
                if 200 <= response.status_code < 300:
                    return True
                logger.warning(
                    f"Webhook returned {response.status_code}: {response.text[:100]}"
                )
                return False
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return False
