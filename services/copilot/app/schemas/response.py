"""Pydantic response schemas for Copilot service."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Query intent classification."""

    GREETING = "GREETING"
    POSTURE = "POSTURE"
    FINDING = "FINDING"
    COMPLIANCE = "COMPLIANCE"
    REMEDIATION = "REMEDIATION"
    THREAT = "THREAT"
    DRIFT = "DRIFT"
    GENERAL = "GENERAL"


class Citation(BaseModel):
    """Citation for a claim in the response."""

    source: str = Field(..., description="Data source name (e.g., 'findings', 'asset_graph')")
    reference: str = Field(..., description="Specific reference (e.g., finding ID, asset ARN)")
    claim: str = Field(..., description="The specific claim this citation supports")


class SuggestedAction(BaseModel):
    """Suggested action the user can take."""

    label: str = Field(..., description="Action button label")
    action: str = Field(
        ..., description="Action type: 'navigate', 'remediation', 'export', 'investigate'"
    )
    target: str | None = Field(default=None, description="Target URL or resource ID")
    finding_id: str | None = Field(default=None, description="Related finding ID")
    asset_id: str | None = Field(default=None, description="Related asset ID")


class CopilotQueryResponse(BaseModel):
    """Response schema for copilot query."""

    query_id: str = Field(..., description="Unique query identifier for audit trail")

    answer: str = Field(..., description="Natural language answer grounded in actual data")

    intent: IntentType = Field(..., description="Detected query intent")

    citations: list[Citation] = Field(
        default_factory=list, description="Citations for claims in the answer"
    )

    suggested_actions: list[SuggestedAction] = Field(
        default_factory=list, description="Suggested next actions for the user"
    )

    data_freshness: datetime = Field(
        ..., description="Timestamp of the most recent data used in the response"
    )

    processing_ms: int = Field(..., description="Total processing time in milliseconds")

    data_sources_used: list[str] = Field(
        default_factory=list, description="List of data sources queried"
    )

    session_id: str | None = Field(
        default=None, description="Session ID this query was saved to"
    )


class StreamChunk(BaseModel):
    """Streaming response chunk."""

    type: str = Field(..., description="Chunk type: 'token', 'citation', 'action', 'done'")
    content: str | dict = Field(..., description="Chunk content")
