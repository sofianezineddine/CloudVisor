"""Cloud provider client factory."""

from typing import Any
from .base import CloudClientBase
from .aws import AWSClient
from .azure import AzureClient
from .gcp import GCPClient
from .oci import OCIClient


class ClientFactory:
    """Factory for creating cloud provider clients."""

    _clients: dict[str, type] = {
        "aws": AWSClient,
        "azure": AzureClient,
        "gcp": GCPClient,
        "oci": OCIClient,
    }

    @classmethod
    def create_client(
        cls, provider: str, credentials: dict[str, Any], **kwargs: Any
    ) -> CloudClientBase:
        """Create a cloud provider client instance."""
        client_class = cls._clients.get(provider.lower())
        if not client_class:
            raise ValueError(f"Unknown cloud provider: {provider}")
        return client_class(credentials, **kwargs)

    @classmethod
    def register_client(cls, provider: str, client_class: type) -> None:
        """Register a new cloud provider client."""
        cls._clients[provider.lower()] = client_class


__all__ = ["ClientFactory", "CloudClientBase"]
