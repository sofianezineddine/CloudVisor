"""Unit tests for the RealtimeConsumerManager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_settings(enabled=True, sqs_url="https://sqs.us-east-1.amazonaws.com/123/queue"):
    s = MagicMock()
    s.realtime_enabled = enabled
    s.aws_cloudtrail_sqs_queue_url = sqs_url
    s.aws_cloudtrail_region = "us-east-1"
    s.azure_event_hub_connection_string = ""
    s.azure_event_hub_name = "cloudvisor-activity-logs"
    s.azure_event_hub_consumer_group = "$Default"
    s.gcp_pubsub_subscription = ""
    s.oci_stream_ocid = ""
    s.oci_stream_endpoint = ""
    return s


class TestRealtimeConsumerManager:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        from app.consumers.manager import RealtimeConsumerManager
        producer = AsyncMock()
        settings = _make_settings(enabled=False)
        mgr = RealtimeConsumerManager(event_producer=producer, settings=settings)
        await mgr.start()
        assert mgr._running is True
        await mgr.stop()
        assert mgr._running is False

    @pytest.mark.asyncio
    async def test_no_consumers_when_disabled(self):
        from app.consumers.manager import RealtimeConsumerManager
        producer = AsyncMock()
        settings = _make_settings(enabled=False)
        mgr = RealtimeConsumerManager(event_producer=producer, settings=settings)
        await mgr.start()
        count = await mgr.add_account_consumers(
            account_id="acct-1",
            organization_id="org-1",
            provider="aws",
            cloud_account_id="123456789012",
            credentials={"access_key": "k", "secret_key": "s"},
        )
        assert count == 0
        await mgr.stop()

    @pytest.mark.asyncio
    async def test_add_aws_consumer_when_enabled(self):
        from app.consumers.manager import RealtimeConsumerManager
        producer = AsyncMock()
        settings = _make_settings(enabled=True, sqs_url="https://sqs.us-east-1.amazonaws.com/123/q")

        mock_consumer = AsyncMock()
        mock_consumer._running = True

        with patch("app.consumers.manager.RealtimeConsumerManager._build_cloudtrail_consumer",
                   return_value=mock_consumer):
            mgr = RealtimeConsumerManager(event_producer=producer, settings=settings)
            await mgr.start()
            count = await mgr.add_account_consumers(
                account_id="acct-1",
                organization_id="org-1",
                provider="aws",
                cloud_account_id="123456789012",
                credentials={"access_key": "k", "secret_key": "s"},
            )
            assert count == 1
            assert "acct-1" in mgr.get_active_accounts()
            await mgr.stop()

    @pytest.mark.asyncio
    async def test_remove_account_consumers(self):
        from app.consumers.manager import RealtimeConsumerManager
        producer = AsyncMock()
        settings = _make_settings(enabled=True)

        mock_consumer = AsyncMock()
        mock_consumer._running = True

        with patch("app.consumers.manager.RealtimeConsumerManager._build_cloudtrail_consumer",
                   return_value=mock_consumer):
            mgr = RealtimeConsumerManager(event_producer=producer, settings=settings)
            await mgr.start()
            await mgr.add_account_consumers(
                account_id="acct-1",
                organization_id="org-1",
                provider="aws",
                cloud_account_id="123456789012",
                credentials={},
            )
            await mgr.remove_account_consumers("acct-1")
            assert "acct-1" not in mgr.get_active_accounts()
            mock_consumer.stop.assert_called_once()
            await mgr.stop()

    @pytest.mark.asyncio
    async def test_no_consumer_for_azure_without_config(self):
        from app.consumers.manager import RealtimeConsumerManager
        producer = AsyncMock()
        settings = _make_settings(enabled=True, sqs_url="")
        settings.azure_event_hub_connection_string = ""
        mgr = RealtimeConsumerManager(event_producer=producer, settings=settings)
        await mgr.start()
        count = await mgr.add_account_consumers(
            account_id="acct-2",
            organization_id="org-1",
            provider="azure",
            cloud_account_id="sub-uuid",
            credentials={},
        )
        assert count == 0
        await mgr.stop()
