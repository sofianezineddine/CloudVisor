from .base import BaseNotifier
from .slack import SlackNotifier
from .webhook import WebhookNotifier
from .email import EmailNotifier
from .jira import JiraNotifier
from .pagerduty import PagerDutyNotifier
from .teams import TeamsNotifier
from .servicenow import ServiceNowNotifier
from .rate_limiter import check_rate_limit

NOTIFIER_REGISTRY = {
    "slack": SlackNotifier,
    "webhook": WebhookNotifier,
    "generic_webhook": WebhookNotifier,
    "email": EmailNotifier,
    "jira": JiraNotifier,
    "pagerduty": PagerDutyNotifier,
    "teams": TeamsNotifier,
    "microsoft_teams": TeamsNotifier,
    "servicenow": ServiceNowNotifier,
    "service_now": ServiceNowNotifier,
}


def get_notifier(channel_type: str) -> BaseNotifier | None:
    cls = NOTIFIER_REGISTRY.get(channel_type.lower())
    return cls() if cls else None


__all__ = [
    "BaseNotifier",
    "SlackNotifier",
    "WebhookNotifier",
    "EmailNotifier",
    "JiraNotifier",
    "PagerDutyNotifier",
    "TeamsNotifier",
    "ServiceNowNotifier",
    "check_rate_limit",
    "get_notifier",
]
