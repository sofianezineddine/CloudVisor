"""Common Data Model types for CloudVisor.

This module defines the canonical data structures used across all CloudVisor
services. Every cloud resource is normalized to these types regardless of
the source provider (AWS, Azure, GCP, OCI).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CloudProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    OCI = "oci"


class Environment(str, Enum):
    PROD = "prod"
    STAGING = "staging"
    DEV = "dev"
    UNKNOWN = "unknown"


class ConnectorStatus(str, Enum):
    ACTIVE = "active"
    ERROR = "error"
    PAUSED = "paused"
    PENDING = "pending"
    AUTH_FAILED = "auth_failed"
    PARTIAL_SYNC = "partial_sync"


class SyncStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CloudResource:
    id: str
    cloud_resource_id: str
    provider: CloudProvider
    account_id: str
    region: str
    resource_type: str
    name: str
    tags: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    first_seen_at: datetime = field(default_factory=datetime.utcnow)
    last_seen_at: datetime = field(default_factory=datetime.utcnow)
    organization_id: str = ""
    is_public: bool = False
    environment: Environment = Environment.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "cloud_resource_id": self.cloud_resource_id,
            "provider": self.provider.value,
            "account_id": self.account_id,
            "region": self.region,
            "resource_type": self.resource_type,
            "name": self.name,
            "tags": self.tags,
            "raw": self.raw,
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
            "organization_id": self.organization_id,
            "is_public": self.is_public,
            "environment": self.environment.value,
        }


@dataclass
class CloudAccount:
    id: str
    organization_id: str
    provider: CloudProvider
    name: str
    account_id: str
    region: str = "global"
    status: ConnectorStatus = ConnectorStatus.PENDING
    sync_status: SyncStatus = SyncStatus.IDLE
    last_sync_at: datetime | None = None
    last_successful_sync_at: datetime | None = None
    consecutive_errors: int = 0
    error_message: str | None = None
    resource_count: int = 0
    polling_interval_minutes: int = 15
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "provider": self.provider.value,
            "name": self.name,
            "account_id": self.account_id,
            "region": self.region,
            "status": self.status.value,
            "sync_status": self.sync_status.value,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_successful_sync_at": self.last_successful_sync_at.isoformat()
            if self.last_successful_sync_at
            else None,
            "consecutive_errors": self.consecutive_errors,
            "error_message": self.error_message,
            "resource_count": self.resource_count,
            "polling_interval_minutes": self.polling_interval_minutes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class SyncResult:
    account_id: str
    organization_id: str
    provider: CloudProvider
    discovered: int = 0
    updated: int = 0
    deleted: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    correlation_id: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "organization_id": self.organization_id,
            "provider": self.provider.value,
            "discovered": self.discovered,
            "updated": self.updated,
            "deleted": self.deleted,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "correlation_id": self.correlation_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


RESOURCE_TYPE_MAPPING: dict[str, dict[str, str]] = {
    "aws": {
        "EC2": "aws::ec2::instance",
        "VPC": "aws::vpc::vpc",
        "Subnet": "aws::vpc::subnet",
        "SecurityGroup": "aws::ec2::securitygroup",
        "S3Bucket": "aws::s3::bucket",
        "IAMUser": "aws::iam::user",
        "IAMRole": "aws::iam::role",
        "IAMPolicy": "aws::iam::policy",
        "RDSInstance": "aws::rds::instance",
        "LambdaFunction": "aws::lambda::function",
        "EKSCluster": "aws::eks::cluster",
        "ECSTaskDefinition": "aws::ecs::task",
        "CloudFrontDistribution": "aws::cloudfront::distribution",
        "Route53HostedZone": "aws::route53::hostedzone",
        "KMSKey": "aws::kms::key",
        "CloudTrailTrail": "aws::cloudtrail::trail",
        "SNSTopic": "aws::sns::topic",
        "SQSQueue": "aws::sqs::queue",
        "DynamoDBTable": "aws::dynamodb::table",
        "ElastiCacheCluster": "aws::elasticache::cluster",
        "LoadBalancer": "aws::elb::loadbalancer",
        "ApiGatewayRestApi": "aws::apigateway::restapi",
        "SecretsManagerSecret": "aws::secretsmanager::secret",
        "ECRRepository": "aws::ecr::repository",
        "EFSFileSystem": "aws::efs::filesystem",
        "EIP": "aws::ec2::eip",
    },
    "azure": {
        "VirtualMachine": "azure::compute::virtualmachine",
        "NetworkSecurityGroup": "azure::network::nsg",
        "VirtualNetwork": "azure::network::virtualnetwork",
        "Subnet": "azure::network::subnet",
        "StorageAccount": "azure::storage::account",
        "BlobContainer": "azure::storage::container",
        "SqlServer": "azure::sql::server",
        "FunctionApp": "azure::functions::function",
        "KubernetesService": "azure::containerservice::aks",
        "WebApp": "azure::appservice::webapp",
        "KeyVault": "azure::keyvault::vault",
        "User": "azure::ad::user",
        "ServicePrincipal": "azure::ad::serviceprincipal",
        "RoleAssignment": "azure::authorization::roleassignment",
        "Firewall": "azure::network::firewall",
        "LoadBalancer": "azure::network::loadbalancer",
        "ApiManagement": "azure::apim::service",
        "CosmosDBAccount": "azure::cosmosdb::account",
        "ContainerRegistry": "azure::containerregistry::registry",
        "EventHubNamespace": "azure::eventhub::namespace",
        "ServiceBusNamespace": "azure::servicebus::namespace",
    },
    "gcp": {
        "Instance": "gcp::compute::instance",
        "FirewallPolicy": "gcp::compute::firewall",
        "Network": "gcp::compute::network",
        "Subnetwork": "gcp::compute::subnetwork",
        "Bucket": "gcp::storage::bucket",
        "Instance": "gcp::sql::instance",
        "CloudFunction": "gcp::functions::function",
        "Cluster": "gcp::container::cluster",
        "ServiceAccount": "gcp::iam::serviceaccount",
        "KMSKey": "gcp::kms::key",
        "Dataset": "gcp::bigquery::dataset",
        "Topic": "gcp::pubsub::topic",
        "ManagedZone": "gcp::dns::managedzone",
        "Repository": "gcp::artifactregistry::repository",
        "Secret": "gcp::secretmanager::secret",
    },
    "oci": {
        "Instance": "oci::compute::instance",
        "SecurityList": "oci::network::securitylist",
        "Vcn": "oci::network::vcn",
        "Subnet": "oci::network::subnet",
        "Bucket": "oci::objectstorage::bucket",
        "AutonomousDatabase": "oci::database::autonomousdatabase",
        "Function": "oci::functions::function",
        "Cluster": "oci::containerengine::cluster",
        "User": "oci::identity::user",
        "Group": "oci::identity::group",
        "Policy": "oci::identity::policy",
        "Vault": "oci::vault::secret",
        "LoadBalancer": "oci::loadbalancer::loadbalancer",
    },
}


def get_resource_type(provider: CloudProvider, provider_type: str) -> str:
    mapping = RESOURCE_TYPE_MAPPING.get(provider.value, {})
    return mapping.get(provider_type, f"{provider.value}::{provider_type.lower()}")
