"""Unit tests for retry logic."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestRetryConfig:
    def test_default_values(self):
        from app.services.retry import RetryConfig
        cfg = RetryConfig()
        assert cfg.max_retries >= 1
        assert cfg.initial_delay_seconds > 0
        assert cfg.max_delay_seconds >= cfg.initial_delay_seconds

    def test_custom_values(self):
        from app.services.retry import RetryConfig
        cfg = RetryConfig(max_retries=3, initial_delay_seconds=2.0, max_delay_seconds=30.0)
        assert cfg.max_retries == 3
        assert cfg.initial_delay_seconds == 2.0
        assert cfg.max_delay_seconds == 30.0


class TestRetryAsync:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        from app.services.retry import retry_async, RetryConfig
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_async(fn, RetryConfig(max_retries=3))
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_temporary_error(self):
        from app.services.retry import retry_async, RetryConfig, TemporaryException
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TemporaryException("transient")
            return "ok"

        cfg = RetryConfig(max_retries=5, initial_delay_seconds=0.01, max_delay_seconds=0.1)
        result = await retry_async(fn, cfg)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        from app.services.retry import retry_async, RetryConfig, TemporaryException

        async def fn():
            raise TemporaryException("always fails")

        cfg = RetryConfig(max_retries=2, initial_delay_seconds=0.01, max_delay_seconds=0.1)
        with pytest.raises(Exception):
            await retry_async(fn, cfg)

    @pytest.mark.asyncio
    async def test_does_not_retry_on_auth_error(self):
        from app.services.retry import retry_async, RetryConfig
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            raise PermissionError("auth failed")

        cfg = RetryConfig(max_retries=5, initial_delay_seconds=0.01, max_delay_seconds=0.1)
        with pytest.raises(PermissionError):
            await retry_async(fn, cfg)
        # Should not retry auth errors
        assert call_count == 1
