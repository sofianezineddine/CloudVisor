"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class AssetResponse(BaseModel):
    """Asset node response."""

    id: str
    cloud_resource_id: str
    provider: str
    account_id: str
    region: str
    resource_type: str
    name: str
    tags: dict[str, str]
    environment: str
    is_public: bool
    risk_score: int
    open_findings_count: int
    last_seen_at: datetime


class AssetListResponse(BaseModel):
    """List of assets."""

    assets: list[AssetResponse]
    total: int
    page: int
    page_size: int


class RelatedAssetResponse(BaseModel):
    """Related asset in graph."""

    id: str
    name: str
    resource_type: str
    relationship_type: str
    risk_score: int


class AssetRelatedResponse(BaseModel):
    """Related assets for an asset."""

    asset_id: str
    relationships: list[RelatedAssetResponse]


class AssetHistoryResponse(BaseModel):
    """Asset history response."""

    asset_id: str
    snapshots: list[dict[str, Any]]
    total: int


class AssetFindingsResponse(BaseModel):
    """Asset findings response."""

    asset_id: str
    findings: list[dict[str, Any]]
    total: int


class AttackPathResponse(BaseModel):
    """Attack path response."""

    paths: list[list[dict[str, Any]]]
    total: int


class AssetSearchRequest(BaseModel):
    """Asset search request."""

    query: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    sort: list[dict[str, Any]] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class GraphStatsResponse(BaseModel):
    """Graph statistics response."""

    node_count: int
    edge_count: int
    by_provider: dict[str, int]
    by_type: dict[str, int]


class CypherQueryRequest(BaseModel):
    """Cypher query request."""

    query: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class CypherQueryResponse(BaseModel):
    """Cypher query response."""

    results: list[dict[str, Any]]
    columns: list[str]


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
