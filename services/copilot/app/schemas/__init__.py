"""Pydantic schemas for the Copilot service."""

from .request import CopilotQueryRequest, QueryContext
from .response import (
    CopilotQueryResponse,
    Citation,
    SuggestedAction,
    IntentType,
)

__all__ = [
    "CopilotQueryRequest",
    "QueryContext",
    "CopilotQueryResponse",
    "Citation",
    "SuggestedAction",
    "IntentType",
]
