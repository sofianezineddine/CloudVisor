"""Pydantic settings specific to the Copilot service."""

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Service-local .env takes priority; fall back to the monorepo root .env
_service_env = Path(__file__).parent.parent.parent / ".env"               # services/copilot/.env
_root_env    = Path(__file__).parent.parent.parent.parent.parent / ".env" # <root>/.env
_env_path    = _service_env if _service_env.exists() else (_root_env if _root_env.exists() else None)


class CopilotSettings(BaseSettings):
    """Configuration settings for CloudVisor Q (Copilot) service."""

    model_config = SettingsConfigDict(
        env_prefix="COPILOT_",
        extra="ignore",
    )

    service_name: str = Field(default="copilot")

    # LLM Provider selection
    llm_provider: str = Field(default="ollama")  # "ollama", "google", "openai", "openrouter"

    # Ollama configuration (local models)
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.2:3b")
    ollama_embedding_model: str = Field(default="nomic-embed-text")
    ollama_timeout: int = Field(default=300)

    # Google Gemini API configuration
    google_api_key: str = Field(default="")
    google_model: str = Field(default="gemini-2.0-flash-lite")
    google_max_tokens: int = Field(default=2048)
    google_temperature: float = Field(default=0.1)

    # OpenAI configuration
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4")
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: int = Field(default=1536)

    # OpenRouter configuration
    openrouter_api_key: str = Field(default="")
    openrouter_model: str = Field(default="meta-llama/llama-3.2-3b-instruct:free")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    openrouter_site_url: str = Field(default="")  # Optional: your site URL for rankings
    openrouter_app_name: str = Field(default="CloudVisor Q")  # Optional: your app name

    # NVIDIA API configuration
    nvidia_api_key: str = Field(default="")
    nvidia_base_url: str = Field(default="https://integrate.api.nvidia.com/v1")
    nvidia_model: str = Field(default="meta/llama-3.1-70b-instruct")
    nvidia_max_tokens: int = Field(default=2048)
    nvidia_temperature: float = Field(default=0.1)

    # General LLM settings
    max_tokens: int = Field(default=512)
    temperature: float = Field(default=0.1)

    # RAG configuration
    max_context_tokens: int = Field(default=128000)  # Llama 3.2 context window
    retrieval_timeout_seconds: int = Field(default=15)
    max_retrieval_results: int = Field(default=50)

    # Performance targets (in milliseconds)
    intent_classification_timeout_ms: int = Field(default=300)
    retrieval_timeout_ms: int = Field(default=2000)
    llm_timeout_ms: int = Field(default=8000)
    total_timeout_ms: int = Field(default=10000)

    # Streaming configuration
    enable_streaming: bool = Field(default=True)
    stream_chunk_size: int = Field(default=64)

    # CORS configuration
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:3001")

    # Internal service URLs
    graph_service_url: str = Field(default="http://localhost:8001")
    policy_service_url: str = Field(default="http://localhost:8003")
    ciem_service_url: str = Field(default="http://localhost:8007")
    cwpp_service_url: str = Field(default="http://localhost:8008")
    cdr_service_url: str = Field(default="http://localhost:8009")
    cicd_service_url: str = Field(default="http://localhost:8006")

    # Elasticsearch configuration
    elasticsearch_url: str = Field(default="http://localhost:9200")
    elasticsearch_findings_index: str = Field(default="cloudvisor-findings")

    # GitHub/GitLab PR configuration (for remediation)
    github_token: str = Field(default="")
    gitlab_token: str = Field(default="")
    enable_auto_pr: bool = Field(default=False)

    # Audit configuration
    audit_all_queries: bool = Field(default=True)
    audit_retention_days: int = Field(default=90)

    # Rate limiting
    rate_limit_per_minute: int = Field(default=20)
    rate_limit_per_hour: int = Field(default=100)


def get_copilot_settings() -> CopilotSettings:
    """Get copilot settings instance."""
    return CopilotSettings()
