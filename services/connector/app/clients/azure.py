"""Azure cloud provider client using Azure SDK."""

import asyncio
import hashlib
import json
import logging
from typing import Any

from .base import CloudClientBase

logger = logging.getLogger(__name__)


def _safe_dict(obj: Any) -> dict:
    """Safely convert an Azure SDK model to a plain dict."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    try:
        # Azure SDK models have .as_dict() or serialize()
        if hasattr(obj, "as_dict"):
            return obj.as_dict()
        if hasattr(obj, "serialize"):
            return obj.serialize()
        # Fallback: use __dict__ but filter private attrs
        return {k: str(v) for k, v in vars(obj).items() if not k.startswith("_")}
    except Exception:
        return {"id": getattr(obj, "id", ""), "name": getattr(obj, "name", "")}


class AzureClient(CloudClientBase):
    """
    Azure API client for resource discovery.

    Discovered resource types:
      Compute:    VirtualMachine, VirtualMachineScaleSet, Disk
      Network:    VirtualNetwork, Subnet, NetworkSecurityGroup, PublicIPAddress,
                  LoadBalancer, ApplicationGateway, FirewallPolicy
      Storage:    StorageAccount, BlobContainer
      Database:   SqlServer, SqlDatabase, CosmosDBAccount, PostgreSQLServer,
                  MySQLServer, RedisCache
      Security:   KeyVault
      Containers: ContainerRegistry, KubernetesService (AKS)
      Messaging:  EventHubNamespace, ServiceBusNamespace
      Identity:   RoleAssignment
      Serverless: FunctionApp, AppService
    """

    def __init__(self, credentials: dict[str, Any], subscription_id: str = ""):
        self._credentials = credentials
        # subscription_id can come from the account record or credentials dict
        self._subscription_id = (
            subscription_id
            or credentials.get("subscription_id")
            or credentials.get("account_id")
            or ""
        )
        self._tenant_id = credentials.get("tenant_id") or ""
        self._client_id = credentials.get("client_id") or ""
        self._client_secret = credentials.get("client_secret") or ""
        self._credential = None

    async def connect(self) -> bool:
        """Authenticate using service principal credentials."""
        try:
            from azure.identity import ClientSecretCredential, DefaultAzureCredential

            if self._client_id and self._client_secret and self._tenant_id:
                self._credential = ClientSecretCredential(
                    tenant_id=self._tenant_id,
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                )
                logger.info(f"Azure: authenticated as service principal {self._client_id}")
            else:
                self._credential = DefaultAzureCredential()
                logger.info("Azure: using DefaultAzureCredential")

            if not self._subscription_id:
                logger.error("Azure: subscription_id is required")
                return False

            # Verify by listing resource groups
            from azure.mgmt.resource.aio import ResourceManagementClient
            async with ResourceManagementClient(self._credential, self._subscription_id) as client:
                rgs = []
                async for rg in client.resource_groups.list():
                    rgs.append(rg.name)
                    if len(rgs) >= 1:
                        break
            logger.info(f"Azure: connected to subscription {self._subscription_id}")
            return True
        except Exception as e:
            logger.error(f"Azure connect failed: {type(e).__name__}: {str(e)[:300]}")
            return False

    async def disconnect(self) -> None:
        self._credential = None

    def get_account_id(self) -> str:
        return self._subscription_id

    async def list_resources(self, region: str | None = None) -> list[dict[str, Any]]:
        """Discover all Azure resources across the subscription."""
        if not self._credential:
            await self.connect()
        if not self._credential:
            return []

        tasks = [
            self._discover_compute(),
            self._discover_network(),
            self._discover_storage(),
            self._discover_databases(),
            self._discover_keyvault(),
            self._discover_containers(),
            self._discover_messaging(),
            self._discover_identity(),
            self._discover_web(),
            self._discover_api_management(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        resources: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, list):
                resources.extend(result)
            elif isinstance(result, Exception):
                logger.debug(f"Azure discovery task error: {result}")

        logger.info(f"Azure: total discovered {len(resources)} resources in subscription {self._subscription_id}")
        return resources

    # ─── Compute ──────────────────────────────────────────────────────────────

    async def _discover_compute(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from azure.mgmt.compute.aio import ComputeManagementClient
            async with ComputeManagementClient(self._credential, self._subscription_id) as client:
                # Virtual Machines
                async for vm in client.virtual_machines.list_all():
                    resources.append({
                        "type": "VirtualMachine",
                        "id": vm.id,
                        "name": vm.name,
                        "region": vm.location,
                        "tags": vm.tags or {},
                        "raw": {
                            "id": vm.id,
                            "name": vm.name,
                            "location": vm.location,
                            "vm_size": vm.hardware_profile.vm_size if vm.hardware_profile else None,
                            "os_type": vm.storage_profile.os_disk.os_type if vm.storage_profile and vm.storage_profile.os_disk else None,
                            "provisioning_state": vm.provisioning_state,
                        },
                    })

                # Disks
                async for disk in client.disks.list():
                    resources.append({
                        "type": "Disk",
                        "id": disk.id,
                        "name": disk.name,
                        "region": disk.location,
                        "tags": disk.tags or {},
                        "raw": {
                            "id": disk.id,
                            "name": disk.name,
                            "disk_size_gb": disk.disk_size_gb,
                            "disk_state": disk.disk_state,
                            "encryption": _safe_dict(disk.encryption) if disk.encryption else {},
                        },
                    })

            if resources:
                logger.info(f"Azure: discovered {len(resources)} compute resources")
        except Exception as e:
            logger.warning(f"Azure compute discovery failed: {e}")
        return resources

    # ─── Network ──────────────────────────────────────────────────────────────

    async def _discover_network(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from azure.mgmt.network.aio import NetworkManagementClient
            async with NetworkManagementClient(self._credential, self._subscription_id) as client:
                # Virtual Networks
                async for vnet in client.virtual_networks.list_all():
                    resources.append({
                        "type": "VirtualNetwork",
                        "id": vnet.id,
                        "name": vnet.name,
                        "region": vnet.location,
                        "tags": vnet.tags or {},
                        "raw": {"id": vnet.id, "name": vnet.name, "address_space": _safe_dict(vnet.address_space)},
                    })

                # Network Security Groups
                async for nsg in client.network_security_groups.list_all():
                    # Check if any rule allows inbound from internet
                    is_public = False
                    if nsg.security_rules:
                        for rule in nsg.security_rules:
                            if (getattr(rule, "direction", "") == "Inbound" and
                                    getattr(rule, "access", "") == "Allow" and
                                    getattr(rule, "source_address_prefix", "") in ("*", "Internet", "0.0.0.0/0")):
                                is_public = True
                                break
                    resources.append({
                        "type": "NetworkSecurityGroup",
                        "id": nsg.id,
                        "name": nsg.name,
                        "region": nsg.location,
                        "tags": nsg.tags or {},
                        "is_public": is_public,
                        "raw": {"id": nsg.id, "name": nsg.name, "rules_count": len(nsg.security_rules or [])},
                    })

                # Public IP Addresses
                async for pip in client.public_ip_addresses.list_all():
                    resources.append({
                        "type": "PublicIPAddress",
                        "id": pip.id,
                        "name": pip.name,
                        "region": pip.location,
                        "tags": pip.tags or {},
                        "is_public": True,
                        "raw": {"id": pip.id, "ip_address": pip.ip_address, "allocation_method": str(pip.public_ip_allocation_method)},
                    })

                # Load Balancers
                async for lb in client.load_balancers.list_all():
                    resources.append({
                        "type": "LoadBalancer",
                        "id": lb.id,
                        "name": lb.name,
                        "region": lb.location,
                        "tags": lb.tags or {},
                        "raw": {"id": lb.id, "name": lb.name, "sku": _safe_dict(lb.sku)},
                    })

            if resources:
                logger.info(f"Azure: discovered {len(resources)} network resources")
        except Exception as e:
            logger.warning(f"Azure network discovery failed: {e}")
        return resources

    # ─── Storage ──────────────────────────────────────────────────────────────

    async def _discover_storage(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from azure.mgmt.storage.aio import StorageManagementClient
            async with StorageManagementClient(self._credential, self._subscription_id) as client:
                async for account in client.storage_accounts.list():
                    is_public = getattr(account, "allow_blob_public_access", False) or False
                    resources.append({
                        "type": "StorageAccount",
                        "id": account.id,
                        "name": account.name,
                        "region": account.location,
                        "tags": account.tags or {},
                        "is_public": is_public,
                        "raw": {
                            "id": account.id,
                            "name": account.name,
                            "kind": str(account.kind),
                            "sku": _safe_dict(account.sku),
                            "allow_blob_public_access": is_public,
                            "https_only": account.enable_https_traffic_only,
                        },
                    })
            if resources:
                logger.info(f"Azure: discovered {len(resources)} storage resources")
        except Exception as e:
            logger.warning(f"Azure storage discovery failed: {e}")
        return resources

    # ─── Databases ────────────────────────────────────────────────────────────

    async def _discover_databases(self) -> list[dict[str, Any]]:
        resources = []

        # SQL Servers + Databases
        try:
            from azure.mgmt.sql.aio import SqlManagementClient
            async with SqlManagementClient(self._credential, self._subscription_id) as client:
                async for server in client.servers.list():
                    resources.append({
                        "type": "SqlServer",
                        "id": server.id,
                        "name": server.name,
                        "region": server.location,
                        "tags": server.tags or {},
                        "raw": {"id": server.id, "name": server.name, "fully_qualified_domain_name": server.fully_qualified_domain_name},
                    })
        except Exception as e:
            logger.debug(f"Azure SQL discovery: {e}")

        # Cosmos DB
        try:
            from azure.mgmt.cosmosdb.aio import CosmosDBManagementClient
            async with CosmosDBManagementClient(self._credential, self._subscription_id) as client:
                async for account in client.database_accounts.list():
                    resources.append({
                        "type": "CosmosDBAccount",
                        "id": account.id,
                        "name": account.name,
                        "region": account.location,
                        "tags": account.tags or {},
                        "raw": {"id": account.id, "name": account.name, "kind": str(account.kind)},
                    })
        except Exception as e:
            logger.debug(f"Azure CosmosDB discovery: {e}")

        if resources:
            logger.info(f"Azure: discovered {len(resources)} database resources")
        return resources

    # ─── Key Vault ────────────────────────────────────────────────────────────

    async def _discover_keyvault(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from azure.mgmt.keyvault.aio import KeyVaultManagementClient
            async with KeyVaultManagementClient(self._credential, self._subscription_id) as client:
                async for vault in client.vaults.list():
                    resources.append({
                        "type": "KeyVault",
                        "id": vault.id,
                        "name": vault.name,
                        "region": vault.location,
                        "tags": vault.tags or {},
                        "raw": {"id": vault.id, "name": vault.name},
                    })
            if resources:
                logger.info(f"Azure: discovered {len(resources)} key vaults")
        except Exception as e:
            logger.warning(f"Azure KeyVault discovery failed: {e}")
        return resources

    # ─── Containers ───────────────────────────────────────────────────────────

    async def _discover_containers(self) -> list[dict[str, Any]]:
        resources = []

        # Container Registry
        try:
            from azure.mgmt.containerregistry.aio import ContainerRegistryManagementClient
            async with ContainerRegistryManagementClient(self._credential, self._subscription_id) as client:
                async for registry in client.registries.list():
                    resources.append({
                        "type": "ContainerRegistry",
                        "id": registry.id,
                        "name": registry.name,
                        "region": registry.location,
                        "tags": registry.tags or {},
                        "raw": {"id": registry.id, "name": registry.name, "sku": _safe_dict(registry.sku)},
                    })
        except Exception as e:
            logger.debug(f"Azure ContainerRegistry discovery: {e}")

        # AKS
        try:
            from azure.mgmt.containerservice.aio import ContainerServiceClient
            async with ContainerServiceClient(self._credential, self._subscription_id) as client:
                async for cluster in client.managed_clusters.list():
                    resources.append({
                        "type": "KubernetesService",
                        "id": cluster.id,
                        "name": cluster.name,
                        "region": cluster.location,
                        "tags": cluster.tags or {},
                        "raw": {
                            "id": cluster.id,
                            "name": cluster.name,
                            "kubernetes_version": cluster.kubernetes_version,
                            "node_count": sum(p.count or 0 for p in (cluster.agent_pool_profiles or [])),
                        },
                    })
        except Exception as e:
            logger.debug(f"Azure AKS discovery: {e}")

        if resources:
            logger.info(f"Azure: discovered {len(resources)} container resources")
        return resources

    # ─── Messaging ────────────────────────────────────────────────────────────

    async def _discover_messaging(self) -> list[dict[str, Any]]:
        resources = []
        # Event Hubs
        try:
            from azure.mgmt.eventhub.aio import EventHubManagementClient
            async with EventHubManagementClient(self._credential, self._subscription_id) as client:
                async for ns in client.namespaces.list():
                    resources.append({
                        "type": "EventHubNamespace",
                        "id": ns.id,
                        "name": ns.name,
                        "region": ns.location,
                        "tags": ns.tags or {},
                        "raw": {"id": ns.id, "name": ns.name, "sku": _safe_dict(ns.sku)},
                    })
        except Exception as e:
            logger.debug(f"Azure EventHub discovery: {e}")

        # Service Bus
        try:
            from azure.mgmt.servicebus.aio import ServiceBusManagementClient  # type: ignore[import]
            async with ServiceBusManagementClient(self._credential, self._subscription_id) as client:
                async for ns in client.namespaces.list():
                    resources.append({
                        "type": "ServiceBusNamespace",
                        "id": ns.id,
                        "name": ns.name,
                        "region": ns.location,
                        "tags": ns.tags or {},
                        "raw": {"id": ns.id, "name": ns.name, "sku": _safe_dict(ns.sku) if ns.sku else {}},
                    })
        except ImportError:
            logger.debug("azure-mgmt-servicebus not installed — skipping Service Bus discovery")
        except Exception as e:
            logger.debug(f"Azure ServiceBus discovery: {e}")

        if resources:
            logger.info(f"Azure: discovered {len(resources)} messaging resources")
        return resources

    # ─── Identity ─────────────────────────────────────────────────────────────

    async def _discover_identity(self) -> list[dict[str, Any]]:
        resources = []
        # RBAC Role Assignments
        try:
            from azure.mgmt.authorization.aio import AuthorizationManagementClient
            async with AuthorizationManagementClient(self._credential, self._subscription_id) as client:
                count = 0
                async for ra in client.role_assignments.list_for_subscription():
                    resources.append({
                        "type": "RoleAssignment",
                        "id": ra.id,
                        "name": ra.name or ra.id,
                        "region": "global",
                        "tags": {},
                        "raw": {
                            "id": ra.id,
                            "principal_id": ra.principal_id,
                            "role_definition_id": ra.role_definition_id,
                            "scope": ra.scope,
                        },
                    })
                    count += 1
                    if count >= 200:  # cap to avoid huge payloads
                        break
            if resources:
                logger.info(f"Azure: discovered {len(resources)} role assignments")
        except Exception as e:
            logger.debug(f"Azure identity discovery: {e}")

        # Azure AD Users
        try:
            from msgraph.core import GraphClient  # type: ignore[import]
            graph_client = GraphClient(credential=self._credential)
            response = graph_client.get("/users?$top=100&$select=id,displayName,userPrincipalName,accountEnabled,createdDateTime")
            if response.status_code == 200:
                users_data = response.json().get("value", [])
                for user in users_data:
                    resources.append({
                        "type": "AzureADUser",
                        "id": f"/tenants/{self._tenant_id}/users/{user['id']}",
                        "name": user.get("displayName") or user.get("userPrincipalName", ""),
                        "region": "global",
                        "tags": {},
                        "raw": {
                            "id": user["id"],
                            "display_name": user.get("displayName"),
                            "user_principal_name": user.get("userPrincipalName"),
                            "account_enabled": user.get("accountEnabled"),
                        },
                    })
        except ImportError:
            # msgraph-core not installed — use REST directly
            try:
                import httpx
                token = self._credential.get_token("https://graph.microsoft.com/.default")
                headers = {"Authorization": f"Bearer {token.token}"}
                async with httpx.AsyncClient() as http:
                    resp = await http.get(
                        "https://graph.microsoft.com/v1.0/users?$top=100&$select=id,displayName,userPrincipalName,accountEnabled",
                        headers=headers,
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        for user in resp.json().get("value", []):
                            resources.append({
                                "type": "AzureADUser",
                                "id": f"/tenants/{self._tenant_id}/users/{user['id']}",
                                "name": user.get("displayName") or user.get("userPrincipalName", ""),
                                "region": "global",
                                "tags": {},
                                "raw": {
                                    "id": user["id"],
                                    "display_name": user.get("displayName"),
                                    "user_principal_name": user.get("userPrincipalName"),
                                    "account_enabled": user.get("accountEnabled"),
                                },
                            })
            except Exception as e:
                logger.debug(f"Azure AD Users discovery: {e}")
        except Exception as e:
            logger.debug(f"Azure AD Users discovery: {e}")

        # Azure AD Service Principals
        try:
            import httpx
            token = self._credential.get_token("https://graph.microsoft.com/.default")
            headers = {"Authorization": f"Bearer {token.token}"}
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    "https://graph.microsoft.com/v1.0/servicePrincipals?$top=100&$select=id,displayName,appId,servicePrincipalType,accountEnabled",
                    headers=headers,
                    timeout=30,
                )
                if resp.status_code == 200:
                    for sp in resp.json().get("value", []):
                        resources.append({
                            "type": "ServicePrincipal",
                            "id": f"/tenants/{self._tenant_id}/servicePrincipals/{sp['id']}",
                            "name": sp.get("displayName", ""),
                            "region": "global",
                            "tags": {},
                            "raw": {
                                "id": sp["id"],
                                "display_name": sp.get("displayName"),
                                "app_id": sp.get("appId"),
                                "service_principal_type": sp.get("servicePrincipalType"),
                                "account_enabled": sp.get("accountEnabled"),
                            },
                        })
        except Exception as e:
            logger.debug(f"Azure Service Principals discovery: {e}")

        return resources

    # ─── API Management ───────────────────────────────────────────────────────

    async def _discover_api_management(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from azure.mgmt.apimanagement.aio import ApiManagementClient  # type: ignore[import]
            async with ApiManagementClient(self._credential, self._subscription_id) as client:
                async for svc in client.api_management_service.list():
                    resources.append({
                        "type": "APIManagement",
                        "id": svc.id,
                        "name": svc.name,
                        "region": svc.location,
                        "tags": svc.tags or {},
                        "raw": {
                            "id": svc.id,
                            "name": svc.name,
                            "sku": _safe_dict(svc.sku) if svc.sku else {},
                            "gateway_url": getattr(svc, "gateway_url", None),
                        },
                    })
            if resources:
                logger.info(f"Azure: discovered {len(resources)} API Management services")
        except ImportError:
            logger.debug("azure-mgmt-apimanagement not installed — skipping API Management discovery")
        except Exception as e:
            logger.debug(f"Azure API Management discovery: {e}")
        return resources

    # ─── Web / Serverless ─────────────────────────────────────────────────────

    async def _discover_web(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from azure.mgmt.web.aio import WebSiteManagementClient
            async with WebSiteManagementClient(self._credential, self._subscription_id) as client:
                async for app in client.web_apps.list():
                    resources.append({
                        "type": "AppService" if not getattr(app, "kind", "").startswith("functionapp") else "FunctionApp",
                        "id": app.id,
                        "name": app.name,
                        "region": app.location,
                        "tags": app.tags or {},
                        "raw": {
                            "id": app.id,
                            "name": app.name,
                            "kind": app.kind,
                            "state": app.state,
                            "https_only": app.https_only,
                        },
                    })
            if resources:
                logger.info(f"Azure: discovered {len(resources)} web/function apps")
        except Exception as e:
            logger.debug(f"Azure web discovery: {e}")
        return resources

    # ─── Hashing ──────────────────────────────────────────────────────────────

    def compute_resource_hash(self, resource: dict[str, Any]) -> str:
        content = json.dumps({
            "cloud_resource_id": resource.get("id"),
            "resource_type": resource.get("type"),
            "name": resource.get("name"),
            "region": resource.get("region"),
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
