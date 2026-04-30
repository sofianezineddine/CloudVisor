"""CloudVisor type definitions for the Connector service."""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


class CloudProvider(str, Enum):
    """Supported cloud providers."""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    OCI = "oci"


class Environment(str, Enum):
    """Deployment environments."""
    PROD = "prod"
    STAGING = "staging"
    DEV = "dev"
    UNKNOWN = "unknown"


class SyncStatus(str, Enum):
    """Sync operation status."""
    IDLE = "idle"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncResult:
    """Result of a sync operation."""
    discovered: int = 0
    updated: int = 0
    deleted: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    error_details: list[str] = field(default_factory=list)


@dataclass
class CloudResource:
    """Common Data Model (CDM) for cloud resources."""
    id: str
    cloud_resource_id: str
    provider: CloudProvider
    account_id: str
    region: str
    resource_type: str
    name: str
    tags: dict[str, str]
    raw: dict[str, Any]
    organization_id: str
    is_public: bool
    environment: Environment
    first_seen_at: datetime
    last_seen_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "id": self.id,
            "cloud_resource_id": self.cloud_resource_id,
            "provider": self.provider.value,
            "account_id": self.account_id,
            "region": self.region,
            "resource_type": self.resource_type,
            "name": self.name,
            "tags": self.tags,
            "organization_id": self.organization_id,
            "is_public": self.is_public,
            "environment": self.environment.value,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


@dataclass
class CloudAccount:
    """Cloud account configuration."""
    id: str
    organization_id: str
    provider: CloudProvider
    name: str
    account_id: str
    status: str = "pending"
    region: str = "global"
    polling_interval_minutes: int = 15
    resource_count: int = 0
    consecutive_errors: int = 0
    error_message: str | None = None
    last_sync_at: datetime | None = None
    last_successful_sync_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "provider": self.provider.value,
            "name": self.name,
            "account_id": self.account_id,
            "status": self.status,
            "region": self.region,
            "polling_interval_minutes": self.polling_interval_minutes,
            "resource_count": self.resource_count,
            "consecutive_errors": self.consecutive_errors,
            "error_message": self.error_message,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_successful_sync_at": (
                self.last_successful_sync_at.isoformat()
                if self.last_successful_sync_at else None
            ),
        }


def get_resource_type(provider: CloudProvider, raw_type: str) -> str:
    """Get normalized resource type string."""
    return f"{provider.value}::{raw_type.lower()}"


__all__ = [
    "CloudProvider",
    "Environment",
    "SyncStatus",
    "SyncResult",
    "CloudResource",
    "CloudAccount",
    "get_resource_type",
]
