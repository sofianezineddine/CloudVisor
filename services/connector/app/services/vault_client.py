"""HashiCorp Vault integration for secure credential storage."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class VaultClient:
    """
    Client for HashiCorp Vault to store and retrieve cloud credentials.
    """

    def __init__(
        self,
        vault_url: str = "",
        vault_token: str = "",
        vault_role: str = "",
        vault_namespace: str = "",
        mount_point: str = "cloudvisor",
    ):
        self._vault_url = vault_url
        self._vault_token = vault_token
        self._vault_role = vault_role
        self._vault_namespace = vault_namespace
        # Normalise: strip trailing slashes and any "/data" suffix that callers
        # might accidentally include — hvac adds those itself for KV v2.
        self._mount_point = mount_point.rstrip("/").split("/")[0]
        self._client = None

    async def initialize(self) -> bool:
        """Initialize Vault client connection."""
        if not self._vault_url:
            logger.warning("Vault URL not configured - Vault integration disabled")
            return False
        try:
            import hvac

            # If token is empty, try reading from token file
            token = self._vault_token
            if not token:
                import os
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
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Vault client: {e}")
            return False

    async def store_credentials(
        self,
        account_id: str,
        organization_id: str,
        provider: str,
        credentials: dict[str, Any],
    ) -> str:
        """
        Store encrypted credentials in Vault.

        Returns the secret path where credentials are stored.
        """
        if not self._client:
            raise RuntimeError("Vault client not initialized")

        # Use mount_point from config or default
        secret_path = f"{organization_id}/accounts/{account_id}"
        secret_data = {
            "provider": provider,
            "credentials": credentials,
        }

        try:
            self._client.secrets.kv.v2.create_or_update_secret(
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
        Retrieve decrypted credentials from Vault.

        secret_path is the full stored path e.g. "cloudvisor/org-id/accounts/acct-id".
        We strip the mount_point prefix so hvac gets only the sub-path.
        """
        if not self._client:
            raise RuntimeError("Vault client not initialized")

        # Strip the mount_point prefix if present (e.g. "cloudvisor/org/accounts/id"
        # → "org/accounts/id" when mount_point is "cloudvisor")
        prefix = self._mount_point + "/"
        if secret_path.startswith(prefix):
            relative_path = secret_path[len(prefix):]
        else:
            relative_path = secret_path

        try:
            response = self._client.secrets.kv.v2.read_secret_version(
                path=relative_path,
                mount_point=self._mount_point,
            )
            data = response.get("data", {}).get("data", {})
            return data.get("credentials", {})

        except Exception as e:
            logger.error(f"Failed to retrieve credentials from Vault: {e}")
            raise

    async def rotate_credentials(
        self,
        account_id: str,
        organization_id: str,
        provider: str,
        new_credentials: dict[str, Any],
    ) -> str:
        """
        Rotate credentials in Vault (creates new version, doesn't delete old).

        Returns the new secret version path.
        """
        if not self._client:
            raise RuntimeError("Vault client not initialized")

        secret_path = f"cloudvisor/{organization_id}/accounts/{account_id}"

        try:
            # Store new version
            await self.store_credentials(
                account_id=account_id,
                organization_id=organization_id,
                provider=provider,
                credentials=new_credentials,
            )

            logger.info(f"Credentials rotated for account {account_id}")
            return secret_path

        except Exception as e:
            logger.error(f"Failed to rotate credentials in Vault: {e}")
            raise

    async def delete_credentials(
        self,
        account_id: str,
        organization_id: str,
    ) -> None:
        """
        Permanently delete credentials from Vault.
        """
        if not self._client:
            raise RuntimeError("Vault client not initialized")

        secret_path = f"cloudvisor/{organization_id}/accounts/{account_id}"

        try:
            self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=secret_path,
            )
            logger.info(f"Credentials deleted from Vault for account {account_id}")

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

        secret_path = f"cloudvisor/{organization_id}/accounts/{account_id}"

        try:
            response = self._client.secrets.kv.v2.read_secret_metadata(
                path=secret_path,
            )
            return response.get("data", {})

        except Exception as e:
            logger.error(f"Failed to get secret metadata: {e}")
            return {}
