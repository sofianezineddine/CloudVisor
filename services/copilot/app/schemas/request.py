"""Pydantic request schemas for Copilot service."""

from pydantic import BaseModel, Field
from typing import Any


class QueryContext(BaseModel):
    """Optional context to pre-load into the query."""

    finding_id: str | None = Field(
        default=None, description="Pre-load a specific finding into context"
    )
    asset_id: str | None = Field(
        default=None, description="Pre-load a specific asset into context"
    )


class ScopeAccount(BaseModel):
    """A single cloud account in the user's scope."""
    account_id: str
    provider: str
    name: str
    resource_count: int = 0
    critical_count: int = 0
    posture_score: float = 0


class ScopeContext(BaseModel):
    """The active scope the user is viewing in the UI."""
    mode: str = Field(default="provider", description="'provider' or 'account'")
    provider: str = Field(default="aws", description="Active cloud provider")
    label: str = Field(default="", description="Human-readable scope label")
    account_ids: list[str] = Field(default_factory=list)
    accounts: list[ScopeAccount] = Field(default_factory=list)


class UIContext(BaseModel):
    """Full read-only UI context snapshot sent from the frontend."""
    current_page: str = Field(default="", description="Human-readable page name")
    current_path: str = Field(default="", description="URL path the user is on")
    scope: ScopeContext = Field(default_factory=ScopeContext)
    all_accounts: list[ScopeAccount] = Field(default_factory=list)


class ConversationMessage(BaseModel):
    """A single message in the conversation history."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class CopilotQueryRequest(BaseModel):
    """Request schema for copilot query."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Natural language question about cloud security",
        examples=["Which production workloads have critical CVEs and are internet-facing?"],
    )

    context: QueryContext | None = Field(
        default=None, description="Optional context to pre-load a specific finding/asset"
    )

    ui_context: UIContext | None = Field(
        default=None, description="Read-only UI context: current page, scope, accounts"
    )

    conversation_history: list[ConversationMessage] = Field(
        default_factory=list,
        description="Previous messages in the conversation for multi-turn awareness",
    )

    stream: bool = Field(
        default=False,
        description="If true, returns Server-Sent Events (SSE) streaming response",
    )

    session_id: str | None = Field(
        default=None,
        description="Session ID to group this message with an existing conversation. If None, a new session is created.",
    )
