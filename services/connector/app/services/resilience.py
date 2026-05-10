"""Shared resilience helper: retry + circuit breaker for cloud API calls.

The AWS client had its own inline `_call_with_retry_and_circuit_breaker`.
This module extracts that pattern so Azure, GCP, and OCI clients can use
the same behaviour. Every cloud API call should go through `resilient_call`.

Exception classification is provider-agnostic: each caller passes a small
"classify" function that translates a provider-specific exception into one
of the standard retryable categories (RateLimitException / TemporaryException)
or re-raises for non-retryable errors.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from .circuit_breaker import (
    CircuitBreakerOpenException,
    CircuitBreakerRegistry,
    get_circuit_breaker_registry,
)
from .retry import (
    RateLimitException,
    RetryConfig,
    TemporaryException,
    retry_async,
)

logger = logging.getLogger(__name__)

# A classify function takes an exception and either:
#   - returns a RetryableException to be retried (RateLimit / Temporary)
#   - returns None to re-raise the original exception (non-retryable)
#   - raises a new exception type (e.g. to normalize provider errors)
ClassifyFn = Callable[[Exception], Exception | None]


# Default retry config used across all providers. Matches the AWS behaviour
# previously hardcoded in aws.py.
_DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    initial_delay_seconds=1.0,
    max_delay_seconds=60.0,
    exponential_base=2.0,
    jitter=True,
)


async def resilient_call(
    *,
    provider: str,
    service: str,
    func: Callable[..., Awaitable[Any]] | Callable[..., Any],
    classify: ClassifyFn,
    registry: CircuitBreakerRegistry | None = None,
    retry_config: RetryConfig | None = None,
    failure_threshold: float = 0.5,
    failure_window_seconds: int = 300,
    recovery_timeout_seconds: int = 60,
    min_requests_for_threshold: int = 10,
    **kwargs: Any,
) -> Any:
    """Call a cloud API function with retry + circuit breaker protection.

    Args:
        provider: ``aws`` / ``azure`` / ``gcp`` / ``oci`` — used for CB naming.
        service: the provider service name (e.g. ``s3``, ``compute``, ``storage``).
            Each (provider, service) tuple gets its own circuit breaker so one
            broken service doesn't kill others.
        func: the async (or sync-returning-awaitable) callable to invoke.
        classify: translates provider-specific exceptions into RateLimit /
            Temporary / <unchanged for non-retryable>.
        registry: circuit breaker registry, defaults to the global one.
        retry_config: retry configuration, defaults to spec-compliant config.
        **kwargs: forwarded to ``func``.

    Returns:
        The return value of ``func``.

    Raises:
        CircuitBreakerOpenException: if the circuit for this service is open.
        Any exception from ``func`` that ``classify`` doesn't mark retryable.
    """
    reg = registry or await get_circuit_breaker_registry()
    cfg = retry_config or _DEFAULT_RETRY_CONFIG

    breaker = await reg.get_or_create(
        name=f"{provider}-{service}",
        failure_threshold=failure_threshold,
        failure_window_seconds=failure_window_seconds,
        recovery_timeout_seconds=recovery_timeout_seconds,
        min_requests_for_threshold=min_requests_for_threshold,
    )

    async def _invoke() -> Any:
        try:
            result = func(**kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result
        except (TimeoutError, ConnectionError, asyncio.TimeoutError) as e:
            raise TemporaryException(f"{provider}/{service} connection error: {type(e).__name__}")
        except Exception as e:
            # Let caller-provided classifier decide how to treat it.
            classified = classify(e)
            if isinstance(classified, (RateLimitException, TemporaryException)):
                raise classified
            # Non-retryable — re-raise original
            raise

    @retry_async(
        config=cfg,
        retryable_exceptions=(RateLimitException, TemporaryException),
    )
    async def _with_retry() -> Any:
        return await _invoke()

    return await breaker.call(_with_retry)


# ── Provider-specific classifiers ─────────────────────────────────────────────

def classify_azure(exc: Exception) -> Exception | None:
    """Classify an Azure SDK exception as retryable or not."""
    msg = str(exc)
    # Azure SDK exposes HttpResponseError with .status_code when network-level,
    # and plain strings otherwise. Check both.
    status = getattr(exc, "status_code", None) or getattr(exc, "response", None)
    if status is not None and hasattr(status, "status_code"):
        status = status.status_code

    if status == 429 or "TooManyRequests" in msg or "throttled" in msg.lower():
        retry_after = None
        if hasattr(exc, "response") and exc.response is not None:
            headers = getattr(exc.response, "headers", {}) or {}
            ra = headers.get("Retry-After") or headers.get("retry-after")
            if ra:
                try:
                    retry_after = float(ra)
                except (TypeError, ValueError):
                    retry_after = None
        return RateLimitException(retry_after)

    if status is not None and isinstance(status, int) and status >= 500:
        return TemporaryException(f"Azure HTTP {status}")

    if "ServiceUnavailable" in msg or "InternalServerError" in msg or "GatewayTimeout" in msg:
        return TemporaryException(f"Azure transient error: {msg[:120]}")

    return None


def classify_gcp(exc: Exception) -> Exception | None:
    """Classify a GCP SDK exception as retryable or not."""
    # google.api_core.exceptions has TooManyRequests, ServiceUnavailable, etc.
    exc_type = type(exc).__name__
    msg = str(exc)

    if exc_type in ("TooManyRequests", "ResourceExhausted") or "429" in msg:
        return RateLimitException(None)

    if exc_type in ("ServiceUnavailable", "InternalServerError", "DeadlineExceeded", "Aborted"):
        return TemporaryException(f"GCP transient: {exc_type}")

    if "503" in msg or "500" in msg or "504" in msg:
        return TemporaryException(f"GCP HTTP error: {msg[:120]}")

    return None


def classify_oci(exc: Exception) -> Exception | None:
    """Classify an OCI SDK exception as retryable or not."""
    # oci.exceptions.ServiceError has .status attribute.
    status = getattr(exc, "status", None)
    code = getattr(exc, "code", "") or ""

    if status == 429 or code == "TooManyRequests":
        retry_after = None
        headers = getattr(exc, "headers", {}) or {}
        ra = headers.get("retry-after") if hasattr(headers, "get") else None
        if ra:
            try:
                retry_after = float(ra)
            except (TypeError, ValueError):
                retry_after = None
        return RateLimitException(retry_after)

    if status is not None and isinstance(status, int) and status >= 500:
        return TemporaryException(f"OCI HTTP {status}")

    if code in ("InternalServerError", "ServiceUnavailable"):
        return TemporaryException(f"OCI transient: {code}")

    return None


__all__ = [
    "CircuitBreakerOpenException",
    "classify_azure",
    "classify_gcp",
    "classify_oci",
    "resilient_call",
]
