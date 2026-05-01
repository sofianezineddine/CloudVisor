"""Multi-provider LLM client for CloudVisor Q (Ollama, Google Gemini, OpenAI)."""

import logging
from typing import AsyncGenerator
from abc import ABC, abstractmethod

from ..core.config import CopilotSettings

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Base class for LLM clients."""

    def __init__(self, settings: CopilotSettings):
        self.settings = settings

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate a response from the LLM."""
        pass


class OllamaClient(BaseLLMClient):
    """Ollama client for local LLM inference."""

    def __init__(self, settings: CopilotSettings):
        super().__init__(settings)
        import httpx
        self.client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout,
        )
        self.model_name = settings.ollama_model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate a response from Ollama."""
        try:
            if stream:
                return self._generate_stream(system_prompt, user_prompt)
            else:
                return await self._generate_complete(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise

    async def _generate_complete(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a complete (non-streaming) response using /api/chat."""
        logger.info(f"Calling Ollama API (model: {self.model_name}, non-streaming)")

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self.settings.temperature,
                "num_predict": self.settings.max_tokens,
                # Prevent repetition loops — critical for small models listing many items
                "repeat_penalty": 1.3,
                "repeat_last_n": 64,
                # Stop tokens to prevent runaway generation
                "stop": ["\n\n\n", "---", "==="],
            },
        }

        response = await self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        content = data.get("message", {}).get("content", "")
        if not content:
            logger.warning("Ollama returned empty content, trying legacy /api/generate")
            content = await self._generate_legacy(system_prompt, user_prompt)

        logger.info(f"Ollama response received: {len(content)} chars")
        return content

    async def _generate_legacy(self, system_prompt: str, user_prompt: str) -> str:
        """Fallback to legacy /api/generate endpoint."""
        payload = {
            "model": self.model_name,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
            "options": {
                "temperature": self.settings.temperature,
                "num_predict": self.settings.max_tokens,
            },
        }
        response = await self.client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")

    async def _generate_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using /api/chat."""
        logger.info(f"Calling Ollama API (model: {self.model_name}, streaming)")

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
            "options": {
                "temperature": self.settings.temperature,
                "num_predict": self.settings.max_tokens,
            },
        }

        async with self.client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    import json
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

        logger.info("Ollama streaming response completed")

    async def embed(self, text: str) -> list[float]:
        """Generate embeddings using Ollama."""
        logger.info(f"Generating embeddings with Ollama (model: {self.settings.ollama_embedding_model})")

        payload = {
            "model": self.settings.ollama_embedding_model,
            "prompt": text,
        }

        response = await self.client.post("/api/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()

        return data.get("embedding", [])


class GeminiClient(BaseLLMClient):
    """Wrapper for Google Gemini API with streaming support."""

    def __init__(self, settings: CopilotSettings):
        super().__init__(settings)
        from google import genai
        from google.genai import types
        self.genai = genai
        self.types = types
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model_name = settings.google_model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate a response from Gemini."""
        try:
            if stream:
                return self._generate_stream(system_prompt, user_prompt)
            else:
                return await self._generate_complete(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    async def _generate_complete(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a complete (non-streaming) response."""
        logger.info(f"Calling Gemini API (model: {self.model_name}, non-streaming)")

        config = self.types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=self.settings.google_max_tokens,
            temperature=self.settings.google_temperature,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=config,
        )

        content = response.text if response.text else ""

        logger.info(
            f"Gemini response received: {len(content)} chars, "
            f"tokens: {response.usage_metadata.prompt_token_count} in / "
            f"{response.usage_metadata.candidates_token_count} out"
        )

        return content

    async def _generate_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        logger.info(f"Calling Gemini API (model: {self.model_name}, streaming)")

        config = self.types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=self.settings.google_max_tokens,
            temperature=self.settings.google_temperature,
        )

        async for chunk in await self.client.aio.models.generate_content_stream(
            model=self.model_name,
            contents=user_prompt,
            config=config,
        ):
            if chunk.text:
                yield chunk.text

        logger.info("Gemini streaming response completed")


class OpenRouterClient(BaseLLMClient):
    """OpenRouter client using OpenAI-compatible API."""

    def __init__(self, settings: CopilotSettings):
        super().__init__(settings)
        import httpx
        
        # Build headers - strip API key to remove any whitespace
        api_key = settings.openrouter_api_key.strip() if settings.openrouter_api_key else ""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # Add optional headers if configured
        if settings.openrouter_site_url:
            headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_name:
            headers["X-Title"] = settings.openrouter_app_name
        
        self.client = httpx.AsyncClient(
            base_url=settings.openrouter_base_url,
            headers=headers,
            timeout=120.0,
        )
        self.model_name = settings.openrouter_model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate a response from OpenRouter."""
        try:
            if stream:
                return self._generate_stream(system_prompt, user_prompt)
            else:
                return await self._generate_complete(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            raise

    async def _generate_complete(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a complete (non-streaming) response."""
        logger.info(f"Calling OpenRouter API (model: {self.model_name}, non-streaming)")

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
        }

        response = await self.client.post("/chat/completions", json=payload)
        
        # Log response details for debugging
        if response.status_code != 200:
            logger.error(f"OpenRouter error {response.status_code}: {response.text}")
        
        response.raise_for_status()
        data = response.json()

        # Handle cases where content may be None (some free models)
        choices = data.get("choices", [])
        if not choices:
            logger.error(f"OpenRouter returned no choices: {data}")
            raise ValueError("OpenRouter returned an empty response (no choices)")
        
        message = choices[0].get("message", {})
        content = message.get("content") or ""
        
        if not content:
            # Some free models return finish_reason=content_filter or similar
            finish_reason = choices[0].get("finish_reason", "unknown")
            logger.warning(f"OpenRouter returned empty content, finish_reason={finish_reason}")
            content = f"[Model returned empty response. finish_reason={finish_reason}]"
        
        logger.info(f"OpenRouter response received: {len(content)} chars")
        return content

    async def _generate_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        logger.info(f"Calling OpenRouter API (model: {self.model_name}, streaming)")

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
            "stream": True,
        }

        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            if response.status_code != 200:
                body = await response.aread()
                logger.error(f"OpenRouter stream error {response.status_code}: {body}")
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    line = line[6:]  # Remove "data: " prefix
                    if line.strip() == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(line)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

        logger.info("OpenRouter streaming response completed")


class NvidiaClient(BaseLLMClient):
    """NVIDIA API client (OpenAI-compatible)."""

    def __init__(self, settings: CopilotSettings):
        super().__init__(settings)
        import httpx
        self.client = httpx.AsyncClient(
            base_url=settings.nvidia_base_url,
            timeout=300.0,  # 5 minutes timeout for large models
        )
        self.api_key = settings.nvidia_api_key
        self.model_name = settings.nvidia_model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate a response from NVIDIA API."""
        try:
            if stream:
                return self._generate_stream(system_prompt, user_prompt)
            else:
                return await self._generate_complete(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"NVIDIA API call failed: {e}")
            raise

    async def _generate_complete(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a complete response from NVIDIA API."""
        logger.info(f"Calling NVIDIA API (model: {self.model_name}, non-streaming)")

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.settings.nvidia_max_tokens,
            "temperature": self.settings.nvidia_temperature,
            "stream": False,
        }

        response = await self.client.post(
            "/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()

        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        logger.info(f"NVIDIA API response received: {len(answer)} chars")
        return answer

    async def _generate_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from NVIDIA API."""
        logger.info(f"Calling NVIDIA API (model: {self.model_name}, streaming)")

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.settings.nvidia_max_tokens,
            "temperature": self.settings.nvidia_temperature,
            "stream": True,
        }

        async with self.client.stream(
            "POST",
            "/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        import json
                        data = json.loads(data_str)
                        delta = data["choices"][0]["delta"]
                        if "content" in delta:
                            content = delta["content"]
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

        logger.info("NVIDIA API streaming response completed")


def get_llm_client(settings: CopilotSettings) -> BaseLLMClient:
    """
    Factory function to get the appropriate LLM client based on settings.

    Args:
        settings: Copilot service settings

    Returns:
        Configured LLM client instance
    """
    provider = settings.llm_provider.lower()

    if provider == "nvidia":
        logger.info("Using NVIDIA API LLM client")
        return NvidiaClient(settings)
    elif provider == "ollama":
        logger.info("Using Ollama LLM client")
        return OllamaClient(settings)
    elif provider == "google" or provider == "gemini":
        logger.info("Using Google Gemini LLM client")
        return GeminiClient(settings)
    elif provider == "openrouter":
        logger.info("Using OpenRouter LLM client")
        return OpenRouterClient(settings)
    elif provider == "openai":
        logger.info("Using OpenAI LLM client")
        # TODO: Implement OpenAI client
        raise NotImplementedError("OpenAI client not yet implemented")
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# Keep backward-compatible aliases
ClaudeClient = GeminiClient
