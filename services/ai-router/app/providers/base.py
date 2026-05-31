"""
Base LLM Provider Interface

Defines the contract that all LLM providers must implement.
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

from pydantic import BaseModel


class Message(BaseModel):
    """Chat message structure."""
    role: str  # system, user, assistant
    content: str


class ChatCompletionRequest(BaseModel):
    """Standardized chat completion request."""
    model: str
    messages: list[Message]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None


class ChatCompletionResponse(BaseModel):
    """Standardized chat completion response."""
    id: str
    model: str
    content: str
    usage: dict
    finish_reason: Optional[str] = None


class ProviderInfo(BaseModel):
    """Provider metadata."""
    name: str
    available_models: list[str]
    is_available: bool


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str, base_url: str, default_model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
        self._client = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @abstractmethod
    async def initialize(self):
        """Initialize the provider client."""
        pass
    
    @abstractmethod
    async def chat_completion(
        self, 
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Send a chat completion request."""
        pass
    
    @abstractmethod
    async def chat_completion_stream(
        self, 
        request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion response."""
        pass
    
    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        pass
    
    def get_model(self, model: Optional[str] = None) -> str:
        """Get model name, falling back to default if not specified."""
        return model or self.default_model
