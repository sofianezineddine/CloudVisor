"""Database models for the Copilot service."""

from .query_log import Base, CopilotQueryModel
from .chat_session import ChatSessionModel

__all__ = ["Base", "CopilotQueryModel", "ChatSessionModel"]
