from .base import BaseNotifier
from .slack import SlackNotifier
from .webhook import WebhookNotifier
from .rate_limiter import check_rate_limit

NOTIFIER_REGISTRY = {
    "slack": SlackNotifier,
    "webhook": WebhookNotifier,
    "generic_webhook": WebhookNotifier,
}


def get_notifier(channel_type: str) -> BaseNotifier | None:
    cls = NOTIFIER_REGISTRY.get(channel_type.lower())
    return cls() if cls else None


__all__ = [
    "BaseNotifier",
    "SlackNotifier",
    "WebhookNotifier",
    "check_rate_limit",
    "get_notifier",
]
