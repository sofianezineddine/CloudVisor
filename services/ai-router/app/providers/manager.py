"""
Provider Manager - Factory for creating and managing LLM providers
"""
from typing import Optional

from app.core.config import get_settings
from app.providers.base import BaseLLMProvider
from app.providers.nvidia_provider import NVIDIAProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.openrouter_provider import OpenRouterProvider


class ProviderManager:
    """Manages LLM provider instances."""
    
    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}
        self._settings = get_settings()
    
    def get_provider(self, provider_name: Optional[str] = None) -> BaseLLMProvider:
        """Get or create a provider instance."""
        name = provider_name or self._settings.default_provider
        name = name.lower()
        
        if name not in self._providers:
            self._providers[name] = self._create_provider(name)
        
        return self._providers[name]
    
    def _create_provider(self, name: str) -> BaseLLMProvider:
        """Create a new provider instance."""
        config = self._settings.get_provider_config(name)
        
        if not config:
            raise ValueError(f"Unknown provider: {name}")
        
        if not config["api_key"]:
            raise ValueError(f"Provider {name} is not configured (missing API key)")
        
        if name == "openai":
            return OpenAIProvider(
                api_key=config["api_key"],
                base_url=config["base_url"],
                default_model=config["default_model"],
            )
        elif name == "openrouter":
            return OpenRouterProvider(
                api_key=config["api_key"],
                base_url=config["base_url"],
                default_model=config["default_model"],
            )
        elif name == "nvidia":
            return NVIDIAProvider(
                api_key=config["api_key"],
                base_url=config["base_url"],
                default_model=config["default_model"],
            )
        else:
            raise ValueError(f"Unknown provider: {name}")
    
    def list_available_providers(self) -> list[str]:
        """List all configured and available providers."""
        return self._settings.get_available_providers()
    
    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all configured providers."""
        results = {}
        for provider_name in self.list_available_providers():
            try:
                provider = self.get_provider(provider_name)
                results[provider_name] = await provider.health_check()
            except Exception:
                results[provider_name] = False
        return results


# Global provider manager instance
_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Get the global provider manager instance."""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager
