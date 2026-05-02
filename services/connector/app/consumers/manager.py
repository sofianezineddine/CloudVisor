"""Real-time consumer manager.

Manages the lifecycle of all provider-specific real-time event consumers.
Each consumer is only started when its required configuration is present.
The manager handles startup, shutdown, and automatic restart on failure.
"""

import asyncio
import logging
from typing import Any

from ..producers import ResourceEventProducer

logger = logging.getLogger(__name__)

# Restart delay after a consumer crashes (seconds)
_RESTART_DELAY = 30


class RealtimeConsumerManager:
    """
    Manages all real-time cloud event consumers.

    Consumers are started per-account when an account is registered and
    its real-time config is available.  For global (non-per-account)
    consumers the manager starts them once at service startup.

    Lifecycle:
        manager.start()   — called from init_dependencies()
        manager.stop()    — called from shutdown_dependencies()
        manager.add_account_consumers(account, credentials)
        manager.remove_account_consumers(account_id)
    """

    def __init__(
        self,
        event_producer: ResourceEventProducer,
        settings: Any,  # ConnectorSettings
    ):
        self._producer = event_producer
        self._settings = settings
        self._running = False
        # Maps account_id → list of consumer instances
        self._consumers: dict[str, list[Any]] = {}
        # Maps account_id → list of watchdog tasks
        self._watchdog_tasks: dict[str, list[asyncio.Task]] = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the manager (does not start per-account consumers yet)."""
        self._running = True
        logger.info("RealtimeConsumerManager started")

    async def stop(self) -> None:
        """Stop all running consumers gracefully."""
        self._running = False

        # Cancel all watchdog tasks first
        for account_id, tasks in list(self._watchdog_tasks.items()):
            for task in tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass

        # Stop all consumers
        for account_id, consumers in list(self._consumers.items()):
            for consumer in consumers:
                try:
                    await consumer.stop()
                except Exception as e:
                    logger.warning(f"Error stopping consumer for account {account_id}: {e}")

        self._consumers.clear()
        self._watchdog_tasks.clear()
        logger.info("RealtimeConsumerManager stopped — all consumers shut down")

    # ── Per-account consumer management ───────────────────────────────────────

    async def add_account_consumers(
        self,
        account_id: str,
        organization_id: str,
        provider: str,
        cloud_account_id: str,
        credentials: dict[str, Any],
        region: str = "us-east-1",
    ) -> int:
        """
        Start real-time consumers for a newly registered account.

        Returns the number of consumers successfully started.
        """
        if not self._settings.realtime_enabled:
            logger.debug(
                "Real-time consumers disabled (REALTIME_ENABLED=false). "
                "Set REALTIME_ENABLED=true to enable."
            )
            return 0

        if account_id in self._consumers:
            logger.debug(f"Consumers already running for account {account_id}")
            return len(self._consumers[account_id])

        consumers = []
        s = self._settings

        if provider == "aws" and s.aws_cloudtrail_sqs_queue_url:
            consumer = self._build_cloudtrail_consumer(
                organization_id=organization_id,
                account_id=cloud_account_id,
                credentials=credentials,
                region=region or s.aws_cloudtrail_region,
            )
            if consumer:
                consumers.append(consumer)

        elif provider == "azure" and s.azure_event_hub_connection_string:
            consumer = self._build_azure_consumer(
                organization_id=organization_id,
                subscription_id=cloud_account_id,
            )
            if consumer:
                consumers.append(consumer)

        elif provider == "gcp" and s.gcp_pubsub_subscription:
            consumer = self._build_gcp_consumer(
                organization_id=organization_id,
                project_id=cloud_account_id,
                credentials=credentials,
            )
            if consumer:
                consumers.append(consumer)

        elif provider == "oci" and s.oci_stream_ocid and s.oci_stream_endpoint:
            consumer = self._build_oci_consumer(
                organization_id=organization_id,
                tenancy_ocid=cloud_account_id,
                credentials=credentials,
                region=region,
            )
            if consumer:
                consumers.append(consumer)

        if not consumers:
            logger.debug(
                f"No real-time consumers configured for provider={provider} "
                f"account={account_id}. Check provider-specific env vars."
            )
            return 0

        # Start each consumer with a watchdog that restarts on failure
        started = 0
        watchdog_tasks = []
        for consumer in consumers:
            try:
                await consumer.start()
                task = asyncio.create_task(
                    self._watchdog(account_id, consumer),
                    name=f"consumer-watchdog-{account_id}",
                )
                watchdog_tasks.append(task)
                started += 1
                logger.info(
                    f"Started {type(consumer).__name__} for account {account_id} "
                    f"(provider={provider})"
                )
            except Exception as e:
                logger.error(
                    f"Failed to start {type(consumer).__name__} for account {account_id}: {e}"
                )

        if started:
            self._consumers[account_id] = consumers
            self._watchdog_tasks[account_id] = watchdog_tasks

        return started

    async def remove_account_consumers(self, account_id: str) -> None:
        """Stop and remove all consumers for a deleted/paused account."""
        # Cancel watchdog tasks
        for task in self._watchdog_tasks.pop(account_id, []):
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

        # Stop consumers
        for consumer in self._consumers.pop(account_id, []):
            try:
                await consumer.stop()
                logger.info(
                    f"Stopped {type(consumer).__name__} for account {account_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Error stopping consumer for account {account_id}: {e}"
                )

    def get_active_accounts(self) -> list[str]:
        """Return account IDs that have active real-time consumers."""
        return list(self._consumers.keys())

    # ── Watchdog ──────────────────────────────────────────────────────────────

    async def _watchdog(self, account_id: str, consumer: Any) -> None:
        """
        Monitor a consumer and restart it if it crashes.

        The watchdog runs as a background task.  When the consumer's internal
        loop exits unexpectedly (exception or clean exit while _running=True),
        the watchdog waits _RESTART_DELAY seconds and restarts it.
        """
        while self._running and account_id in self._consumers:
            await asyncio.sleep(_RESTART_DELAY)

            if not self._running or account_id not in self._consumers:
                break

            # Check if consumer is still alive by inspecting its _running flag
            consumer_running = getattr(consumer, "_running", False)
            if not consumer_running:
                logger.warning(
                    f"{type(consumer).__name__} for account {account_id} appears stopped. "
                    f"Restarting in {_RESTART_DELAY}s..."
                )
                try:
                    await consumer.start()
                    logger.info(
                        f"Restarted {type(consumer).__name__} for account {account_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to restart {type(consumer).__name__} "
                        f"for account {account_id}: {e}"
                    )

    # ── Consumer builders ─────────────────────────────────────────────────────

    def _build_cloudtrail_consumer(
        self,
        organization_id: str,
        account_id: str,
        credentials: dict[str, Any],
        region: str,
    ) -> Any | None:
        try:
            from .realtime_consumers import CloudTrailConsumer
            return CloudTrailConsumer(
                sqs_queue_url=self._settings.aws_cloudtrail_sqs_queue_url,
                event_producer=self._producer,
                credentials=credentials,
                organization_id=organization_id,
                account_id=account_id,
                region=region,
            )
        except Exception as e:
            logger.error(f"Failed to build CloudTrailConsumer: {e}")
            return None

    def _build_azure_consumer(
        self,
        organization_id: str,
        subscription_id: str,
    ) -> Any | None:
        try:
            from .realtime_consumers import AzureMonitorConsumer
            return AzureMonitorConsumer(
                event_hub_connection_string=self._settings.azure_event_hub_connection_string,
                event_hub_name=self._settings.azure_event_hub_name,
                event_producer=self._producer,
                organization_id=organization_id,
                subscription_id=subscription_id,
                consumer_group=self._settings.azure_event_hub_consumer_group,
            )
        except Exception as e:
            logger.error(f"Failed to build AzureMonitorConsumer: {e}")
            return None

    def _build_gcp_consumer(
        self,
        organization_id: str,
        project_id: str,
        credentials: dict[str, Any],
    ) -> Any | None:
        try:
            from .realtime_consumers import GCPAssetConsumer
            return GCPAssetConsumer(
                pubsub_subscription=self._settings.gcp_pubsub_subscription,
                event_producer=self._producer,
                credentials=credentials,
                organization_id=organization_id,
                project_id=project_id,
            )
        except Exception as e:
            logger.error(f"Failed to build GCPAssetConsumer: {e}")
            return None

    def _build_oci_consumer(
        self,
        organization_id: str,
        tenancy_ocid: str,
        credentials: dict[str, Any],
        region: str,
    ) -> Any | None:
        try:
            from .realtime_consumers import OCIEventsConsumer
            return OCIEventsConsumer(
                stream_ocid=self._settings.oci_stream_ocid,
                stream_endpoint=self._settings.oci_stream_endpoint,
                event_producer=self._producer,
                credentials=credentials,
                organization_id=organization_id,
                tenancy_ocid=tenancy_ocid,
                region=region,
            )
        except Exception as e:
            logger.error(f"Failed to build OCIEventsConsumer: {e}")
            return None
