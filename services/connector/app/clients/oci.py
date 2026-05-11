"""OCI (Oracle Cloud Infrastructure) cloud provider client."""

import asyncio
import hashlib
import json
import logging
from typing import Any, Callable

from .base import CloudClientBase
from ..services.resilience import (
    CircuitBreakerOpenException,
    classify_oci,
    resilient_call,
)

logger = logging.getLogger(__name__)


class OCIClient(CloudClientBase):
    """
    OCI API client for resource discovery.

    Discovered resource types:
      Compute:        Instance
      Networking:     Vcn, Subnet, SecurityList, NetworkSecurityGroup
      Storage:        Bucket (Object Storage), BootVolume, BlockVolume
      Database:       AutonomousDatabase, DbSystem
      Serverless:     FunctionApplication
      Kubernetes:     OkeCluster
      Security:       Vault, Key
      Load Balancing: LoadBalancer, NetworkLoadBalancer
      Identity:       User, Group, Policy, DynamicGroup
    """

    def __init__(self, credentials: dict[str, Any], config: dict[str, Any] | None = None):
        self._credentials = credentials
        self._config = config or {}
        # Accept multiple key name variants for tenancy
        self._tenancy_ocid = (
            credentials.get("tenancy_ocid")
            or credentials.get("tenancy_id")
            or credentials.get("account_id")   # passed by discovery service
            or ""
        )
        # Accept multiple key name variants for user
        self._user_ocid = (
            credentials.get("user_ocid")
            or credentials.get("user_id")
            or ""
        )
        self._fingerprint = credentials.get("fingerprint") or ""
        # Accept both "private_key" and "key_content"
        self._private_key = (
            credentials.get("private_key")
            or credentials.get("key_content")
            or ""
        )
        self._region = (
            credentials.get("region")
            or (config.get("region") if config else None)
            or "us-ashburn-1"
        )
        self._oci_config: dict | None = None
        self._compartments: list[str] = []

    async def _call(self, service: str, func: Callable[..., Any], **kwargs: Any) -> Any:
        """Wrap an OCI SDK call with retry + circuit breaker.

        OCI SDK methods are sync — this helper awaits them correctly via the
        shared ``resilient_call`` and translates ``oci.exceptions.ServiceError``
        into retryable categories.
        """
        return await resilient_call(
            provider="oci",
            service=service,
            func=func,
            classify=classify_oci,
            **kwargs,
        )

    # ─── Connection ───────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Build OCI config dict and verify connectivity via identity client."""
        try:
            import oci  # noqa: F401 — verify SDK is installed
        except ImportError:
            logger.error("oci SDK not installed. Run: pip install oci")
            return False

        # tenancy_ocid can come from credentials dict OR be set directly
        # (discovery.py passes account.account_id separately)
        if not self._tenancy_ocid:
            logger.error("OCI tenancy_ocid not set")
            return False

        if not all([self._user_ocid, self._fingerprint, self._private_key]):
            logger.error(
                f"OCI credentials incomplete — have: "
                f"tenancy_ocid={'yes' if self._tenancy_ocid else 'NO'}, "
                f"user_ocid={'yes' if self._user_ocid else 'NO'}, "
                f"fingerprint={'yes' if self._fingerprint else 'NO'}, "
                f"private_key={'yes' if self._private_key else 'NO'}"
            )
            return False

        self._oci_config = {
            "tenancy": self._tenancy_ocid,
            "user": self._user_ocid,
            "fingerprint": self._fingerprint,
            "key_content": self._normalize_private_key(self._private_key),
            "region": self._region,
        }

        try:
            import oci
            identity_client = oci.identity.IdentityClient(self._oci_config)
            # Verify credentials by fetching tenancy
            tenancy = identity_client.get_tenancy(self._tenancy_ocid).data
            logger.info(f"Connected to OCI tenancy: {tenancy.name} ({self._tenancy_ocid})")

            # Pre-fetch all compartments (including root)
            self._compartments = [self._tenancy_ocid]
            try:
                compartments = oci.pagination.list_call_get_all_results(
                    identity_client.list_compartments,
                    self._tenancy_ocid,
                    compartment_id_in_subtree=True,
                    lifecycle_state="ACTIVE",
                ).data
                self._compartments.extend([c.id for c in compartments])
            except Exception as e:
                logger.warning(f"Could not list compartments: {e}")

            logger.info(f"Discovered {len(self._compartments)} compartments")
            return True
        except Exception as e:
            logger.error(f"OCI connect failed: {type(e).__name__}: {str(e)[:300]}")
            return False

    async def disconnect(self) -> None:
        self._oci_config = None
        self._compartments = []

    def get_account_id(self) -> str:
        return self._tenancy_ocid

    # ─── Resource discovery ───────────────────────────────────────────────────

    async def list_resources(self, region: str | None = None) -> list[dict[str, Any]]:
        """Discover all supported OCI resource types across all compartments."""
        if not self._oci_config:
            await self.connect()

        if not self._oci_config:
            return []

        # Use specified region or the configured one
        target_region = region if region and region != "global" else self._region
        cfg = {**self._oci_config, "region": target_region}

        tasks = [
            self._discover_compute(cfg),
            self._discover_networking(cfg),
            self._discover_object_storage(cfg),
            self._discover_block_storage(cfg),
            self._discover_database(cfg),
            self._discover_functions(cfg),
            self._discover_kubernetes(cfg),
            self._discover_vault(cfg),
            self._discover_load_balancer(cfg),
            self._discover_identity(cfg),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        resources: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, list):
                resources.extend(result)
            elif isinstance(result, Exception):
                logger.debug(f"OCI discovery task failed: {result}")

        logger.info(f"OCI total discovered: {len(resources)} resources in {target_region}")
        return resources

    # ─── Compute ──────────────────────────────────────────────────────────────

    async def _discover_compute(self, cfg: dict) -> list[dict[str, Any]]:
        resources = []
        try:
            import oci
            client = oci.core.ComputeClient(cfg)
            for compartment_id in self._compartments:
                try:
                    instances = oci.pagination.list_call_get_all_results(
                        client.list_instances,
                        compartment_id,
                        lifecycle_state="RUNNING",
                    ).data
                    for inst in instances:
                        resources.append({
                            "type": "Instance",
                            "id": inst.id,
                            "name": inst.display_name or inst.id,
                            "region": cfg["region"],
                            "tags": inst.freeform_tags or {},
                            "raw": {
                                "id": inst.id,
                                "display_name": inst.display_name,
                                "shape": inst.shape,
                                "lifecycle_state": inst.lifecycle_state,
                                "availability_domain": inst.availability_domain,
                                "compartment_id": compartment_id,
                            },
                        })
                except Exception as e:
                    logger.debug(f"Compute compartment {compartment_id}: {e}")
            if resources:
                logger.info(f"OCI: discovered {len(resources)} compute instances in {cfg['region']}")
        except Exception as e:
            logger.warning(f"OCI compute discovery failed: {e}")
        return resources

    # ─── Networking ───────────────────────────────────────────────────────────

    async def _discover_networking(self, cfg: dict) -> list[dict[str, Any]]:
        resources = []
        try:
            import oci
            client = oci.core.VirtualNetworkClient(cfg)
            for compartment_id in self._compartments:
                try:
                    # VCNs
                    vcns = oci.pagination.list_call_get_all_results(
                        client.list_vcns, compartment_id, lifecycle_state="AVAILABLE"
                    ).data
                    for vcn in vcns:
                        resources.append({
                            "type": "Vcn",
                            "id": vcn.id,
                            "name": vcn.display_name or vcn.id,
                            "region": cfg["region"],
                            "tags": vcn.freeform_tags or {},
                            "raw": {"id": vcn.id, "cidr_block": vcn.cidr_block, "display_name": vcn.display_name},
                        })

                    # Subnets
                    subnets = oci.pagination.list_call_get_all_results(
                        client.list_subnets, compartment_id, lifecycle_state="AVAILABLE"
                    ).data
                    for subnet in subnets:
                        resources.append({
                            "type": "Subnet",
                            "id": subnet.id,
                            "name": subnet.display_name or subnet.id,
                            "region": cfg["region"],
                            "tags": subnet.freeform_tags or {},
                            "raw": {"id": subnet.id, "cidr_block": subnet.cidr_block, "prohibit_public_ip_on_vnic": subnet.prohibit_public_ip_on_vnic},
                        })

                    # Security Lists
                    slists = oci.pagination.list_call_get_all_results(
                        client.list_security_lists, compartment_id, lifecycle_state="AVAILABLE"
                    ).data
                    for sl in slists:
                        resources.append({
                            "type": "SecurityList",
                            "id": sl.id,
                            "name": sl.display_name or sl.id,
                            "region": cfg["region"],
                            "tags": sl.freeform_tags or {},
                            "raw": {"id": sl.id, "ingress_security_rules": len(sl.ingress_security_rules or [])},
                        })

                    # Network Security Groups
                    nsgs = oci.pagination.list_call_get_all_results(
                        client.list_network_security_groups, compartment_id, lifecycle_state="AVAILABLE"
                    ).data
                    for nsg in nsgs:
                        resources.append({
                            "type": "NetworkSecurityGroup",
                            "id": nsg.id,
                            "name": nsg.display_name or nsg.id,
                            "region": cfg["region"],
                            "tags": nsg.freeform_tags or {},
                            "raw": {"id": nsg.id, "display_name": nsg.display_name},
                        })
                except Exception as e:
                    logger.debug(f"Networking compartment {compartment_id}: {e}")
            if resources:
                logger.info(f"OCI: discovered {len(resources)} networking resources in {cfg['region']}")
        except Exception as e:
            logger.warning(f"OCI networking discovery failed: {e}")
        return resources

    # ─── Object Storage ───────────────────────────────────────────────────────

    async def _discover_object_storage(self, cfg: dict) -> list[dict[str, Any]]:
        resources = []
        try:
            import oci
            client = oci.object_storage.ObjectStorageClient(cfg)
            namespace = client.get_namespace().data

            for compartment_id in self._compartments:
                try:
                    buckets = oci.pagination.list_call_get_all_results(
                        client.list_buckets, namespace, compartment_id
                    ).data
                    for bucket in buckets:
                        resources.append({
                            "type": "Bucket",
                            "id": f"oci::objectstorage::{namespace}::{bucket.name}",
                            "name": bucket.name,
                            "region": cfg["region"],
                            "tags": bucket.freeform_tags or {},
                            "raw": {
                                "name": bucket.name,
                                "namespace": namespace,
                                "compartment_id": compartment_id,
                                "public_access_type": getattr(bucket, "public_access_type", "NoPublicAccess"),
                            },
                        })
                except Exception as e:
                    logger.debug(f"Object storage compartment {compartment_id}: {e}")
            if resources:
                logger.info(f"OCI: discovered {len(resources)} buckets in {cfg['region']}")
        except Exception as e:
            logger.warning(f"OCI object storage discovery failed: {e}")
        return resources

    # ─── Block Storage ────────────────────────────────────────────────────────

    async def _discover_block_storage(self, cfg: dict) -> list[dict[str, Any]]:
        resources = []
        try:
            import oci
            client = oci.core.BlockstorageClient(cfg)
            for compartment_id in self._compartments:
                try:
                    volumes = oci.pagination.list_call_get_all_results(
                        client.list_volumes, compartment_id, lifecycle_state="AVAILABLE"
                    ).data
                    for vol in volumes:
                        resources.append({
                            "type": "BlockVolume",
                            "id": vol.id,
                            "name": vol.display_name or vol.id,
                            "region": cfg["region"],
                            "tags": vol.freeform_tags or {},
                            "raw": {"id": vol.id, "size_in_gbs": vol.size_in_gbs, "is_auto_tune_enabled": getattr(vol, "is_auto_tune_enabled", False)},
                        })
                except Exception as e:
                    logger.debug(f"Block storage compartment {compartment_id}: {e}")
        except Exception as e:
            logger.warning(f"OCI block storage discovery failed: {e}")
        return resources

    # ─── Database ─────────────────────────────────────────────────────────────

    async def _discover_database(self, cfg: dict) -> list[dict[str, Any]]:
        resources = []
        try:
            import oci
            client = oci.database.DatabaseClient(cfg)
            for compartment_id in self._compartments:
                try:
                    # Autonomous Databases
                    adbs = oci.pagination.list_call_get_all_results(
                        client.list_autonomous_databases,
                        compartment_id,
                        lifecycle_state="AVAILABLE",
                    ).data
                    for db in adbs:
                        resources.append({
                            "type": "AutonomousDatabase",
                            "id": db.id,
                            "name": db.display_name or db.id,
                            "region": cfg["region"],
                            "tags": db.freeform_tags or {},
                            "raw": {
                                "id": db.id,
                                "db_name": db.db_name,
                                "is_free_tier": db.is_free_tier,
                                "is_dedicated": getattr(db, "is_dedicated", False),
                                "cpu_core_count": db.cpu_core_count,
                            },
                        })

                    # DB Systems (Oracle DB)
                    db_systems = oci.pagination.list_call_get_all_results(
                        client.list_db_systems,
                        compartment_id,
                        lifecycle_state="AVAILABLE",
                    ).data
                    for dbs in db_systems:
                        resources.append({
                            "type": "DbSystem",
                            "id": dbs.id,
                            "name": dbs.display_name or dbs.id,
                            "region": cfg["region"],
                            "tags": dbs.freeform_tags or {},
                            "raw": {"id": dbs.id, "shape": dbs.shape, "node_count": dbs.node_count},
                        })
                except Exception as e:
                    logger.debug(f"Database compartment {compartment_id}: {e}")
            if resources:
                logger.info(f"OCI: discovered {len(resources)} database resources in {cfg['region']}")
        except Exception as e:
            logger.warning(f"OCI database discovery failed: {e}")
        return resources

    # ─── Functions ────────────────────────────────────────────────────────────

    async def _discover_functions(self, cfg: dict) -> list[dict[str, Any]]:
        resources = []
        try:
            import oci
            client = oci.functions.FunctionsManagementClient(cfg)
            for compartment_id in self._compartments:
                try:
                    apps = oci.pagination.list_call_get_all_results(
                        client.list_applications, compartment_id, lifecycle_state="ACTIVE"
                    ).data
                    for app in apps:
                        resources.append({
                            "type": "FunctionApplication",
                            "id": app.id,
                            "name": app.display_name or app.id,
                            "region": cfg["region"],
                            "tags": app.freeform_tags or {},
                            "raw": {"id": app.id, "display_name": app.display_name},
                        })
                except Exception as e:
                    logger.debug(f"Functions compartment {compartment_id}: {e}")
        except Exception as e:
            logger.warning(f"OCI functions discovery failed: {e}")
        return resources

    # ─── Kubernetes (OKE) ─────────────────────────────────────────────────────

    async def _discover_kubernetes(self, cfg: dict) -> list[dict[str, Any]]:
        resources = []
        try:
            import oci
            client = oci.container_engine.ContainerEngineClient(cfg)
            for compartment_id in self._compartments:
                try:
                    clusters = oci.pagination.list_call_get_all_results(
                        client.list_clusters, compartment_id, lifecycle_state=["ACTIVE"]
                    ).data
                    for cluster in clusters:
                        resources.append({
                            "type": "OkeCluster",
                            "id": cluster.id,
                            "name": cluster.name or cluster.id,
                            "region": cfg["region"],
                            "tags": cluster.freeform_tags or {},
                            "raw": {"id": cluster.id, "kubernetes_version": cluster.kubernetes_version},
                        })
                except Exception as e:
                    logger.debug(f"OKE compartment {compartment_id}: {e}")
        except Exception as e:
            logger.warning(f"OCI Kubernetes discovery failed: {e}")
        return resources

    # ─── Vault / KMS ─────────────────────────────────────────────────────────

    async def _discover_vault(self, cfg: dict) -> list[dict[str, Any]]:
        resources = []
        try:
            import oci
            vault_client = oci.key_management.KmsVaultClient(cfg)
            for compartment_id in self._compartments:
                try:
                    vaults = oci.pagination.list_call_get_all_results(
                        vault_client.list_vaults, compartment_id, lifecycle_state="ACTIVE"
                    ).data
                    for v in vaults:
                        resources.append({
                            "type": "Vault",
                            "id": v.id,
                            "name": v.display_name or v.id,
                            "region": cfg["region"],
                            "tags": v.freeform_tags or {},
                            "raw": {"id": v.id, "vault_type": v.vault_type},
                        })

                        # Secrets within each vault
                        try:
                            secrets_client = oci.vault.VaultsClient(cfg)
                            secrets = oci.pagination.list_call_get_all_results(
                                secrets_client.list_secrets,
                                compartment_id,
                                vault_id=v.id,
                                lifecycle_state="ACTIVE",
                            ).data
                            for secret in secrets:
                                resources.append({
                                    "type": "VaultSecret",
                                    "id": secret.id,
                                    "name": secret.secret_name or secret.id,
                                    "region": cfg["region"],
                                    "tags": secret.freeform_tags or {},
                                    "raw": {
                                        "id": secret.id,
                                        "secret_name": secret.secret_name,
                                        "vault_id": v.id,
                                        "lifecycle_state": secret.lifecycle_state,
                                    },
                                })
                        except Exception as e:
                            logger.debug(f"OCI vault secrets for {v.id}: {e}")

                except Exception as e:
                    logger.debug(f"Vault compartment {compartment_id}: {e}")
        except Exception as e:
            logger.warning(f"OCI vault discovery failed: {e}")
        return resources

    # ─── Load Balancer ────────────────────────────────────────────────────────

    async def _discover_load_balancer(self, cfg: dict) -> list[dict[str, Any]]:
        resources = []
        try:
            import oci
            client = oci.load_balancer.LoadBalancerClient(cfg)
            for compartment_id in self._compartments:
                try:
                    lbs = oci.pagination.list_call_get_all_results(
                        client.list_load_balancers, compartment_id, lifecycle_state="ACTIVE"
                    ).data
                    for lb in lbs:
                        is_public = bool(lb.ip_addresses and any(
                            getattr(ip, "is_public", False) for ip in lb.ip_addresses
                        ))
                        resources.append({
                            "type": "LoadBalancer",
                            "id": lb.id,
                            "name": lb.display_name or lb.id,
                            "region": cfg["region"],
                            "tags": lb.freeform_tags or {},
                            "is_public": is_public,
                            "raw": {
                                "id": lb.id,
                                "shape_name": lb.shape_name,
                                "is_private": lb.is_private,
                            },
                        })
                except Exception as e:
                    logger.debug(f"LB compartment {compartment_id}: {e}")
        except Exception as e:
            logger.warning(f"OCI load balancer discovery failed: {e}")
        return resources

    # ─── Identity ─────────────────────────────────────────────────────────────

    async def _discover_identity(self, cfg: dict) -> list[dict[str, Any]]:
        """Discover IAM users, groups, policies, dynamic groups (tenancy-level)."""
        resources = []
        try:
            import oci
            client = oci.identity.IdentityClient(cfg)

            # Users
            try:
                users = oci.pagination.list_call_get_all_results(
                    client.list_users, self._tenancy_ocid, lifecycle_state="ACTIVE"
                ).data
                for user in users:
                    resources.append({
                        "type": "User",
                        "id": user.id,
                        "name": user.name,
                        "region": "global",
                        "tags": user.freeform_tags or {},
                        "raw": {
                            "id": user.id,
                            "name": user.name,
                            "is_mfa_activated": user.is_mfa_activated,
                            "can_use_console_password": user.can_use_console_password,
                        },
                    })
            except Exception as e:
                logger.debug(f"OCI users: {e}")

            # Groups
            try:
                groups = oci.pagination.list_call_get_all_results(
                    client.list_groups, self._tenancy_ocid, lifecycle_state="ACTIVE"
                ).data
                for group in groups:
                    resources.append({
                        "type": "Group",
                        "id": group.id,
                        "name": group.name,
                        "region": "global",
                        "tags": group.freeform_tags or {},
                        "raw": {"id": group.id, "name": group.name},
                    })
            except Exception as e:
                logger.debug(f"OCI groups: {e}")

            # Policies
            try:
                policies = oci.pagination.list_call_get_all_results(
                    client.list_policies, self._tenancy_ocid, lifecycle_state="ACTIVE"
                ).data
                for policy in policies:
                    resources.append({
                        "type": "Policy",
                        "id": policy.id,
                        "name": policy.name,
                        "region": "global",
                        "tags": policy.freeform_tags or {},
                        "raw": {"id": policy.id, "name": policy.name, "statements": policy.statements},
                    })
            except Exception as e:
                logger.debug(f"OCI policies: {e}")

            # Dynamic Groups
            try:
                dgs = oci.pagination.list_call_get_all_results(
                    client.list_dynamic_groups, self._tenancy_ocid, lifecycle_state="ACTIVE"
                ).data
                for dg in dgs:
                    resources.append({
                        "type": "DynamicGroup",
                        "id": dg.id,
                        "name": dg.name,
                        "region": "global",
                        "tags": dg.freeform_tags or {},
                        "raw": {"id": dg.id, "name": dg.name, "matching_rule": dg.matching_rule},
                    })
            except Exception as e:
                logger.debug(f"OCI dynamic groups: {e}")

            if resources:
                logger.info(f"OCI: discovered {len(resources)} identity resources")
        except Exception as e:
            logger.warning(f"OCI identity discovery failed: {e}")
        return resources

    # ─── Hashing ──────────────────────────────────────────────────────────────

    def _normalize_private_key(self, key: str) -> str:
        """
        Normalize private key to PEM format.

        Handles:
        - Already-valid PEM (-----BEGIN ... KEY-----)
        - Raw base64 DER (PKCS#8 or PKCS#1) — wraps in PEM headers
        - Key with escaped newlines (\\n) — replaces with real newlines
        """
        if not key:
            return key

        # Replace escaped newlines
        key = key.replace("\\n", "\n").strip()

        # Already PEM
        if "-----BEGIN" in key:
            return key

        # Raw base64 — try to detect PKCS#8 vs PKCS#1 by decoding header
        try:
            import base64
            # Strip any whitespace/newlines from the base64 string
            b64 = key.replace("\n", "").replace("\r", "").replace(" ", "")
            der = base64.b64decode(b64)

            # PKCS#8 starts with 30 82 (SEQUENCE) and contains OID for RSA
            # PKCS#1 RSA private key starts with 30 82 as well but different structure
            # Use cryptography library to detect
            try:
                from cryptography.hazmat.primitives.serialization import (
                    load_der_private_key, Encoding, PrivateFormat, NoEncryption
                )
                private_key = load_der_private_key(der, password=None)
                pem = private_key.private_bytes(
                    encoding=Encoding.PEM,
                    format=PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=NoEncryption(),
                )
                return pem.decode("utf-8")
            except Exception:
                pass

            # Fallback: wrap as PKCS#8 PEM
            # Re-chunk into 64-char lines
            chunks = [b64[i:i+64] for i in range(0, len(b64), 64)]
            pem_body = "\n".join(chunks)
            return f"-----BEGIN PRIVATE KEY-----\n{pem_body}\n-----END PRIVATE KEY-----\n"

        except Exception as e:
            logger.debug(f"Key normalization fallback: {e}")
            return key

    def compute_resource_hash(self, resource: dict[str, Any]) -> str:
        content = json.dumps({
            "cloud_resource_id": resource.get("id"),
            "resource_type": resource.get("type"),
            "name": resource.get("name"),
            "region": resource.get("region"),
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
