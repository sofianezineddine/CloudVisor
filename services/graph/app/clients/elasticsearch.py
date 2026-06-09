"""Elasticsearch client for full-text search."""

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """Async Elasticsearch client for search operations."""

    def __init__(
        self,
        url: str = "http://localhost:9200",
        index_prefix: str = "cloudvisor",
        username: str = "",
        password: str = "",
    ):
        self._url = url
        self._index_prefix = index_prefix
        self._username = username
        self._password = password
        self._client: AsyncElasticsearch | None = None

    async def connect(self) -> None:
        """Initialize Elasticsearch client — compatible with ES 8.x."""
        try:
            kwargs: dict = dict(
                hosts=[self._url],
                verify_certs=False,
                ssl_show_warn=False,
            )
            if self._username and self._password:
                kwargs["http_auth"] = (self._username, self._password)
            self._client = AsyncElasticsearch(**kwargs)
            await self._client.info()
            logger.info(f"Connected to Elasticsearch at {self._url}")
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Elasticsearch client."""
        if self._client:
            await self._client.close()
            self._client = None

    def _get_index_name(self, index_type: str) -> str:
        """Get the index name for a given type."""
        return f"{self._index_prefix}-{index_type}"

    async def create_index(
        self,
        index_type: str,
        mappings: dict[str, Any],
    ) -> None:
        """Create an index with mappings."""
        if not self._client:
            raise RuntimeError("Elasticsearch client not connected")

        index_name = self._get_index_name(index_type)

        try:
            if not await self._client.indices.exists(index=index_name):
                await self._client.indices.create(
                    index=index_name,
                    mappings=mappings,
                    settings={
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                    },
                )
                logger.info(f"Created index: {index_name}")
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            raise

    async def index_document(
        self,
        index_type: str,
        document_id: str,
        document: dict[str, Any],
    ) -> None:
        """Index a single document."""
        if not self._client:
            raise RuntimeError("Elasticsearch client not connected")

        index_name = self._get_index_name(index_type)

        await self._client.index(
            index=index_name,
            id=document_id,
            document=document,
        )

    async def bulk_index(
        self,
        index_type: str,
        documents: list[tuple[str, dict[str, Any]]],
    ) -> None:
        """Bulk index multiple documents."""
        if not self._client:
            raise RuntimeError("Elasticsearch client not connected")

        index_name = self._get_index_name(index_type)

        operations = []
        for doc_id, doc in documents:
            operations.append({"index": {"_index": index_name, "_id": doc_id}})
            operations.append(doc)

        if operations:
            await self._client.bulk(operations=operations, refresh=True)

    async def delete_document(self, index_type: str, document_id: str) -> None:
        """Delete a document."""
        if not self._client:
            raise RuntimeError("Elasticsearch client not connected")

        index_name = self._get_index_name(index_type)

        try:
            await self._client.delete(index=index_name, id=document_id)
        except Exception as e:
            logger.debug(f"Failed to delete document {document_id}: {e}")

    async def search(
        self,
        index_type: str,
        query: dict[str, Any],
        size: int = 100,
        from_: int = 0,
    ) -> dict[str, Any]:
        """Search documents."""
        if not self._client:
            raise RuntimeError("Elasticsearch client not connected")

        index_name = self._get_index_name(index_type)

        result = await self._client.search(
            index=index_name,
            query=query,
            size=size,
            from_=from_,
        )

        return {
            "total": result["hits"]["total"]["value"],
            "hits": [hit["_source"] for hit in result["hits"]["hits"]],
        }

    async def full_text_search(
        self,
        index_type: str,
        search_term: str,
        fields: list[str] | None = None,
        size: int = 100,
    ) -> dict[str, Any]:
        """Full-text search across specified fields."""
        if not self._client:
            raise RuntimeError("Elasticsearch client not connected")

        if fields is None:
            fields = ["name", "resource_type", "tags.*"]

        should_clauses = []
        for field in fields:
            should_clauses.append({"match": {field: {"query": search_term, "fuzziness": "AUTO"}}})

        query = {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1,
            }
        }

        return await self.search(index_type, query, size)

    async def advanced_search(
        self,
        index_type: str,
        filters: dict[str, Any],
        sort: list[dict[str, Any]] | None = None,
        size: int = 100,
        from_: int = 0,
    ) -> dict[str, Any]:
        """Advanced search with filters and sorting."""
        if not self._client:
            raise RuntimeError("Elasticsearch client not connected")

        must_clauses = []
        for field, value in filters.items():
            if isinstance(value, list):
                must_clauses.append({"terms": {field: value}})
            else:
                must_clauses.append({"term": {field: value}})

        query = {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}

        index_name = self._get_index_name(index_type)

        result = await self._client.search(
            index=index_name,
            query=query,
            sort=sort,
            size=size,
            from_=from_,
        )

        return {
            "total": result["hits"]["total"]["value"],
            "hits": [hit["_source"] for hit in result["hits"]["hits"]],
        }

    async def get_stats(self) -> dict[str, Any]:
        """Get Elasticsearch cluster stats."""
        if not self._client:
            raise RuntimeError("Elasticsearch client not connected")

        return await self._client.cluster.stats()


ASSET_MAPPINGS = {
    "properties": {
        "id": {"type": "keyword"},
        "cloud_resource_id": {"type": "keyword"},
        "provider": {"type": "keyword"},
        "account_id": {"type": "keyword"},
        "region": {"type": "keyword"},
        "resource_type": {"type": "keyword"},
        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "organization_id": {"type": "keyword"},
        "tags": {"type": "object", "enabled": True},
        "environment": {"type": "keyword"},
        "is_public": {"type": "boolean"},
        "risk_score": {"type": "integer"},
        "open_findings_count": {"type": "integer"},
        "last_seen_at": {"type": "date"},
    }
}
