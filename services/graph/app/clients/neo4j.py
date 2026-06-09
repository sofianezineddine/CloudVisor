"""Neo4j async client for graph database operations."""

import logging
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Async Neo4j client for graph operations."""

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
        max_connection_lifetime: int = 3600,
        max_connection_pool_size: int = 50,
    ):
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._max_connection_lifetime = max_connection_lifetime
        self._max_connection_pool_size = max_connection_pool_size
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Initialize async Neo4j driver."""
        try:
            self._driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
                max_connection_lifetime=self._max_connection_lifetime,
                max_connection_pool_size=self._max_connection_pool_size,
            )
            await self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self._uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Neo4j driver."""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results as dicts."""
        if not self._driver:
            raise RuntimeError("Neo4j client not connected")

        async with self._driver.session(database=database or self._database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """Execute a write query."""
        if not self._driver:
            raise RuntimeError("Neo4j client not connected")

        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, parameters or {})
            await result.consume()

    async def create_node(self, label: str, properties: dict[str, Any]) -> dict[str, Any]:
        query = f"CREATE (n:{label} $props) RETURN n"
        result = await self.execute_query(query, {"props": properties})
        return result[0]["n"] if result else {}

    async def update_node(self, node_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        query = "MATCH (n {id: $node_id}) SET n += $props RETURN n"
        result = await self.execute_query(query, {"node_id": node_id, "props": properties})
        return result[0]["n"] if result else {}

    async def delete_node(self, node_id: str) -> bool:
        query = "MATCH (n {id: $node_id}) DETACH DELETE n"
        await self.execute_write(query, {"node_id": node_id})
        return True

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query = f"""
        MATCH (a {{id: $source_id}})
        MATCH (b {{id: $target_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $props
        RETURN a, r, b
        """
        result = await self.execute_query(
            query, {"source_id": source_id, "target_id": target_id, "props": properties or {}}
        )
        return result[0] if result else {}

    async def get_node(self, node_id: str) -> dict[str, Any] | None:
        query = "MATCH (n {id: $node_id}) RETURN n"
        result = await self.execute_query(query, {"node_id": node_id})
        return result[0]["n"] if result else None

    async def get_node_relationships(
        self, node_id: str, direction: str = "both", depth: int = 1
    ) -> list[dict[str, Any]]:
        if direction == "outgoing":
            query = "MATCH (n {id: $node_id})-[r]->(related) RETURN n, r, related LIMIT 100"
        elif direction == "incoming":
            query = "MATCH (related)-[r]->(n {id: $node_id}) RETURN related, r, n LIMIT 100"
        else:
            query = "MATCH (n {id: $node_id})-[r]-(related) RETURN n, r, related LIMIT 100"
        return await self.execute_query(query, {"node_id": node_id})

    async def find_paths(
        self, start_id: str, end_id: str, max_depth: int = 6
    ) -> list[list[dict[str, Any]]]:
        query = f"""
        MATCH path = (start {{id: $start_id}})-[*1..{max_depth}]->(end {{id: $end_id}})
        RETURN path, length(path) as pathLength
        ORDER BY pathLength ASC LIMIT 10
        """
        result = await self.execute_query(query, {"start_id": start_id, "end_id": end_id})
        return [r.get("path", []) for r in result]

    async def get_stats(self) -> dict[str, Any]:
        nodes = await self.execute_query("MATCH (n) RETURN count(n) as count")
        edges = await self.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
        return {
            "node_count": nodes[0]["count"] if nodes else 0,
            "edge_count": edges[0]["count"] if edges else 0,
        }

    async def create_constraints(self) -> None:
        """Create indexes and constraints for the asset graph."""
        constraints = [
            "CREATE CONSTRAINT asset_id_unique IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE",
            "CREATE INDEX asset_provider IF NOT EXISTS FOR (a:Asset) ON (a.provider)",
            "CREATE INDEX asset_account IF NOT EXISTS FOR (a:Asset) ON (a.account_id)",
            "CREATE INDEX asset_type IF NOT EXISTS FOR (a:Asset) ON (a.resource_type)",
            "CREATE INDEX asset_org IF NOT EXISTS FOR (a:Asset) ON (a.organization_id)",
            "CREATE INDEX asset_environment IF NOT EXISTS FOR (a:Asset) ON (a.environment)",
        ]
        for constraint in constraints:
            try:
                await self.execute_write(constraint)
            except Exception as e:
                logger.debug(f"Constraint: {e}")


class GraphTransaction:
    """Context manager for Neo4j transactions."""

    def __init__(self, client: Neo4jClient):
        self._client = client
        self._session = None

    async def __aenter__(self):
        if not self._client._driver:
            raise RuntimeError("Neo4j client not connected")
        self._session = self._client._driver.session(database=self._client._database)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def run(self, query: str, parameters: dict[str, Any] | None = None):
        if not self._session:
            raise RuntimeError("No active session")
        result = await self._session.run(query, parameters or {})
        return await result.data()
