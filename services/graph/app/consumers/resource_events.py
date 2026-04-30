"""Kafka consumers for processing resource events from the Connector service."""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)


class ResourceEventConsumer:
    """Consumes resource.discovered/updated/deleted events and writes to Neo4j."""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str = "cloudvisor-graph",
        graph_service: Any = None,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._graph_service = graph_service
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            "resource.discovered",
            "resource.updated",
            "resource.deleted",
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        logger.info("Resource event consumer started")

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
        logger.info("Resource event consumer stopped")

    async def run(self) -> None:
        if not self._consumer:
            return
        try:
            async for message in self._consumer:
                if not self._running:
                    break
                try:
                    await self._process_message(message)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        except Exception as e:
            logger.error(f"Consumer error: {e}")

    async def _process_message(self, message: Any) -> None:
        value = message.value
        if not self._graph_service:
            return

        event_type = value.get("event_type", "")

        # Record metric
        try:
            from app.metrics.prometheus import GraphMetrics
            GraphMetrics.record_event_consumed(event_type)
        except Exception:
            pass

        if event_type == "resource.discovered":
            await self._handle_discovered(value)
        elif event_type == "resource.updated":
            await self._handle_updated(value)
        elif event_type == "resource.deleted":
            await self._handle_deleted(value)

    async def _handle_discovered(self, event: dict[str, Any]) -> None:
        from app.services.graph_service import AssetNode

        asset = AssetNode(
            id=event.get("cloud_resource_id", str(uuid.uuid4())),
            cloud_resource_id=event.get("cloud_resource_id", ""),
            provider=event.get("provider", ""),
            account_id=event.get("account_id", ""),
            region=event.get("region", "global"),
            resource_type=event.get("resource_type", ""),
            name=event.get("name", ""),
            tags=event.get("tags", {}),
            raw=event.get("raw", {}),
            organization_id=event.get("organization_id", ""),
            is_public=event.get("is_public", False),
            environment=event.get("environment", "unknown"),
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
        )
        await self._graph_service.create_asset_node(asset)
        logger.debug(f"Created asset node: {asset.id}")

    async def _handle_updated(self, event: dict[str, Any]) -> None:
        from app.services.graph_service import AssetNode

        asset = AssetNode(
            id=event.get("cloud_resource_id", str(uuid.uuid4())),
            cloud_resource_id=event.get("cloud_resource_id", ""),
            provider=event.get("provider", ""),
            account_id=event.get("account_id", ""),
            region=event.get("region", "global"),
            resource_type=event.get("resource_type", ""),
            name=event.get("name", ""),
            tags=event.get("tags", {}),
            raw=event.get("raw", {}),
            organization_id=event.get("organization_id", ""),
            is_public=event.get("is_public", False),
            environment=event.get("environment", "unknown"),
            last_seen_at=datetime.utcnow(),
        )
        await self._graph_service.update_asset_node(asset)
        await self._graph_service.compute_and_update_risk_score(asset.id)
        logger.debug(f"Updated asset node: {asset.id}")

    async def _handle_deleted(self, event: dict[str, Any]) -> None:
        cloud_resource_id = event.get("cloud_resource_id")
        if cloud_resource_id:
            await self._graph_service.delete_asset_node(cloud_resource_id)
            logger.debug(f"Deleted asset node: {cloud_resource_id}")


class FindingEventConsumer:
    """Consumes finding events to update asset risk scores in Neo4j."""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str = "cloudvisor-graph-findings",
        graph_service: Any = None,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._graph_service = graph_service
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            "finding.created",
            "finding.resolved",
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
        )
        await self._consumer.start()
        self._running = True
        logger.info("Finding event consumer started")

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()

    async def run(self) -> None:
        if not self._consumer:
            return
        try:
            async for message in self._consumer:
                if not self._running:
                    break
                await self._process_message(message)
        except Exception as e:
            logger.error(f"Finding consumer error: {e}")

    async def _process_message(self, message: Any) -> None:
        if not self._graph_service:
            return
        event = message.value
        event_type = event.get("event_type", "")
        resource_id = event.get("resource_id")
        if not resource_id:
            return

        delta = 1 if event_type == "finding.created" else -1
        query = """
        MATCH (a:Asset {cloud_resource_id: $resource_id})
        SET a.open_findings_count = coalesce(a.open_findings_count, 0) + $delta
        RETURN a
        """
        try:
            await self._graph_service._neo4j.execute_write(
                query, {"resource_id": resource_id, "delta": delta}
            )
            await self._graph_service.compute_and_update_risk_score(resource_id)
        except Exception as e:
            logger.error(f"Failed to update findings for {resource_id}: {e}")
