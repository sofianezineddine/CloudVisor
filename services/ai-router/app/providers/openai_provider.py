"""
OpenAI Provider Implementation
Supports both native OpenAI and OpenAI-compatible APIs (OpenRouter, etc.)
"""
from typing import AsyncGenerator

import httpx
from openai import AsyncOpenAI

from app.providers.base import (
    BaseLLMProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""
    
    @property
    def name(self) -> str:
        return "openai"
    
    async def initialize(self):
        """Initialize OpenAI client."""
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=httpx.Timeout(60.0),
        )
    
    async def chat_completion(
        self, 
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Send chat completion request to OpenAI."""
        if not self._client:
            await self.initialize()
        
        model = self.get_model(request.model)
        
        response = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
            top_p=request.top_p,
            presence_penalty=request.presence_penalty,
            frequency_penalty=request.frequency_penalty,
        )
        
        return ChatCompletionResponse(
            id=response.id,
            model=response.model or model,
            content=response.choices[0].message.content or "",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            finish_reason=response.choices[0].finish_reason,
        )
    
    async def chat_completion_stream(
        self, 
        request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from OpenAI."""
        if not self._client:
            await self.initialize()
        
        model = self.get_model(request.model)
        
        stream = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
            top_p=request.top_p,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def list_models(self) -> list[str]:
        """List available OpenAI models."""
        # OpenAI model list - in production, this could be fetched from API
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ]
    
    async def health_check(self) -> bool:
        """Check OpenAI API health."""
        try:
            if not self._client:
                await self.initialize()
            # Try a simple models list call
            await self._client.models.list()
            return True
        except Exception:
            return False
