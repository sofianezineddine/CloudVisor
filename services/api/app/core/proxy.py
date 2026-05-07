"""
HTTP proxy client for forwarding requests to upstream services.
All upstream calls include the caller's auth headers for tenant isolation.
"""

import logging
import uuid
from typing import Any

import httpx

from .config import get_api_settings

logger = logging.getLogger(__name__)
_settings = get_api_settings()


class ServiceProxy:
    """Thin async HTTP proxy to an upstream microservice."""

    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")
        self._timeout = _settings.upstream_timeout

    async def get(
        self,
        path: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base_url}{path}",
                params=params,
                headers=headers or {},
            )
            resp.raise_for_status()
            return resp.json()

    async def post(
        self,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}{path}",
                json=json,
                params=params,
                headers=headers or {},
            )
            resp.raise_for_status()
            return resp.json()

    async def patch(
        self,
        path: str,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.patch(
                f"{self._base_url}{path}",
                json=json,
                headers=headers or {},
            )
            resp.raise_for_status()
            return resp.json()

    async def put(
        self,
        path: str,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.put(
                f"{self._base_url}{path}",
                json=json,
                headers=headers or {},
            )
            resp.raise_for_status()
            return resp.json()

    async def delete(
        self,
        path: str,
        headers: dict | None = None,
    ) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.delete(
                f"{self._base_url}{path}",
                headers=headers or {},
            )
            if resp.status_code == 204:
                return None
            resp.raise_for_status()
            return resp.json()


# ─── Service proxy singletons ─────────────────────────────────────────────────

def get_connector_proxy() -> ServiceProxy:
    return ServiceProxy(_settings.connector_service_url)

def get_graph_proxy() -> ServiceProxy:
    return ServiceProxy(_settings.graph_service_url)

def get_policy_proxy() -> ServiceProxy:
    return ServiceProxy(_settings.policy_service_url)

def get_alert_proxy() -> ServiceProxy:
    return ServiceProxy(_settings.alert_service_url)

def get_cspm_proxy() -> ServiceProxy:
    return ServiceProxy(_settings.cspm_service_url)

# Expose base URL for direct streaming (file downloads)
_CSPM_URL = _settings.cspm_service_url

def get_auth_proxy() -> ServiceProxy:
    return ServiceProxy(_settings.auth_service_url)

def get_copilot_proxy() -> ServiceProxy:
    return ServiceProxy(_settings.copilot_service_url)
