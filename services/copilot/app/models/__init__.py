"""Database models for the Copilot service."""

from .query_log import Base, CopilotQueryModel

__all__ = ["Base", "CopilotQueryModel"]
