#!/usr/bin/env python3
"""
Vault initialization + auto-unseal daemon.

Runs on every container start (restart: always).
1. Waits for Vault TCP to be reachable
2. Initializes Vault if not already initialized (saves keys to /vault/data/init_keys.json)
3. Unseals Vault if sealed
4. Enables cloudvisor/ KV v2 mount
5. Writes root token to /vault/data/vault_token for the connector service
6. Loops every 10 seconds — re-unseals automatically if Vault restarts

SECURITY WARNING: This script uses a single-key unseal (secret_shares=1, threshold=1)
and stores the unseal key and root token on disk. This is intentional for a
development/demo environment where Vault auto-unseal is not configured.

For PRODUCTION deployments:
  - Use Vault Auto Unseal with AWS KMS, Azure Key Vault, or GCP Cloud KMS
  - Use multiple key shares (e.g., 5 shares, threshold 3) for Shamir's Secret Sharing
  - Never store the root token on disk — use AppRole or Kubernetes auth instead
  - Rotate the root token immediately after initial setup
  - Use a dedicated service token with minimal policies instead of the root token
"""
import json
import os
import stat
import sys
import time

try:
    import hvac
except ImportError:
    os.system("pip install hvac -q")
    import hvac

VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://cv-vault:8200")
DATA_DIR = "/vault/data"
KEYS_FILE = os.path.join(DATA_DIR, "init_keys.json")
TOKEN_FILE = os.path.join(DATA_DIR, "vault_token")


def get_status(client):
    try:
        resp = client.sys.read_health_status(method="GET")
        if hasattr(resp, "json"):
            return resp.json()
        if isinstance(resp, dict):
            return resp
        return {}
    except Exception:
        return {}


def wait_for_vault(retries=60):
    for i in range(retries):
        try:
            client = hvac.Client(url=VAULT_ADDR)
            status = get_status(client)
            if "initialized" in status:
                return client
        except Exception:
            pass
        print(f"Waiting for Vault ({i+1}/{retries})...")
        time.sleep(2)
    print("ERROR: Vault not reachable after retries")
    sys.exit(1)


def initialize_vault(client):
    """Initialize Vault and save keys. Only runs once.

    SECURITY: Uses 1 key share for development convenience.
    Production should use multiple shares with a higher threshold.
    """
    print("Initializing Vault (1 key share, threshold 1)...")
    result = client.sys.initialize(secret_shares=1, secret_threshold=1)
    keys = {
        "unseal_keys_b64": result["keys_base64"],
        "root_token": result["root_token"],
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f)
    # Restrict to owner read/write only (no group or other access)
    os.chmod(KEYS_FILE, stat.S_IRUSR | stat.S_IWUSR)
    print(f"Initialized. Keys saved to {KEYS_FILE}")
    print("WARNING: Root token and unseal key stored on disk — development mode only.")
    return keys


def load_keys():
    if not os.path.exists(KEYS_FILE):
        print(f"ERROR: {KEYS_FILE} not found — cannot unseal")
        sys.exit(1)
    with open(KEYS_FILE) as f:
        return json.load(f)


def unseal_vault(client, unseal_key):
    print("Unsealing Vault...")
    client.sys.submit_unseal_key(unseal_key)
    time.sleep(1)
    status = get_status(client)
    if not status.get("sealed", True):
        print("Vault unsealed successfully ✓")
        return True
    print("WARNING: Vault still sealed after unseal attempt")
    return False


def enable_kv(client, root_token):
    client.token = root_token
    try:
        client.sys.enable_secrets_engine(
            backend_type="kv",
            path="cloudvisor",
            options={"version": "2"},
        )
        print("Enabled cloudvisor/ KV v2 ✓")
    except Exception as e:
        msg = str(e).lower()
        if "path is already in use" in msg or "existing mount" in msg:
            print("cloudvisor/ KV v2 already mounted ✓")
        else:
            print(f"KV enable warning: {e}")


def write_token(root_token):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        f.write(root_token)
    try:
        os.chmod(TOKEN_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass
    print(f"Token written to {TOKEN_FILE} ✓")


def setup():
    """One-time setup: init + unseal + enable KV + write token."""
    client = wait_for_vault()
    status = get_status(client)
    print(f"Vault status: initialized={status.get('initialized')}, sealed={status.get('sealed')}")

    if not status.get("initialized", False):
        keys = initialize_vault(client)
    else:
        print("Vault already initialized")
        keys = load_keys()

    unseal_key = keys["unseal_keys_b64"][0]
    root_token = keys["root_token"]

    if status.get("sealed", True):
        unseal_vault(client, unseal_key)

    enable_kv(client, root_token)
    write_token(root_token)
    print("Vault initialization complete ✓")
    return unseal_key, root_token


def watch_loop(unseal_key):
    """
    Daemon loop — checks every 10 seconds and re-unseals if Vault was restarted.
    This is what makes Vault persistent across restarts.
    """
    print("Starting Vault watchdog (auto-unseal on restart)...")
    while True:
        time.sleep(10)
        try:
            client = hvac.Client(url=VAULT_ADDR)
            status = get_status(client)
            if status.get("sealed", False):
                print("Vault is sealed — auto-unsealing...")
                unseal_vault(client, unseal_key)
        except Exception as e:
            print(f"Watchdog check failed: {e}")


if __name__ == "__main__":
    unseal_key, root_token = setup()
    watch_loop(unseal_key)
