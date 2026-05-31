"""
NVIDIA NIM Provider Implementation
NVIDIA NIM (NVIDIA Inference Microservices) provides optimized LLM inference
"""
from typing import AsyncGenerator

import httpx
from openai import AsyncOpenAI

from app.providers.base import (
    BaseLLMProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
)


class NVIDIAProvider(BaseLLMProvider):
    """NVIDIA NIM API provider."""
    
    @property
    def name(self) -> str:
        return "nvidia"
    
    async def initialize(self):
        """Initialize NVIDIA NIM client (OpenAI-compatible)."""
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=httpx.Timeout(60.0),
        )
    
    async def chat_completion(
        self, 
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Send chat completion request to NVIDIA NIM."""
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
        """Stream chat completion from NVIDIA NIM."""
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
        """List available NVIDIA NIM models."""
        return [
            "meta/llama-3.1-405b-instruct",
            "meta/llama-3.1-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "mistralai/mistral-large",
            "mistralai/mixtral-8x22b-instruct",
            "google/gemma-2-27b-it",
            "google/gemma-2-9b-it",
            "nvidia/nemotron-4-340b-instruct",
        ]
    
    async def health_check(self) -> bool:
        """Check NVIDIA NIM API health."""
        try:
            if not self._client:
                await self.initialize()
            # Try to get models list
            await self._client.models.list()
            return True
        except Exception:
            return False
