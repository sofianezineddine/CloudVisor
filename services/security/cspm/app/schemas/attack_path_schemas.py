"""Pydantic schemas for Attack Path Engine endpoints."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


# ─── Request Schemas ───────────────────────────────────────────────────────────


class AttackPathAnalyzeRequest(BaseModel):
    """Request body for POST /api/v1/cspm/attack-paths/analyze."""

    account_id: Optional[str] = None
    max_hops: int = 6
    include_lateral_movement: bool = True


# ─── Response Schemas ──────────────────────────────────────────────────────────


class AttackPathOut(BaseModel):
    """Response schema for a single attack path."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    entry_resource_id: str
    target_resource_id: str
    path_hops: int
    path_nodes: List[str] = []
    path_edges: List[Any] = []
    severity: str
    mitre_technique_id: Optional[str] = None
    mitre_technique_name: Optional[str] = None
    is_lateral_movement: bool = False
    blast_radius_count: int = 0
    discovered_at: Optional[datetime] = None


class AttackPathListOut(BaseModel):
    """Paginated list response for attack paths."""

    items: List[AttackPathOut]
    total: int = 0
    page: int = 1
    page_size: int = 20


class BlastRadiusOut(BaseModel):
    """Response schema for blast radius computation."""

    resource_id: str
    blast_radius_count: int = 0
    reachable_resources: List[str] = []
    reachable_resource_types: List[str] = []


class ToxicCombinationOut(BaseModel):
    """Response schema for a toxic combination finding."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    pattern_id: str
    resource_id: str
    component_finding_ids: List[str] = []
    component_details: List[Any] = []
    elevated_severity: str
    description: Optional[str] = None
    detected_at: Optional[datetime] = None
