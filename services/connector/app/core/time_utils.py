"""Timezone-aware timestamp helpers.

Python 3.12 deprecates `datetime.utcnow()`. Use these helpers instead so
every timestamp in the connector is timezone-aware (UTC).
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def utcnow_naive() -> datetime:
    """Return current UTC time as a NAIVE datetime (for legacy code paths
    that can't yet accept tz-aware values). Prefer ``utcnow()``.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
