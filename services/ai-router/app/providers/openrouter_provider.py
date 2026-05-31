"""
OpenRouter Provider Implementation
OpenRouter provides unified access to many LLMs through OpenAI-compatible API
"""
from typing import AsyncGenerator

import httpx
from openai import AsyncOpenAI

from app.providers.base import (
    BaseLLMProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
)


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter API provider - access to many models via unified API."""
    
    @property
    def name(self) -> str:
        return "openrouter"
    
    async def initialize(self):
        """Initialize OpenRouter client (OpenAI-compatible)."""
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=httpx.Timeout(60.0),
            default_headers={
                "HTTP-Referer": "https://cloudvisor.ai",
                "X-Title": "CloudVisor AI Router",
            },
        )
    
    async def chat_completion(
        self, 
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Send chat completion request to OpenRouter."""
        if not self._client:
            await self.initialize()
        
        model = self.get_model(request.model)
        
        response = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
            extra_body={
                "transforms": ["middle-out"],  # OpenRouter optimization
            } if "transformers" in model else None,
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
        """Stream chat completion from OpenRouter."""
        if not self._client:
            await self.initialize()
        
        model = self.get_model(request.model)
        
        stream = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
            extra_body={
                "transforms": ["middle-out"],
            } if "transformers" in model else None,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def list_models(self) -> list[str]:
        """List popular OpenRouter models."""
        return [
            "meta-llama/llama-3.3-70b-instruct:free",
            "meta-llama/llama-3.1-405b-instruct",
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus",
            "google/gemini-pro-1.5",
            "mistralai/mistral-large",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "deepseek/deepseek-chat",
        ]
    
    async def health_check(self) -> bool:
        """Check OpenRouter API health."""
        try:
            if not self._client:
                await self.initialize()
            # Try to get models list
            await self._client.models.list()
            return True
        except Exception:
            return False
