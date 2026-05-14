"""Async Neo4j graph client wrapper for CSPM service.

Communicates with the Graph Service (cv-graph) via HTTP to execute
Cypher queries, create nodes, and create relationships in the Neo4j
asset graph.
"""

import logging
from typing import Any

import httpx

from .config import get_cspm_settings

logger = logging.getLogger(__name__)


class GraphClientError(Exception):
    """Raised when a graph operation fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GraphClient:
    """Async HTTP client for the Neo4j-backed Graph Service."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        settings = get_cspm_settings()
        self._base_url = (base_url or settings.graph_service_url).rstrip("/")
        self._timeout = timeout or settings.graph_query_timeout

    async def query(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return the result records.

        Args:
            cypher: The Cypher query string.
            parameters: Optional dict of query parameters.

        Returns:
            List of record dicts from the graph service.

        Raises:
            GraphClientError: If the request fails or returns a non-2xx status.
        """
        payload: dict[str, Any] = {"query": cypher}
        if parameters:
            payload["parameters"] = parameters

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/graph/query",
                    json=payload,
                )
                if resp.status_code >= 400:
                    detail = resp.text[:500]
                    logger.error(
                        "Graph query failed [%d]: %s", resp.status_code, detail
                    )
                    raise GraphClientError(
                        f"Graph query failed: {detail}",
                        status_code=resp.status_code,
                    )
                data = resp.json()
                return data.get("records", data.get("results", []))
        except httpx.HTTPError as exc:
            logger.error("Graph service connection error: %s", exc)
            raise GraphClientError(f"Graph service unavailable: {exc}") from exc

    async def create_node(
        self,
        labels: list[str],
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a node in the graph with the given labels and properties.

        Args:
            labels: List of node labels (e.g. ["IAMIdentity", "Resource"]).
            properties: Dict of node properties.

        Returns:
            The created node data from the graph service.

        Raises:
            GraphClientError: If the request fails.
        """
        payload = {
            "labels": labels,
            "properties": properties,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/graph/nodes",
                    json=payload,
                )
                if resp.status_code >= 400:
                    detail = resp.text[:500]
                    logger.error(
                        "Graph create_node failed [%d]: %s", resp.status_code, detail
                    )
                    raise GraphClientError(
                        f"Failed to create node: {detail}",
                        status_code=resp.status_code,
                    )
                return resp.json()
        except httpx.HTTPError as exc:
            logger.error("Graph service connection error: %s", exc)
            raise GraphClientError(f"Graph service unavailable: {exc}") from exc

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a relationship between two nodes in the graph.

        Args:
            source_id: The ID of the source node.
            target_id: The ID of the target node.
            relationship_type: The relationship type (e.g. "HAS_PERMISSION", "TRUSTS").
            properties: Optional dict of relationship properties.

        Returns:
            The created relationship data from the graph service.

        Raises:
            GraphClientError: If the request fails.
        """
        payload: dict[str, Any] = {
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": relationship_type,
        }
        if properties:
            payload["properties"] = properties

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/graph/relationships",
                    json=payload,
                )
                if resp.status_code >= 400:
                    detail = resp.text[:500]
                    logger.error(
                        "Graph create_relationship failed [%d]: %s",
                        resp.status_code,
                        detail,
                    )
                    raise GraphClientError(
                        f"Failed to create relationship: {detail}",
                        status_code=resp.status_code,
                    )
                return resp.json()
        except httpx.HTTPError as exc:
            logger.error("Graph service connection error: %s", exc)
            raise GraphClientError(f"Graph service unavailable: {exc}") from exc
