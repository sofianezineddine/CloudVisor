"""HashiCorp Vault integration for secure credential storage."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class VaultClient:
    """
    Client for HashiCorp Vault to store and retrieve cloud credentials.

    Features:
      - KV v2 secrets engine with configurable mount point
      - Automatic token renewal loop (every N seconds, default 30 min)
      - Safe path normalisation
      - Async-compatible (hvac is sync but we hop to a thread on writes)
    """

    def __init__(
        self,
        vault_url: str = "",
        vault_token: str = "",
        vault_role: str = "",
        vault_namespace: str = "",
        mount_point: str = "cloudvisor",
        renew_every_seconds: int = 1800,
    ):
        self._vault_url = vault_url
        self._vault_token = vault_token
        self._vault_role = vault_role
        self._vault_namespace = vault_namespace
        # Normalise: strip trailing slashes and any "/data" suffix that callers
        # might accidentally include — hvac adds those itself for KV v2.
        self._mount_point = mount_point.rstrip("/").split("/")[0]
        self._renew_every_seconds = renew_every_seconds
        self._client = None
        self._renew_task: asyncio.Task | None = None

    async def initialize(self) -> bool:
        """Initialize Vault client connection and start the token-renewal loop."""
        if not self._vault_url:
            logger.warning("Vault URL not configured - Vault integration disabled")
            return False
        try:
            import hvac

            # If token is empty, try reading from token file
            token = self._vault_token
            if not token:
                token_file = os.environ.get("VAULT_TOKEN_FILE", "/vault/data/vault_token")
                if os.path.exists(token_file):
                    with open(token_file) as f:
                        token = f.read().strip()
                    logger.info(f"Loaded Vault token from {token_file}")
                else:
                    logger.error(f"No Vault token and token file not found: {token_file}")
                    return False

            self._client = hvac.Client(
                url=self._vault_url,
                token=token,
                namespace=self._vault_namespace,
            )
            if not self._client.is_authenticated():
                logger.error("Failed to authenticate with Vault")
                return False
            logger.info("Vault client initialized successfully")

            # Start the token renewal loop in the background
            try:
                self._renew_task = asyncio.create_task(
                    self._renewal_loop(), name="vault-token-renewal"
                )
            except RuntimeError:
                # Not inside an event loop — skip renewal (e.g. during tests)
                logger.debug("No running event loop — Vault token renewal skipped")

            return True
        except Exception as e:
            logger.error(f"Failed to initialize Vault client: {e}")
            return False

    async def close(self) -> None:
        """Cancel the token renewal loop. Safe to call even if never started."""
        if self._renew_task is not None and not self._renew_task.done():
            self._renew_task.cancel()
            try:
                await self._renew_task
            except (asyncio.CancelledError, Exception):
                pass
            self._renew_task = None

    async def _renewal_loop(self) -> None:
        """Renew the token periodically to keep long-running connectors alive."""
        while True:
            try:
                await asyncio.sleep(self._renew_every_seconds)
                if self._client is None:
                    return
                # hvac is sync — run in a thread so we don't block the loop
                await asyncio.to_thread(self._client.auth.token.renew_self)
                logger.debug("Vault token renewed")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Non-fatal — renewal will try again next tick
                logger.warning(f"Vault token renewal failed: {e}")

    async def store_credentials(
        self,
        account_id: str,
        organization_id: str,
        provider: str,
        credentials: dict[str, Any],
    ) -> str:
        """
        Store credentials (already encrypted by caller) in Vault.

        Returns the secret path where credentials are stored.
        """
        if not self._client:
            raise RuntimeError("Vault client not initialized")

        secret_path = f"{organization_id}/accounts/{account_id}"
        secret_data = {
            "provider": provider,
            "credentials": credentials,
        }

        try:
            await asyncio.to_thread(
                self._client.secrets.kv.v2.create_or_update_secret,
                path=secret_path,
                secret=secret_data,
                mount_point=self._mount_point,
            )
            full_path = f"{self._mount_point}/{secret_path}"
            logger.info(f"Credentials stored in Vault at: {full_path}")
            return full_path

        except Exception as e:
            logger.error(f"Failed to store credentials in Vault: {e}")
            raise

    async def retrieve_credentials(
        self,
        secret_path: str,
    ) -> dict[str, Any]:
        """
        Retrieve credentials from Vault.

        ``secret_path`` is the full stored path (e.g. ``cloudvisor/org/accounts/id``).
        The mount_point prefix is stripped so hvac gets only the sub-path.
        Returns the raw ``credentials`` sub-dict — caller is responsible for
        decrypting it via :mod:`credential_crypto` if encrypted.
        """
        if not self._client:
            raise RuntimeError("Vault client not initialized")

        prefix = self._mount_point + "/"
        if secret_path.startswith(prefix):
            relative_path = secret_path[len(prefix):]
        else:
            relative_path = secret_path

        try:
            response = await asyncio.to_thread(
                self._client.secrets.kv.v2.read_secret_version,
                path=relative_path,
                mount_point=self._mount_point,
                raise_on_deleted_version=True,
            )
            data = response.get("data", {}).get("data", {})
            return data.get("credentials", {})

        except Exception as e:
            logger.error(f"Failed to retrieve credentials from Vault: {e}")
            raise

    # Backwards-compat alias for older callers that used ``get_credentials``
    async def get_credentials(self, secret_path: str) -> dict[str, Any]:
        """Deprecated — use ``retrieve_credentials`` instead."""
        return await self.retrieve_credentials(secret_path)

    async def rotate_credentials(
        self,
        account_id: str,
        organization_id: str,
        provider: str,
        new_credentials: dict[str, Any],
    ) -> str:
        """
        Rotate credentials in Vault (creates new KV v2 version).
        Returns the stored secret path.
        """
        if not self._client:
            raise RuntimeError("Vault client not initialized")

        return await self.store_credentials(
            account_id=account_id,
            organization_id=organization_id,
            provider=provider,
            credentials=new_credentials,
        )

    async def delete_credentials(
        self,
        secret_path_or_account_id: str,
        organization_id: str | None = None,
    ) -> None:
        """
        Permanently delete credentials from Vault.

        Accepts either a full secret path (as stored) or legacy signature
        ``(account_id, organization_id)`` for compatibility with older callers.
        """
        if not self._client:
            raise RuntimeError("Vault client not initialized")

        if organization_id is not None:
            # Legacy signature: delete_credentials(account_id, organization_id)
            secret_path = f"{organization_id}/accounts/{secret_path_or_account_id}"
        else:
            # Strip the mount_point prefix if caller included it
            prefix = self._mount_point + "/"
            if secret_path_or_account_id.startswith(prefix):
                secret_path = secret_path_or_account_id[len(prefix):]
            else:
                secret_path = secret_path_or_account_id

        try:
            await asyncio.to_thread(
                self._client.secrets.kv.v2.delete_metadata_and_all_versions,
                path=secret_path,
                mount_point=self._mount_point,
            )
            logger.info(f"Credentials deleted from Vault at {secret_path}")

        except Exception as e:
            logger.error(f"Failed to delete credentials from Vault: {e}")
            raise

    async def get_secret_metadata(
        self,
        account_id: str,
        organization_id: str,
    ) -> dict[str, Any]:
        """
        Get metadata about stored credentials (version, creation time, etc.).
        """
        if not self._client:
            raise RuntimeError("Vault client not initialized")

        secret_path = f"{organization_id}/accounts/{account_id}"

        try:
            response = await asyncio.to_thread(
                self._client.secrets.kv.v2.read_secret_metadata,
                path=secret_path,
                mount_point=self._mount_point,
            )
            return response.get("data", {})

        except Exception as e:
            logger.error(f"Failed to get secret metadata: {e}")
            return {}
