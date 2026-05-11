"""Resource normalization service - converts raw cloud API responses to CDM."""

import uuid
from typing import Any

from cloudvisor_types.models import (
    CloudProvider,
    CloudResource,
    Environment,
    get_resource_type,
)

from app.core.time_utils import utcnow


class ResourceNormalizer:
    """Normalizes cloud provider API responses to Common Data Model."""

    PUBLIC_IP_RANGES = {
        "0.0.0.0/0",
        "::/0",
    }

    ENV_KEYWORDS = {
        "prod": Environment.PROD,
        "production": Environment.PROD,
        "staging": Environment.STAGING,
        "stage": Environment.STAGING,
        "dev": Environment.DEV,
        "development": Environment.DEV,
        "test": Environment.DEV,
        "qa": Environment.DEV,
    }

    def __init__(self, organization_id: str):
        self._organization_id = organization_id

    def normalize(
        self,
        raw_resource: dict[str, Any],
        provider: str,
        account_id: str,
    ) -> CloudResource:
        """Normalize a raw cloud resource to CDM format."""
        provider_enum = CloudProvider(provider)

        resource_type = self._get_resource_type(raw_resource, provider_enum)
        normalized_type = get_resource_type(provider_enum, resource_type)

        name = self._extract_name(raw_resource, resource_type)
        tags = self._normalize_tags(raw_resource, provider)
        region = self._extract_region(raw_resource, provider)
        is_public = self._detect_public_access(raw_resource, resource_type, provider)
        environment = self._infer_environment(tags, name)

        return CloudResource(
            id=str(uuid.uuid4()),
            cloud_resource_id=raw_resource.get("id", ""),
            provider=provider_enum,
            account_id=account_id,
            region=region,
            resource_type=normalized_type,
            name=name,
            tags=tags,
            raw=raw_resource.get("raw", raw_resource),
            organization_id=self._organization_id,
            is_public=is_public,
            environment=environment,
            first_seen_at=utcnow(),
            last_seen_at=utcnow(),
        )

    def _get_resource_type(self, raw: dict[str, Any], provider: CloudProvider) -> str:
        """Extract resource type from raw resource."""
        raw_type = raw.get("type", "")
        if not raw_type:
            raw_type = raw.get("resource_type", "")
        return raw_type

    def _extract_name(self, raw: dict[str, Any], resource_type: str) -> str:
        """Extract human-readable name from resource."""
        if "name" in raw:
            return raw["name"]
        if "display_name" in raw:
            return raw["display_name"]
        if "id" in raw:
            return raw["id"].split("/")[-1] if "/" in raw["id"] else raw["id"]
        return resource_type

    def _normalize_tags(self, raw: dict[str, Any], provider: str) -> dict[str, str]:
        """Normalize tags across providers."""
        tags = {}

        if "tags" in raw and isinstance(raw["tags"], dict):
            tags.update(raw["tags"])

        if "labels" in raw and isinstance(raw["labels"], dict):
            if not tags:
                tags.update(raw["labels"])

        return {k.lower(): str(v).lower() for k, v in tags.items()}

    def _extract_region(self, raw: dict[str, Any], provider: str) -> str:
        """Extract region from resource."""
        if "region" in raw:
            return raw["region"]
        if "location" in raw:
            if isinstance(raw["location"], str):
                return raw["location"]
            if isinstance(raw["location"], dict):
                return raw["location"].get("location", "global")

        if provider == "aws":
            if "availabilityZone" in raw:
                return raw["availabilityZone"][:-1]
        if provider == "azure":
            if "location" in raw:
                return raw["location"]
        if provider == "gcp":
            if "zone" in raw:
                return raw["zone"].split("/")[-1]
            if "region" in raw:
                return raw["region"]

        return "global"

    def _detect_public_access(self, raw: dict[str, Any], resource_type: str, provider: str) -> bool:
        """Detect if resource is internet-facing."""
        if resource_type.lower() in ["s3bucket", "bucket"]:
            if "publicaccessblockconfiguration" in raw:
                config = raw["publicaccessblockconfiguration"]
                if not all(
                    [
                        config.get("blockpublicacls", True),
                        config.get("blockpublicpolicy", True),
                        config.get("ignorepublicacls", True),
                        config.get("restrictpublicbuckets", True),
                    ]
                ):
                    return True
            return False

        if resource_type.lower() in ["securitygroup", "nsg"]:
            rules = raw.get("ipPermissions", raw.get("securityrules", []))
            for rule in rules:
                cidr = rule.get("cidrIp", "")
                if cidr in self.PUBLIC_IP_RANGES:
                    return True

        if resource_type.lower() in ["instance", "virtualmachine"]:
            if raw.get("publicipaddress") or raw.get("PublicIpAddress"):
                return True

        if resource_type.lower() in ["loadbalancer", "elb"]:
            if raw.get("scheme") == "internet-facing":
                return True

        return False

    def _infer_environment(self, tags: dict[str, str], name: str) -> Environment:
        """Infer environment from tags or name patterns."""
        for key, value in tags.items():
            if key in ["environment", "env", "stage"]:
                env = self.ENV_KEYWORDS.get(value.lower())
                if env:
                    return env

        name_lower = name.lower()
        for keyword, env in self.ENV_KEYWORDS.items():
            if keyword in name_lower:
                return env

        return Environment.UNKNOWN


class BatchNormalizer:
    """Batch normalizes multiple resources."""

    def __init__(self, organization_id: str):
        self._normalizer = ResourceNormalizer(organization_id)

    def normalize_batch(
        self,
        raw_resources: list[dict[str, Any]],
        provider: str,
        account_id: str,
    ) -> list[CloudResource]:
        """Normalize a batch of resources."""
        return [self._normalizer.normalize(raw, provider, account_id) for raw in raw_resources]
