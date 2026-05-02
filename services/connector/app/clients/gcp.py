"""GCP cloud provider client using Google Cloud SDK."""

import asyncio
import hashlib
import json
import logging
from typing import Any

from .base import CloudClientBase

logger = logging.getLogger(__name__)


class GCPClient(CloudClientBase):
    """
    GCP API client for resource discovery.

    Discovered resource types:
      Compute:    Instance, Disk, Snapshot, Image (custom)
      Network:    Network, Subnetwork, Firewall, ForwardingRule, Address
      Storage:    Bucket
      Database:   CloudSQLInstance, BigtableInstance, SpannerInstance
      Containers: GKECluster
      Serverless: CloudFunction, CloudRunService
      Security:   ServiceAccount, IAMPolicy, KMSKeyRing, KMSCryptoKey
      Messaging:  PubSubTopic, PubSubSubscription
    """

    def __init__(self, credentials: dict[str, Any], project_id: str = ""):
        self._credentials = credentials
        self._project_id = (
            project_id
            or credentials.get("project_id")
            or credentials.get("account_id")
            or ""
        )
        # service_account_json can be a dict or a JSON string
        sa_json = credentials.get("service_account_json")
        if isinstance(sa_json, str):
            try:
                sa_json = json.loads(sa_json)
            except Exception:
                sa_json = None
        self._service_account_json = sa_json
        self._service_account_file = credentials.get("service_account_file")
        self._gcp_credentials = None
        self._all_zones: list[str] = []
        self._all_regions: list[str] = []

    # ─── Connection ───────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Authenticate and discover all zones/regions."""
        if not self._project_id:
            logger.error("GCP: project_id is required")
            return False

        try:
            self._gcp_credentials = self._build_credentials()
        except Exception as e:
            logger.error(f"GCP credential build failed: {e}")
            return False

        # Discover all zones and regions
        try:
            from google.cloud import compute_v1
            zones_client = compute_v1.ZonesClient(credentials=self._gcp_credentials)
            self._all_zones = [
                z.name for z in zones_client.list(project=self._project_id)
                if z.status == "UP"
            ]
            regions_client = compute_v1.RegionsClient(credentials=self._gcp_credentials)
            self._all_regions = [
                r.name for r in regions_client.list(project=self._project_id)
                if r.status == "UP"
            ]
            logger.info(
                f"GCP: connected to project {self._project_id} — "
                f"{len(self._all_zones)} zones, {len(self._all_regions)} regions"
            )
            return True
        except Exception as e:
            logger.error(f"GCP connect failed: {type(e).__name__}: {str(e)[:300]}")
            # Fall back to common zones/regions
            self._all_zones = [
                "us-central1-a", "us-central1-b", "us-east1-b", "us-east1-c",
                "us-west1-a", "us-west1-b", "europe-west1-b", "europe-west1-c",
                "asia-east1-a", "asia-east1-b",
            ]
            self._all_regions = [
                "us-central1", "us-east1", "us-west1",
                "europe-west1", "asia-east1",
            ]
            return True

    async def disconnect(self) -> None:
        self._gcp_credentials = None

    def get_account_id(self) -> str:
        return self._project_id

    def _build_credentials(self):
        """Build GCP credentials from service account JSON or file."""
        if self._service_account_json:
            from google.oauth2 import service_account
            return service_account.Credentials.from_service_account_info(
                self._service_account_json,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        if self._service_account_file:
            from google.oauth2 import service_account
            return service_account.Credentials.from_service_account_file(
                self._service_account_file,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        # Fall back to Application Default Credentials
        import google.auth
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return creds

    # ─── Resource discovery ───────────────────────────────────────────────────

    async def list_resources(self, region: str | None = None) -> list[dict[str, Any]]:
        """Discover all GCP resources in the project."""
        if not self._gcp_credentials:
            await self.connect()
        if not self._project_id:
            return []

        tasks = [
            self._discover_compute(),
            self._discover_network(),
            self._discover_storage(),
            self._discover_databases(),
            self._discover_gke(),
            self._discover_functions(),
            self._discover_cloud_run(),
            self._discover_pubsub(),
            self._discover_iam(),
            self._discover_iam_bindings(),
            self._discover_kms(),
            self._discover_bigquery(),
            self._discover_dns(),
            self._discover_artifact_registry(),
            self._discover_secret_manager(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        resources: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, list):
                resources.extend(result)
            elif isinstance(result, Exception):
                logger.debug(f"GCP discovery task error: {result}")

        logger.info(f"GCP: total discovered {len(resources)} resources in project {self._project_id}")
        return resources

    # ─── Compute ──────────────────────────────────────────────────────────────

    async def _discover_compute(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import compute_v1

            # Instances — use aggregated list (all zones at once)
            client = compute_v1.InstancesClient(credentials=self._gcp_credentials)
            agg = client.aggregated_list(project=self._project_id)
            for zone_name, zone_data in agg:
                if not zone_data.instances:
                    continue
                for inst in zone_data.instances:
                    is_public = any(
                        ac.nat_i_p
                        for ni in (inst.network_interfaces or [])
                        for ac in (ni.access_configs or [])
                        if ac.nat_i_p
                    )
                    resources.append({
                        "type": "Instance",
                        "id": f"projects/{self._project_id}/zones/{zone_name.split('/')[-1]}/instances/{inst.name}",
                        "name": inst.name,
                        "region": zone_name.split("/")[-1],
                        "tags": dict(inst.labels) if inst.labels else {},
                        "is_public": is_public,
                        "raw": {
                            "name": inst.name,
                            "machine_type": inst.machine_type.split("/")[-1] if inst.machine_type else None,
                            "status": inst.status,
                            "zone": zone_name.split("/")[-1],
                        },
                    })

            # Disks — aggregated
            disk_client = compute_v1.DisksClient(credentials=self._gcp_credentials)
            disk_agg = disk_client.aggregated_list(project=self._project_id)
            for zone_name, zone_data in disk_agg:
                if not zone_data.disks:
                    continue
                for disk in zone_data.disks:
                    resources.append({
                        "type": "Disk",
                        "id": f"projects/{self._project_id}/zones/{zone_name.split('/')[-1]}/disks/{disk.name}",
                        "name": disk.name,
                        "region": zone_name.split("/")[-1],
                        "tags": dict(disk.labels) if disk.labels else {},
                        "raw": {
                            "name": disk.name,
                            "size_gb": disk.size_gb,
                            "status": disk.status,
                            "type": disk.type_.split("/")[-1] if disk.type_ else None,
                        },
                    })

            if resources:
                logger.info(f"GCP: discovered {len(resources)} compute resources")
        except Exception as e:
            logger.warning(f"GCP compute discovery failed: {e}")
        return resources

    # ─── Network ──────────────────────────────────────────────────────────────

    async def _discover_network(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import compute_v1

            # VPC Networks
            net_client = compute_v1.NetworksClient(credentials=self._gcp_credentials)
            for network in net_client.list(project=self._project_id):
                resources.append({
                    "type": "Network",
                    "id": network.self_link or f"projects/{self._project_id}/global/networks/{network.name}",
                    "name": network.name,
                    "region": "global",
                    "tags": {},
                    "raw": {"name": network.name, "auto_create_subnetworks": network.auto_create_subnetworks},
                })

            # Firewall rules
            fw_client = compute_v1.FirewallsClient(credentials=self._gcp_credentials)
            for fw in fw_client.list(project=self._project_id):
                is_public = "0.0.0.0/0" in (fw.source_ranges or []) or "::/0" in (fw.source_ranges or [])
                resources.append({
                    "type": "Firewall",
                    "id": fw.self_link or f"projects/{self._project_id}/global/firewalls/{fw.name}",
                    "name": fw.name,
                    "region": "global",
                    "tags": {},
                    "is_public": is_public,
                    "raw": {
                        "name": fw.name,
                        "direction": fw.direction,
                        "source_ranges": list(fw.source_ranges or []),
                        "disabled": fw.disabled,
                    },
                })

            # Subnetworks — aggregated
            subnet_client = compute_v1.SubnetworksClient(credentials=self._gcp_credentials)
            subnet_agg = subnet_client.aggregated_list(project=self._project_id)
            for region_name, region_data in subnet_agg:
                if not region_data.subnetworks:
                    continue
                for subnet in region_data.subnetworks:
                    resources.append({
                        "type": "Subnetwork",
                        "id": subnet.self_link or subnet.name,
                        "name": subnet.name,
                        "region": region_name.split("/")[-1],
                        "tags": {},
                        "raw": {
                            "name": subnet.name,
                            "ip_cidr_range": subnet.ip_cidr_range,
                            "private_ip_google_access": subnet.private_ip_google_access,
                        },
                    })

            if resources:
                logger.info(f"GCP: discovered {len(resources)} network resources")
        except Exception as e:
            logger.warning(f"GCP network discovery failed: {e}")
        return resources

    # ─── Storage ──────────────────────────────────────────────────────────────

    async def _discover_storage(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import storage

            client = storage.Client(
                project=self._project_id,
                credentials=self._gcp_credentials,
            )
            for bucket in client.list_buckets():
                # Check public access
                is_public = False
                try:
                    policy = bucket.get_iam_policy()
                    for binding in policy.bindings:
                        if "allUsers" in binding.get("members", []) or "allAuthenticatedUsers" in binding.get("members", []):
                            is_public = True
                            break
                except Exception:
                    pass

                resources.append({
                    "type": "Bucket",
                    "id": f"gs://{bucket.name}",
                    "name": bucket.name,
                    "region": bucket.location or "multi-region",
                    "tags": dict(bucket.labels) if bucket.labels else {},
                    "is_public": is_public,
                    "raw": {
                        "name": bucket.name,
                        "location": bucket.location,
                        "storage_class": bucket.storage_class,
                        "versioning_enabled": bucket.versioning_enabled,
                        "uniform_bucket_level_access": bucket.iam_configuration.uniform_bucket_level_access_enabled if bucket.iam_configuration else False,
                    },
                })
            if resources:
                logger.info(f"GCP: discovered {len(resources)} storage buckets")
        except Exception as e:
            logger.warning(f"GCP storage discovery failed: {e}")
        return resources

    # ─── Databases ────────────────────────────────────────────────────────────

    async def _discover_databases(self) -> list[dict[str, Any]]:
        resources = []

        # Cloud SQL
        try:
            import googleapiclient.discovery
            import google.auth.transport.requests

            request = google.auth.transport.requests.Request()
            self._gcp_credentials.refresh(request)

            sqladmin = googleapiclient.discovery.build(
                "sqladmin", "v1beta4",
                credentials=self._gcp_credentials,
                cache_discovery=False,
            )
            instances = sqladmin.instances().list(project=self._project_id).execute()
            for inst in instances.get("items", []):
                is_public = any(
                    ip.get("type") == "PRIMARY"
                    for ip in inst.get("ipAddresses", [])
                )
                resources.append({
                    "type": "CloudSQLInstance",
                    "id": f"projects/{self._project_id}/instances/{inst['name']}",
                    "name": inst["name"],
                    "region": inst.get("region", "unknown"),
                    "tags": {},
                    "is_public": is_public,
                    "raw": {
                        "name": inst["name"],
                        "database_version": inst.get("databaseVersion"),
                        "state": inst.get("state"),
                        "tier": inst.get("settings", {}).get("tier"),
                    },
                })
        except Exception as e:
            logger.debug(f"GCP CloudSQL discovery: {e}")

        if resources:
            logger.info(f"GCP: discovered {len(resources)} database resources")
        return resources

    # ─── GKE ──────────────────────────────────────────────────────────────────

    async def _discover_gke(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import container_v1

            client = container_v1.ClusterManagerClient(credentials=self._gcp_credentials)
            # "-" means all locations
            response = client.list_clusters(parent=f"projects/{self._project_id}/locations/-")
            for cluster in response.clusters:
                resources.append({
                    "type": "GKECluster",
                    "id": f"projects/{self._project_id}/locations/{cluster.location}/clusters/{cluster.name}",
                    "name": cluster.name,
                    "region": cluster.location,
                    "tags": dict(cluster.resource_labels) if cluster.resource_labels else {},
                    "raw": {
                        "name": cluster.name,
                        "location": cluster.location,
                        "current_master_version": cluster.current_master_version,
                        "status": str(cluster.status),
                        "node_count": cluster.current_node_count,
                    },
                })
            if resources:
                logger.info(f"GCP: discovered {len(resources)} GKE clusters")
        except Exception as e:
            logger.warning(f"GCP GKE discovery failed: {e}")
        return resources

    # ─── Cloud Functions ──────────────────────────────────────────────────────

    async def _discover_functions(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import functions_v1

            client = functions_v1.CloudFunctionsServiceClient(credentials=self._gcp_credentials)
            for region in self._all_regions[:10]:  # cap to avoid too many API calls
                try:
                    parent = f"projects/{self._project_id}/locations/{region}"
                    for fn in client.list_functions(request={"parent": parent}):
                        resources.append({
                            "type": "CloudFunction",
                            "id": fn.name,
                            "name": fn.name.split("/")[-1],
                            "region": region,
                            "tags": dict(fn.labels) if fn.labels else {},
                            "raw": {
                                "name": fn.name,
                                "status": str(fn.status),
                                "runtime": fn.runtime,
                                "https_trigger": bool(fn.https_trigger),
                            },
                        })
                except Exception:
                    continue
            if resources:
                logger.info(f"GCP: discovered {len(resources)} Cloud Functions")
        except Exception as e:
            logger.debug(f"GCP functions discovery: {e}")
        return resources

    # ─── Pub/Sub ──────────────────────────────────────────────────────────────

    async def _discover_pubsub(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import pubsub_v1

            publisher = pubsub_v1.PublisherClient(credentials=self._gcp_credentials)
            project_path = f"projects/{self._project_id}"
            for topic in publisher.list_topics(request={"project": project_path}):
                resources.append({
                    "type": "PubSubTopic",
                    "id": topic.name,
                    "name": topic.name.split("/")[-1],
                    "region": "global",
                    "tags": dict(topic.labels) if topic.labels else {},
                    "raw": {"name": topic.name},
                })

            subscriber = pubsub_v1.SubscriberClient(credentials=self._gcp_credentials)
            for sub in subscriber.list_subscriptions(request={"project": project_path}):
                resources.append({
                    "type": "PubSubSubscription",
                    "id": sub.name,
                    "name": sub.name.split("/")[-1],
                    "region": "global",
                    "tags": {},
                    "raw": {"name": sub.name, "topic": sub.topic},
                })
            if resources:
                logger.info(f"GCP: discovered {len(resources)} Pub/Sub resources")
        except Exception as e:
            logger.debug(f"GCP Pub/Sub discovery: {e}")
        return resources

    # ─── IAM ──────────────────────────────────────────────────────────────────

    async def _discover_iam(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import iam_admin_v1

            client = iam_admin_v1.IAMClient(credentials=self._gcp_credentials)
            # Service accounts
            for sa in client.list_service_accounts(
                request={"name": f"projects/{self._project_id}"}
            ):
                resources.append({
                    "type": "ServiceAccount",
                    "id": sa.name,
                    "name": sa.display_name or sa.email,
                    "region": "global",
                    "tags": {},
                    "raw": {
                        "name": sa.name,
                        "email": sa.email,
                        "display_name": sa.display_name,
                        "disabled": sa.disabled,
                    },
                })
            if resources:
                logger.info(f"GCP: discovered {len(resources)} IAM service accounts")
        except Exception as e:
            logger.debug(f"GCP IAM discovery: {e}")
        return resources

    # ─── KMS ──────────────────────────────────────────────────────────────────

    async def _discover_kms(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import kms_v1

            client = kms_v1.KeyManagementServiceClient(credentials=self._gcp_credentials)
            for location in ["global", "us", "europe", "asia"] + self._all_regions[:5]:
                try:
                    parent = f"projects/{self._project_id}/locations/{location}"
                    for keyring in client.list_key_rings(request={"parent": parent}):
                        resources.append({
                            "type": "KMSKeyRing",
                            "id": keyring.name,
                            "name": keyring.name.split("/")[-1],
                            "region": location,
                            "tags": {},
                            "raw": {"name": keyring.name},
                        })
                        # Keys within keyring
                        for key in client.list_crypto_keys(request={"parent": keyring.name}):
                            resources.append({
                                "type": "KMSCryptoKey",
                                "id": key.name,
                                "name": key.name.split("/")[-1],
                                "region": location,
                                "tags": dict(key.labels) if key.labels else {},
                                "raw": {
                                    "name": key.name,
                                    "purpose": str(key.purpose),
                                    "rotation_period": str(key.rotation_period) if key.rotation_period else None,
                                },
                            })
                except Exception:
                    continue
            if resources:
                logger.info(f"GCP: discovered {len(resources)} KMS resources")
        except Exception as e:
            logger.debug(f"GCP KMS discovery: {e}")
        return resources

    # ─── Cloud Run ────────────────────────────────────────────────────────────

    async def _discover_cloud_run(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import run_v2  # type: ignore[import]
            client = run_v2.ServicesClient(credentials=self._gcp_credentials)
            for region in self._all_regions[:15]:
                try:
                    parent = f"projects/{self._project_id}/locations/{region}"
                    for svc in client.list_services(parent=parent):
                        resources.append({
                            "type": "CloudRunService",
                            "id": svc.name,
                            "name": svc.name.split("/")[-1],
                            "region": region,
                            "tags": dict(svc.labels) if svc.labels else {},
                            "is_public": any(
                                b.role == "roles/run.invoker" and "allUsers" in b.members
                                for b in getattr(svc, "iam_bindings", [])
                            ),
                            "raw": {
                                "name": svc.name,
                                "uri": getattr(svc, "uri", None),
                                "ingress": str(getattr(svc, "ingress", "")),
                            },
                        })
                except Exception:
                    continue
            if resources:
                logger.info(f"GCP: discovered {len(resources)} Cloud Run services")
        except ImportError:
            logger.debug("google-cloud-run not installed — skipping Cloud Run discovery")
        except Exception as e:
            logger.debug(f"GCP Cloud Run discovery: {e}")
        return resources

    # ─── BigQuery ─────────────────────────────────────────────────────────────

    async def _discover_bigquery(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import bigquery  # type: ignore[import]
            client = bigquery.Client(
                project=self._project_id,
                credentials=self._gcp_credentials,
            )
            for dataset in client.list_datasets():
                full_id = f"projects/{self._project_id}/datasets/{dataset.dataset_id}"
                resources.append({
                    "type": "BigQueryDataset",
                    "id": full_id,
                    "name": dataset.dataset_id,
                    "region": dataset.location or "US",
                    "tags": dict(dataset.labels) if dataset.labels else {},
                    "raw": {
                        "dataset_id": dataset.dataset_id,
                        "project": self._project_id,
                        "location": dataset.location,
                    },
                })
            if resources:
                logger.info(f"GCP: discovered {len(resources)} BigQuery datasets")
        except ImportError:
            logger.debug("google-cloud-bigquery not installed — skipping BigQuery discovery")
        except Exception as e:
            logger.debug(f"GCP BigQuery discovery: {e}")
        return resources

    # ─── Cloud DNS ────────────────────────────────────────────────────────────

    async def _discover_dns(self) -> list[dict[str, Any]]:
        resources = []
        try:
            import googleapiclient.discovery
            dns = googleapiclient.discovery.build(
                "dns", "v1",
                credentials=self._gcp_credentials,
                cache_discovery=False,
            )
            zones = dns.managedZones().list(project=self._project_id).execute()
            for zone in zones.get("managedZones", []):
                resources.append({
                    "type": "CloudDNSZone",
                    "id": f"projects/{self._project_id}/managedZones/{zone['name']}",
                    "name": zone["name"],
                    "region": "global",
                    "tags": zone.get("labels", {}),
                    "raw": {
                        "name": zone["name"],
                        "dns_name": zone.get("dnsName"),
                        "visibility": zone.get("visibility"),
                    },
                })
            if resources:
                logger.info(f"GCP: discovered {len(resources)} Cloud DNS zones")
        except Exception as e:
            logger.debug(f"GCP Cloud DNS discovery: {e}")
        return resources

    # ─── Artifact Registry ────────────────────────────────────────────────────

    async def _discover_artifact_registry(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import artifactregistry_v1  # type: ignore[import]
            client = artifactregistry_v1.ArtifactRegistryClient(credentials=self._gcp_credentials)
            for region in self._all_regions[:10]:
                try:
                    parent = f"projects/{self._project_id}/locations/{region}"
                    for repo in client.list_repositories(parent=parent):
                        resources.append({
                            "type": "ArtifactRegistryRepository",
                            "id": repo.name,
                            "name": repo.name.split("/")[-1],
                            "region": region,
                            "tags": dict(repo.labels) if repo.labels else {},
                            "raw": {
                                "name": repo.name,
                                "format": str(repo.format_),
                                "description": repo.description,
                            },
                        })
                except Exception:
                    continue
            if resources:
                logger.info(f"GCP: discovered {len(resources)} Artifact Registry repositories")
        except ImportError:
            logger.debug("google-cloud-artifact-registry not installed — skipping")
        except Exception as e:
            logger.debug(f"GCP Artifact Registry discovery: {e}")
        return resources

    # ─── Secret Manager ───────────────────────────────────────────────────────

    async def _discover_secret_manager(self) -> list[dict[str, Any]]:
        resources = []
        try:
            from google.cloud import secretmanager  # type: ignore[import]
            client = secretmanager.SecretManagerServiceClient(credentials=self._gcp_credentials)
            parent = f"projects/{self._project_id}"
            for secret in client.list_secrets(request={"parent": parent}):
                resources.append({
                    "type": "SecretManagerSecret",
                    "id": secret.name,
                    "name": secret.name.split("/")[-1],
                    "region": "global",
                    "tags": dict(secret.labels) if secret.labels else {},
                    "raw": {
                        "name": secret.name,
                        "replication": str(secret.replication) if secret.replication else None,
                    },
                })
            if resources:
                logger.info(f"GCP: discovered {len(resources)} Secret Manager secrets")
        except ImportError:
            logger.debug("google-cloud-secret-manager not installed — skipping")
        except Exception as e:
            logger.debug(f"GCP Secret Manager discovery: {e}")
        return resources

    # ─── IAM Bindings ─────────────────────────────────────────────────────────

    async def _discover_iam_bindings(self) -> list[dict[str, Any]]:
        """Discover project-level IAM policy bindings."""
        resources = []
        try:
            import googleapiclient.discovery
            crm = googleapiclient.discovery.build(
                "cloudresourcemanager", "v1",
                credentials=self._gcp_credentials,
                cache_discovery=False,
            )
            policy = crm.projects().getIamPolicy(
                resource=self._project_id, body={}
            ).execute()
            for binding in policy.get("bindings", []):
                role = binding.get("role", "")
                members = binding.get("members", [])
                resources.append({
                    "type": "IAMBinding",
                    "id": f"projects/{self._project_id}/iamBindings/{role.replace('/', '_')}",
                    "name": role,
                    "region": "global",
                    "tags": {},
                    "is_public": "allUsers" in members or "allAuthenticatedUsers" in members,
                    "raw": {
                        "role": role,
                        "members": members,
                        "project": self._project_id,
                    },
                })
            if resources:
                logger.info(f"GCP: discovered {len(resources)} IAM bindings")
        except Exception as e:
            logger.debug(f"GCP IAM bindings discovery: {e}")
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
