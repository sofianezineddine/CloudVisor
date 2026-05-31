"""
AI Router Service Configuration
"""
import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service Configuration
    app_environment: str = "development"
    log_level: str = "INFO"
    port: int = 8015
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_default_model: str = "gpt-4o-mini"
    
    # OpenRouter Configuration
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    
    # NVIDIA NIM Configuration
    nvidia_api_key: Optional[str] = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_default_model: str = "meta/llama-3.1-405b-instruct"
    
    # Default Provider
    default_provider: str = "openai"
    
    # Rate Limiting
    rate_limit_rpm: int = 60
    request_timeout: int = 60
    max_tokens: int = 4096
    
    # Redis Configuration
    redis_url: Optional[str] = None
    enable_cache: bool = False
    cache_ttl: int = 3600
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def is_production(self) -> bool:
        return self.app_environment.lower() == "production"
    
    def get_provider_config(self, provider: str):
        """Get configuration for a specific provider."""
        configs = {
            "openai": {
                "api_key": self.openai_api_key,
                "base_url": self.openai_base_url,
                "default_model": self.openai_default_model,
            },
            "openrouter": {
                "api_key": self.openrouter_api_key or self.openai_api_key,
                "base_url": self.openrouter_base_url,
                "default_model": self.openrouter_default_model,
            },
            "nvidia": {
                "api_key": self.nvidia_api_key,
                "base_url": self.nvidia_base_url,
                "default_model": self.nvidia_default_model,
            },
        }
        return configs.get(provider.lower())
    
    def get_available_providers(self) -> list[str]:
        """Return list of configured providers."""
        available = []
        if self.openai_api_key:
            available.append("openai")
        if self.openrouter_api_key or (self.openai_api_key and "openrouter" in self.openai_base_url):
            available.append("openrouter")
        if self.nvidia_api_key:
            available.append("nvidia")
        return available


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
