"""Envelope encryption for customer cloud credentials.

Spec §8: customer cloud credentials must be envelope-encrypted with a
per-organization data encryption key (DEK), so that even an operator with
raw DB or Vault access cannot read plaintext without the org-specific DEK.

Design:
    1. On first use for an org, we derive a 32-byte DEK via HKDF-SHA256
       from (a) a master key material (from env ``CONNECTOR_CREDENTIAL_MASTER_KEY``
       — in production, Vault transit or KMS) and (b) the organization_id
       as salt.  This gives a deterministic per-org key without storing one.
    2. Credentials are serialized to JSON, then encrypted with AES-256-GCM
       using the DEK and a fresh 12-byte nonce.
    3. Stored payload is a dict with ``scheme``, ``nonce`` (base64), and
       ``ciphertext`` (base64). A plaintext record is recognised by the
       absence of the ``scheme`` key so we can read legacy data.

The DEK is NEVER persisted — it is re-derived on each decrypt operation.

Fallback: if ``CONNECTOR_CREDENTIAL_MASTER_KEY`` is unset (common in dev),
encryption is a no-op that returns the plaintext dict unchanged, so the
service still works but logs a warning at startup.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_SCHEME = "AES-256-GCM+HKDF-SHA256"


def _hkdf_sha256(key_material: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """HKDF-SHA256 key derivation (RFC 5869)."""
    # Extract step
    prk = hmac.new(salt, key_material, hashlib.sha256).digest()
    # Expand step
    okm = b""
    t = b""
    counter = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]


def _get_master_key() -> bytes | None:
    """Load the master key material from env or Vault.

    Returns None if no master key is configured (dev/legacy mode).
    """
    raw = os.getenv("CONNECTOR_CREDENTIAL_MASTER_KEY", "").strip()
    if not raw:
        return None
    # Accept either hex (64 chars) or base64. A short value is padded to 32 bytes
    # via SHA-256 so a short dev passphrase still produces a valid key.
    try:
        if len(raw) == 64:
            return bytes.fromhex(raw)
        # Try base64
        try:
            decoded = base64.b64decode(raw, validate=True)
            if len(decoded) >= 32:
                return decoded[:32]
        except Exception:
            pass
    except ValueError:
        pass
    # Fallback: SHA-256 of the raw string. Stable + 32 bytes.
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _derive_dek(master: bytes, organization_id: str) -> bytes:
    """Derive a 32-byte DEK for an organization."""
    salt = hashlib.sha256(f"cloudvisor.connector.{organization_id}".encode("utf-8")).digest()
    return _hkdf_sha256(
        key_material=master,
        salt=salt,
        info=b"cloudvisor-credential-dek-v1",
        length=32,
    )


def encrypt_credentials(
    credentials: dict[str, Any] | None,
    organization_id: str,
) -> dict[str, Any] | None:
    """Encrypt a credentials dict for storage.

    Returns a wrapper dict {"scheme", "nonce", "ciphertext"} when encryption
    is active, or the input dict unchanged when no master key is configured
    (legacy / dev mode).
    """
    if not credentials:
        return credentials

    master = _get_master_key()
    if master is None:
        logger.warning(
            "CONNECTOR_CREDENTIAL_MASTER_KEY is not set — credentials stored in "
            "plaintext JSONB. Configure it in production (see spec §8)."
        )
        return credentials

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        logger.error(
            "cryptography library not installed — cannot encrypt credentials. "
            "Falling back to plaintext storage (NOT safe for production)."
        )
        return credentials

    dek = _derive_dek(master, organization_id)
    aesgcm = AESGCM(dek)
    nonce = os.urandom(12)
    plaintext = json.dumps(credentials, default=str, sort_keys=True).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=organization_id.encode("utf-8"))

    return {
        "scheme": _SCHEME,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_credentials(
    stored: dict[str, Any] | None,
    organization_id: str,
) -> dict[str, Any]:
    """Decrypt a stored credentials dict back to plaintext.

    If the stored value has no ``scheme`` key, it's legacy plaintext — return
    as-is. This keeps backward compatibility with already-stored credentials.
    """
    if not stored:
        return {}

    # Legacy plaintext — no scheme key
    if "scheme" not in stored:
        return dict(stored)

    if stored["scheme"] != _SCHEME:
        raise ValueError(f"Unsupported credential encryption scheme: {stored['scheme']}")

    master = _get_master_key()
    if master is None:
        raise RuntimeError(
            "Credentials are encrypted but CONNECTOR_CREDENTIAL_MASTER_KEY is unset. "
            "Restore the master key to decrypt."
        )

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as e:
        raise RuntimeError(
            "cryptography library required to decrypt credentials; install it."
        ) from e

    dek = _derive_dek(master, organization_id)
    aesgcm = AESGCM(dek)
    nonce = base64.b64decode(stored["nonce"])
    ciphertext = base64.b64decode(stored["ciphertext"])
    plaintext = aesgcm.decrypt(
        nonce, ciphertext, associated_data=organization_id.encode("utf-8")
    )
    return json.loads(plaintext.decode("utf-8"))


def is_encrypted(stored: dict[str, Any] | None) -> bool:
    """Return True if a stored credentials blob looks encrypted."""
    return bool(stored) and "scheme" in stored and "ciphertext" in stored
