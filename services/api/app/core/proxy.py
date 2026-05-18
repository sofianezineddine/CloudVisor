"""
HTTP proxy client for forwarding requests to upstream services.

Security & reliability features:
- All upstream calls include the caller's auth headers for tenant isolation
- Connection pooling via shared httpx.AsyncClient instances (avoids per-request overhead)
- Correlation ID propagation for distributed tracing
- Configurable timeouts per upstream service
"""

import logging
import uuid
from contextvars import ContextVar
from typing import Any

import httpx

from .config import get_api_settings

logger = logging.getLogger(__name__)
_settings = get_api_settings()

# ─── Correlation ID context (set in middleware, propagated to all upstream calls) ─
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get the current request's correlation ID."""
    cid = correlation_id_var.get("")
    if not cid:
        cid = f"cid_{uuid.uuid4().hex[:16]}"
        correlation_id_var.set(cid)
    return cid


# ─── Connection-pooled HTTP clients (one per upstream service) ────────────────
# These are module-level singletons that reuse TCP connections across requests.

_clients: dict[str, httpx.AsyncClient] = {}


def _get_client(base_url: str) -> httpx.AsyncClient:
    """Get or create a connection-pooled async HTTP client for the given base URL."""
    if base_url not in _clients:
        _clients[base_url] = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(
                connect=5.0,
                read=_settings.upstream_timeout,
                write=10.0,
                pool=5.0,
            ),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            ),
        )
    return _clients[base_url]


class ServiceProxy:
    """Thin async HTTP proxy to an upstream microservice with connection pooling."""

    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    def _inject_headers(self, headers: dict | None) -> dict[str, str]:
        """Inject correlation ID and service identity into outbound headers."""
        h = dict(headers or {})
        h.setdefault("X-Correlation-ID", get_correlation_id())
        h.setdefault("X-Source-Service", "api")
        return h

    async def get(
        self,
        path: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:
        client = _get_client(self._base_url)
        resp = await client.get(
            path,
            params=params,
            headers=self._inject_headers(headers),
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
        client = _get_client(self._base_url)
        resp = await client.post(
            path,
            json=json,
            params=params,
            headers=self._inject_headers(headers),
        )
        resp.raise_for_status()
        return resp.json()

    async def patch(
        self,
        path: str,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:
        client = _get_client(self._base_url)
        resp = await client.patch(
            path,
            json=json,
            headers=self._inject_headers(headers),
        )
        resp.raise_for_status()
        return resp.json()

    async def put(
        self,
        path: str,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:
        client = _get_client(self._base_url)
        resp = await client.put(
            path,
            json=json,
            headers=self._inject_headers(headers),
        )
        resp.raise_for_status()
        return resp.json()

    async def delete(
        self,
        path: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any] | None:
        client = _get_client(self._base_url)
        resp = await client.delete(
            path,
            params=params,
            headers=self._inject_headers(headers),
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

def get_keep_proxy() -> ServiceProxy:
    return ServiceProxy(_settings.keep_service_url)
