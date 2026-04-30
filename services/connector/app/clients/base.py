"""Base interface for cloud provider clients."""

from abc import ABC, abstractmethod
from typing import Any


class CloudClientBase(ABC):
    """Abstract base class for all cloud provider API clients."""

    @abstractmethod
    async def connect(self) -> bool:
        """Test the connection to the cloud provider."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close any open connections."""
        pass

    @abstractmethod
    async def list_resources(self, region: str | None = None) -> list[dict[str, Any]]:
        """List all resources in the account."""
        pass

    def get_resource(
        self, resource_id: str, region: str | None = None
    ) -> dict[str, Any] | None:
        """Get a specific resource by ID. Override in subclass if needed."""
        return None

    @abstractmethod
    def get_account_id(self) -> str:
        """Get the cloud account ID associated with this client."""
        pass

    def compute_resource_hash(self, resource: dict[str, Any]) -> str:
        """Compute a hash for change detection. Override in subclass."""
        import hashlib, json
        content = json.dumps(resource, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
