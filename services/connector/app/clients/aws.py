"""AWS cloud provider client using boto3."""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any

import aiobotocore.session
import boto3
import botocore.exceptions
from botocore.config import Config

from .base import CloudClientBase

logger = logging.getLogger(__name__)


class AWSClient(CloudClientBase):
    """AWS API client for resource discovery."""

    RESOURCE_TYPE_MAPPING = {
        "ec2": "EC2",           # handles EC2, VPC, Subnet, SecurityGroup, EIP
        "s3": "S3Bucket",
        "iam": "IAMUser",       # handles IAMUser, IAMRole, IAMPolicy
        "rds": "RDSInstance",
        "lambda": "LambdaFunction",
        "eks": "EKSCluster",
        "ecs": "ECSCluster",
        "cloudfront": "CloudFrontDistribution",
        "route53": "Route53HostedZone",
        "kms": "KMSKey",
        "elasticache": "ElastiCacheCluster",
        "elbv2": "LoadBalancer",        # ALB / NLB
        "elb": "ClassicLoadBalancer",   # CLB
        "apigateway": "APIGateway",
        "ecr": "ECRRepository",
        "efs": "EFSFileSystem",
        "config": "ConfigRule",
        "cloudtrail": "CloudTrailTrail",
        "sns": "SNSTopic",
        "sqs": "SQSQueue",
        "dynamodb": "DynamoDBTable",
        "secretsmanager": "SecretsManagerSecret",
    }

    def __init__(self, credentials: dict[str, Any], region: str = "us-east-1"):
        self._credentials = credentials
        self._region = region
        self._role_arn = credentials.get("role_arn")
        self._external_id = credentials.get("external_id")
        self._session = None
        self._sts_client = None
        self._account_id = None

    async def connect(self) -> bool:
        """
        Connect to AWS.

        If role_arn is in credentials (set by auto-setup), assume that role
        and use the resulting session credentials for all API calls.
        If no role_arn, use the access key directly (fallback).
        """
        try:
            session = aiobotocore.session.get_session()
            self._session = session

            if self._role_arn:
                # Assume the CloudVisorReadOnly role — this is the normal path
                async with session.create_client(
                    "sts", region_name=self._region,
                    aws_access_key_id=self._credentials.get("access_key"),
                    aws_secret_access_key=self._credentials.get("secret_key"),
                ) as sts:
                    response = await sts.assume_role(
                        RoleArn=self._role_arn,
                        RoleSessionName="cloudvisor-discovery",
                        ExternalId=self._external_id,
                        DurationSeconds=3600,
                    )
                    creds = response["Credentials"]
                    # Replace credentials with the temporary session credentials
                    self._credentials = {
                        "access_key": creds["AccessKeyId"],
                        "secret_key": creds["SecretAccessKey"],
                        "session_token": creds["SessionToken"],
                    }
                    self._account_id = self._role_arn.split(":")[4]
                    logger.info(f"Assumed role {self._role_arn} for account {self._account_id}")
            else:
                # Fallback: use access key directly (limited permissions)
                async with session.create_client(
                    "sts", region_name=self._region,
                    aws_access_key_id=self._credentials.get("access_key"),
                    aws_secret_access_key=self._credentials.get("secret_key"),
                ) as sts:
                    identity = await sts.get_caller_identity()
                    self._account_id = identity["Account"]
                    logger.info(
                        f"Connected with direct credentials for account {self._account_id}. "
                        f"Consider re-connecting to auto-provision a read-only role."
                    )
            return True
        except Exception as e:
            logger.error(f"AWS connect failed: {type(e).__name__}: {str(e)[:300]}")
            return False

    async def disconnect(self) -> None:
        """Close the session."""
        self._session = None
        self._sts_client = None

    def get_account_id(self) -> str:
        return self._account_id or ""

    async def list_resources(self, region: str | None = None) -> list[dict[str, Any]]:
        """List all resources across all supported types and regions."""
        resources = []

        if not self._session:
            await self.connect()

        # Determine regions to scan
        # IAM, S3, CloudFront are global — always scan them
        # For regional services, scan all available regions (or the specified one)
        regional_services = ["ec2", "rds", "lambda", "eks", "ecs", "kms", "elasticache", "config", "cloudtrail", "sns", "sqs", "dynamodb", "secretsmanager", "elbv2", "elb", "apigateway", "ecr", "efs"]
        global_services = ["iam", "s3", "cloudfront", "route53"]

        # Get regions to scan for regional services
        target_regions = await self._get_regions(region)

        resource_tasks = []

        # Global services — run once
        for svc in global_services:
            if svc in self.RESOURCE_TYPE_MAPPING:
                resource_tasks.append(self._discover_resource_type(svc, "us-east-1"))

        # Regional services — run for each region
        for svc in regional_services:
            if svc in self.RESOURCE_TYPE_MAPPING:
                for r in target_regions:
                    resource_tasks.append(self._discover_resource_type(svc, r))

        results = await asyncio.gather(*resource_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                resources.extend(result)
            elif isinstance(result, Exception):
                pass

        return resources

    async def _get_regions(self, requested_region: str | None) -> list[str]:
        """Get the list of regions to scan.

        If a specific real region is given, use only that.
        If 'global' or None, discover all enabled regions.
        Falls back to common regions if discovery fails.
        """
        FALLBACK_REGIONS = [
            "us-east-1", "us-east-2", "us-west-1", "us-west-2",
            "eu-west-1", "eu-west-2", "eu-central-1",
            "ap-southeast-1", "ap-southeast-2", "ap-northeast-1",
        ]

        # If a real region was specified (not 'global'), use only that
        if requested_region and requested_region not in ("global", ""):
            return [requested_region]

        # Try to discover all enabled regions
        try:
            async with self._session.create_client(
                "ec2", region_name="us-east-1", **self._get_client_config()
            ) as ec2:
                resp = await ec2.describe_regions(Filters=[{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}])
                regions = [r["RegionName"] for r in resp.get("Regions", [])]
                if regions:
                    return regions
        except Exception:
            pass

        return FALLBACK_REGIONS

    async def _discover_resource_type(
        self, resource_type: str, region: str
    ) -> list[dict[str, Any]]:
        """Discover resources of a specific type, with detailed error logging."""
        try:
            method_name = f"_discover_{resource_type}"
            if hasattr(self, method_name):
                result = await getattr(self, method_name)(region)
                if result:
                    logger.info(f"Discovered {len(result)} {resource_type} resources in {region}")
                return result
            return []
        except Exception as e:
            logger.warning(f"Discovery failed for {resource_type} in {region}: {type(e).__name__}: {str(e)[:200]}")
            return []

    async def _discover_ec2(self, region: str) -> list[dict[str, Any]]:
        """Discover EC2 instances, VPCs, Subnets, Security Groups."""
        resources = []
        async with self._session.create_client(
            "ec2", region_name=region, **self._get_client_config()
        ) as ec2:
            paginator = ec2.get_paginator("describe_instances")
            async for page in paginator.paginate():
                for reservation in page.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        resources.append(self._normalize_ec2_instance(instance, region))

            paginator = ec2.get_paginator("describe_vpcs")
            async for page in paginator.paginate():
                for vpc in page.get("Vpcs", []):
                    resources.append(self._normalize_vpc(vpc, region))

            paginator = ec2.get_paginator("describe_subnets")
            async for page in paginator.paginate():
                for subnet in page.get("Subnets", []):
                    resources.append(self._normalize_subnet(subnet, region))

            paginator = ec2.get_paginator("describe_security_groups")
            async for page in paginator.paginate():
                for sg in page.get("SecurityGroups", []):
                    resources.append(self._normalize_security_group(sg, region))

            # Elastic IPs — not pageable, use direct call
            try:
                eip_resp = await ec2.describe_addresses()
                for eip in eip_resp.get("Addresses", []):
                    resources.append(self._normalize_eip(eip, region))
            except Exception as _e:
                logger.debug(f"EIP discovery: {_e}")

        return resources

    async def _discover_s3(self, region: str) -> list[dict[str, Any]]:
        """Discover S3 buckets."""
        resources = []
        async with self._session.create_client(
            "s3", region_name=region, **self._get_client_config()
        ) as s3:
            try:
                response = await s3.list_buckets()
                for bucket in response.get("Buckets", []):
                    try:
                        tags_response = await s3.get_bucket_tagging(Bucket=bucket["Name"])
                        tags = {t["Key"]: t["Value"] for t in tags_response.get("Tags", [])}
                    except:
                        tags = {}
                    resources.append(
                        {
                            "type": "S3Bucket",
                            "id": f"arn:aws:s3:::{bucket['Name']}",
                            "name": bucket["Name"],
                            "region": "global",
                            "tags": tags,
                            "raw": bucket,
                        }
                    )
            except Exception as _e:
                logger.debug(f"Sub-discovery error: {_e}")
        return resources

    async def _discover_iam(self, region: str) -> list[dict[str, Any]]:
        """Discover IAM users, roles, and policies."""
        resources = []
        async with self._session.create_client(
            "iam", region_name="us-east-1", **self._get_client_config()
        ) as iam:
            paginator = iam.get_paginator("list_users")
            async for page in paginator.paginate():
                for user in page.get("Users", []):
                    resources.append(
                        {
                            "type": "IAMUser",
                            "id": user["Arn"],
                            "name": user["UserName"],
                            "region": "global",
                            "tags": {t["Key"]: t["Value"] for t in user.get("Tags", [])},
                            "raw": user,
                        }
                    )

            paginator = iam.get_paginator("list_roles")
            async for page in paginator.paginate():
                for role in page.get("Roles", []):
                    resources.append(
                        {
                            "type": "IAMRole",
                            "id": role["Arn"],
                            "name": role["RoleName"],
                            "region": "global",
                            "tags": {t["Key"]: t["Value"] for t in role.get("Tags", [])},
                            "raw": role,
                        }
                    )

            # Scope="Local" returns only customer-managed policies (not AWS-managed)
            paginator = iam.get_paginator("list_policies")
            async for page in paginator.paginate(Scope="Local"):
                for policy in page.get("Policies", []):
                    resources.append(
                        {
                            "type": "IAMPolicy",
                            "id": policy["Arn"],
                            "name": policy["PolicyName"],
                            "region": "global",
                            "tags": {},
                            "raw": policy,
                        }
                    )
        return resources

    async def _discover_rds(self, region: str) -> list[dict[str, Any]]:
        """Discover RDS instances."""
        resources = []
        async with self._session.create_client(
            "rds", region_name=region, **self._get_client_config()
        ) as rds:
            paginator = rds.get_paginator("describe_db_instances")
            async for page in paginator.paginate():
                for db in page.get("DBInstances", []):
                    resources.append(
                        {
                            "type": "RDSInstance",
                            "id": db["DBInstanceArn"],
                            "name": db["DBInstanceIdentifier"],
                            "region": region,
                            "tags": {t["Key"]: t["Value"] for t in db.get("TagList", [])},
                            "raw": db,
                        }
                    )
        return resources

    async def _discover_lambda(self, region: str) -> list[dict[str, Any]]:
        """Discover Lambda functions."""
        resources = []
        async with self._session.create_client(
            "lambda", region_name=region, **self._get_client_config()
        ) as lambda_client:
            paginator = lambda_client.get_paginator("list_functions")
            async for page in paginator.paginate():
                for function in page.get("Functions", []):
                    resources.append(
                        {
                            "type": "LambdaFunction",
                            "id": function["FunctionArn"],
                            "name": function["FunctionName"],
                            "region": region,
                            "tags": function.get("Tags", {}),
                            "raw": function,
                        }
                    )
        return resources

    async def _discover_eks(self, region: str) -> list[dict[str, Any]]:
        """Discover EKS clusters."""
        resources = []
        async with self._session.create_client(
            "eks", region_name=region, **self._get_client_config()
        ) as eks:
            try:
                response = await eks.list_clusters()
                for cluster_name in response.get("clusters", []):
                    cluster = await eks.describe_cluster(name=cluster_name)
                    cluster_data = cluster.get("cluster", {})
                    resources.append(
                        {
                            "type": "EKSCluster",
                            "id": cluster_data["arn"],
                            "name": cluster_name,
                            "region": region,
                            "tags": cluster_data.get("tags", {}),
                            "raw": cluster_data,
                        }
                    )
            except Exception as _e:
                logger.debug(f"Sub-discovery error: {_e}")
        return resources

    async def _discover_kms(self, region: str) -> list[dict[str, Any]]:
        """Discover KMS keys."""
        resources = []
        async with self._session.create_client(
            "kms", region_name=region, **self._get_client_config()
        ) as kms:
            paginator = kms.get_paginator("list_keys")
            async for page in paginator.paginate():
                for key in page.get("Keys", []):
                    try:
                        key_info = await kms.describe_key(KeyId=key["KeyId"])
                        resources.append(
                            {
                                "type": "KMSKey",
                                "id": key["KeyArn"],
                                "name": key["KeyId"],
                                "region": region,
                                "tags": {
                                    t["TagKey"]: t["TagValue"]
                                    for t in key_info.get("KeyMetadata", {}).get("Tags", [])
                                },
                                "raw": key_info.get("KeyMetadata", {}),
                            }
                        )
                    except Exception as _e:
                        logger.debug(f"KMS key describe error: {_e}")
        return resources

    async def _discover_sns(self, region: str) -> list[dict[str, Any]]:
        """Discover SNS topics."""
        resources = []
        async with self._session.create_client(
            "sns", region_name=region, **self._get_client_config()
        ) as sns:
            try:
                paginator = sns.get_paginator("list_topics")
                async for page in paginator.paginate():
                    for topic in page.get("Topics", []):
                        topic_arn = topic["TopicArn"]
                        name = topic_arn.split(":")[-1]
                        try:
                            attrs_resp = await sns.get_topic_attributes(TopicArn=topic_arn)
                            attrs = attrs_resp.get("Attributes", {})
                        except Exception:
                            attrs = {}
                        resources.append(
                            {
                                "type": "SNSTopic",
                                "id": topic_arn,
                                "name": name,
                                "region": region,
                                "tags": {},
                                "raw": {"TopicArn": topic_arn, **attrs},
                            }
                        )
            except Exception as _e:
                logger.debug(f"SNS discovery error in {region}: {_e}")
        return resources

    async def _discover_sqs(self, region: str) -> list[dict[str, Any]]:
        """Discover SQS queues."""
        resources = []
        async with self._session.create_client(
            "sqs", region_name=region, **self._get_client_config()
        ) as sqs:
            try:
                response = await sqs.list_queues()
                for queue_url in response.get("QueueUrls", []):
                    name = queue_url.split("/")[-1]
                    try:
                        attrs_resp = await sqs.get_queue_attributes(
                            QueueUrl=queue_url,
                            AttributeNames=["All"],
                        )
                        attrs = attrs_resp.get("Attributes", {})
                        queue_arn = attrs.get("QueueArn", queue_url)
                    except Exception:
                        attrs = {}
                        queue_arn = queue_url
                    resources.append(
                        {
                            "type": "SQSQueue",
                            "id": queue_arn,
                            "name": name,
                            "region": region,
                            "tags": {},
                            "raw": {"QueueUrl": queue_url, **attrs},
                        }
                    )
            except Exception as _e:
                logger.debug(f"SQS discovery error in {region}: {_e}")
        return resources

    async def _discover_dynamodb(self, region: str) -> list[dict[str, Any]]:
        """Discover DynamoDB tables."""
        resources = []
        async with self._session.create_client(
            "dynamodb", region_name=region, **self._get_client_config()
        ) as dynamodb:
            try:
                paginator = dynamodb.get_paginator("list_tables")
                async for page in paginator.paginate():
                    for table_name in page.get("TableNames", []):
                        try:
                            desc_resp = await dynamodb.describe_table(TableName=table_name)
                            table = desc_resp.get("Table", {})
                            table_arn = table.get("TableArn", f"arn:aws:dynamodb:{region}:{self._account_id}:table/{table_name}")
                        except Exception:
                            table = {}
                            table_arn = f"arn:aws:dynamodb:{region}:{self._account_id}:table/{table_name}"
                        resources.append(
                            {
                                "type": "DynamoDBTable",
                                "id": table_arn,
                                "name": table_name,
                                "region": region,
                                "tags": {},
                                "raw": table,
                            }
                        )
            except Exception as _e:
                logger.debug(f"DynamoDB discovery error in {region}: {_e}")
        return resources

    async def _discover_secretsmanager(self, region: str) -> list[dict[str, Any]]:
        """Discover Secrets Manager secrets."""
        resources = []
        async with self._session.create_client(
            "secretsmanager", region_name=region, **self._get_client_config()
        ) as sm:
            try:
                paginator = sm.get_paginator("list_secrets")
                async for page in paginator.paginate():
                    for secret in page.get("SecretList", []):
                        resources.append(
                            {
                                "type": "SecretsManagerSecret",
                                "id": secret["ARN"],
                                "name": secret["Name"],
                                "region": region,
                                "tags": {t["Key"]: t["Value"] for t in secret.get("Tags", [])},
                                "raw": secret,
                            }
                        )
            except Exception as _e:
                logger.debug(f"Secrets Manager discovery error in {region}: {_e}")
        return resources

    def _get_client_config(self) -> dict[str, Any]:
        """Get boto3 client config with assumed role credentials."""
        if "session_token" in self._credentials:
            return {
                "aws_access_key_id": self._credentials["access_key"],
                "aws_secret_access_key": self._credentials["secret_key"],
                "aws_session_token": self._credentials["session_token"],
            }
        return {
            "aws_access_key_id": self._credentials.get("access_key"),
            "aws_secret_access_key": self._credentials.get("secret_key"),
        }

    def _normalize_ec2_instance(self, instance: dict, region: str) -> dict:
        return {
            "type": "EC2",
            "id": f"arn:aws:ec2:{region}:{self._account_id}:instance/{instance['InstanceId']}",
            "name": next(
                (t["Value"] for t in instance.get("Tags", []) if t["Key"] == "Name"),
                instance["InstanceId"],
            ),
            "region": region,
            "tags": {t["Key"]: t["Value"] for t in instance.get("Tags", [])},
            "raw": instance,
        }

    def _normalize_vpc(self, vpc: dict, region: str) -> dict:
        return {
            "type": "VPC",
            "id": vpc["VpcId"],
            "name": next(
                (t["Value"] for t in vpc.get("Tags", []) if t["Key"] == "Name"), vpc["VpcId"]
            ),
            "region": region,
            "tags": {t["Key"]: t["Value"] for t in vpc.get("Tags", [])},
            "raw": vpc,
        }

    def _normalize_subnet(self, subnet: dict, region: str) -> dict:
        return {
            "type": "Subnet",
            "id": subnet["SubnetId"],
            "name": next(
                (t["Value"] for t in subnet.get("Tags", []) if t["Key"] == "Name"),
                subnet["SubnetId"],
            ),
            "region": region,
            "tags": {t["Key"]: t["Value"] for t in subnet.get("Tags", [])},
            "raw": subnet,
        }

    def _normalize_security_group(self, sg: dict, region: str) -> dict:
        return {
            "type": "SecurityGroup",
            "id": sg["GroupId"],
            "name": sg.get("GroupName", sg["GroupId"]),
            "region": region,
            "tags": {t["Key"]: t["Value"] for t in sg.get("Tags", [])},
            "raw": sg,
        }

    def _normalize_eip(self, eip: dict, region: str) -> dict:
        return {
            "type": "EIP",
            "id": eip["AllocationId"],
            "name": eip.get("PublicIp", eip["AllocationId"]),
            "region": region,
            "tags": {t["Key"]: t["Value"] for t in eip.get("Tags", [])},
            "raw": eip,
        }

    def compute_resource_hash(self, resource: dict[str, Any]) -> str:
        """Compute a hash for deduplication."""
        content = json.dumps(
            {
                "cloud_resource_id": resource.get("id"),
                "resource_type": resource.get("type"),
                "name": resource.get("name"),
                "region": resource.get("region"),
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    async def _discover_cloudfront(self, region: str) -> list[dict[str, Any]]:
        """Discover CloudFront distributions."""
        resources = []
        async with self._session.create_client(
            "cloudfront", region_name="us-east-1", **self._get_client_config()
        ) as cloudfront:
            try:
                paginator = cloudfront.get_paginator("list_distributions")
                async for page in paginator.paginate():
                    for dist in page.get("DistributionList", {}).get("Items", []):
                        resources.append(
                            {
                                "type": "CloudFrontDistribution",
                                "id": dist["ARN"],
                                "name": dist.get("Comment", dist["Id"]),
                                "region": "global",
                                "tags": dist.get("Tags", {}).get("Items", []),
                                "raw": dist,
                            }
                        )
            except Exception as _e:
                logger.debug(f"Sub-discovery error: {_e}")
        return resources

    async def _discover_ecs(self, region: str) -> list[dict[str, Any]]:
        """Discover ECS clusters and task definitions."""
        resources = []
        async with self._session.create_client(
            "ecs", region_name=region, **self._get_client_config()
        ) as ecs:
            try:
                paginator = ecs.get_paginator("list_clusters")
                async for page in paginator.paginate():
                    for cluster_arn in page.get("clusterArns", []):
                        try:
                            cluster = await ecs.describe_clusters(clusters=[cluster_arn])
                            cluster_data = cluster.get("clusters", [{}])[0]
                            resources.append(
                                {
                                    "type": "ECSCluster",
                                    "id": cluster_data["clusterArn"],
                                    "name": cluster_data["clusterName"],
                                    "region": region,
                                    "tags": {t["key"]: t["value"] for t in cluster_data.get("tags", [])},
                                    "raw": cluster_data,
                                }
                            )
                        except:
                            continue
            except Exception as _e:
                logger.debug(f"Sub-discovery error: {_e}")
        return resources

    async def _discover_elasticache(self, region: str) -> list[dict[str, Any]]:
        """Discover ElastiCache clusters."""
        resources = []
        async with self._session.create_client(
            "elasticache", region_name=region, **self._get_client_config()
        ) as elasticache:
            try:
                paginator = elasticache.get_paginator("describe_cache_clusters")
                async for page in paginator.paginate():
                    for cluster in page.get("CacheClusters", []):
                        resources.append(
                            {
                                "type": "ElastiCacheCluster",
                                "id": cluster["CacheClusterId"],
                                "name": cluster.get("CacheClusterId", ""),
                                "region": region,
                                "tags": {},
                                "raw": cluster,
                            }
                        )
            except Exception as _e:
                logger.debug(f"Sub-discovery error: {_e}")
        return resources

    async def _discover_config(self, region: str) -> list[dict[str, Any]]:
        """Discover Config rules."""
        resources = []
        async with self._session.create_client(
            "config", region_name=region, **self._get_client_config()
        ) as config_client:
            try:
                paginator = config_client.get_paginator("describe_config_rules")
                async for page in paginator.paginate():
                    for rule in page.get("ConfigRules", []):
                        resources.append(
                            {
                                "type": "ConfigRule",
                                "id": rule["ConfigRuleArn"],
                                "name": rule["ConfigRuleName"],
                                "region": region,
                                "tags": {},
                                "raw": rule,
                            }
                        )
            except Exception as _e:
                logger.debug(f"Sub-discovery error: {_e}")
        return resources


    async def _discover_route53(self, region: str) -> list[dict[str, Any]]:
        """Discover Route53 hosted zones (global service)."""
        resources = []
        async with self._session.create_client(
            "route53", region_name="us-east-1", **self._get_client_config()
        ) as r53:
            try:
                paginator = r53.get_paginator("list_hosted_zones")
                async for page in paginator.paginate():
                    for zone in page.get("HostedZones", []):
                        resources.append({
                            "type": "Route53HostedZone",
                            "id": zone["Id"],
                            "name": zone["Name"].rstrip("."),
                            "region": "global",
                            "tags": {},
                            "raw": zone,
                        })
            except Exception as _e:
                logger.debug(f"Route53 discovery error: {_e}")
        return resources

    async def _discover_elbv2(self, region: str) -> list[dict[str, Any]]:
        """Discover ALB and NLB load balancers."""
        resources = []
        async with self._session.create_client(
            "elbv2", region_name=region, **self._get_client_config()
        ) as elbv2:
            try:
                paginator = elbv2.get_paginator("describe_load_balancers")
                async for page in paginator.paginate():
                    for lb in page.get("LoadBalancers", []):
                        is_public = lb.get("Scheme") == "internet-facing"
                        resources.append({
                            "type": "LoadBalancer",
                            "id": lb["LoadBalancerArn"],
                            "name": lb["LoadBalancerName"],
                            "region": region,
                            "tags": {},
                            "is_public": is_public,
                            "raw": lb,
                        })
            except Exception as _e:
                logger.debug(f"ELBv2 discovery error in {region}: {_e}")
        return resources

    async def _discover_elb(self, region: str) -> list[dict[str, Any]]:
        """Discover Classic Load Balancers."""
        resources = []
        async with self._session.create_client(
            "elb", region_name=region, **self._get_client_config()
        ) as elb:
            try:
                paginator = elb.get_paginator("describe_load_balancers")
                async for page in paginator.paginate():
                    for lb in page.get("LoadBalancerDescriptions", []):
                        is_public = lb.get("Scheme") == "internet-facing"
                        resources.append({
                            "type": "ClassicLoadBalancer",
                            "id": f"arn:aws:elasticloadbalancing:{region}:{self._account_id}:loadbalancer/{lb['LoadBalancerName']}",
                            "name": lb["LoadBalancerName"],
                            "region": region,
                            "tags": {},
                            "is_public": is_public,
                            "raw": lb,
                        })
            except Exception as _e:
                logger.debug(f"ELB (classic) discovery error in {region}: {_e}")
        return resources

    async def _discover_apigateway(self, region: str) -> list[dict[str, Any]]:
        """Discover API Gateway REST APIs and HTTP APIs."""
        resources = []
        # REST APIs (v1)
        async with self._session.create_client(
            "apigateway", region_name=region, **self._get_client_config()
        ) as apigw:
            try:
                paginator = apigw.get_paginator("get_rest_apis")
                async for page in paginator.paginate():
                    for api in page.get("items", []):
                        resources.append({
                            "type": "APIGateway",
                            "id": f"arn:aws:apigateway:{region}::/restapis/{api['id']}",
                            "name": api["name"],
                            "region": region,
                            "tags": api.get("tags", {}),
                            "is_public": True,
                            "raw": api,
                        })
            except Exception as _e:
                logger.debug(f"API Gateway v1 discovery error in {region}: {_e}")

        # HTTP APIs (v2)
        async with self._session.create_client(
            "apigatewayv2", region_name=region, **self._get_client_config()
        ) as apigwv2:
            try:
                response = await apigwv2.get_apis()
                for api in response.get("Items", []):
                    resources.append({
                        "type": "APIGatewayV2",
                        "id": f"arn:aws:apigateway:{region}::/apis/{api['ApiId']}",
                        "name": api["Name"],
                        "region": region,
                        "tags": api.get("Tags", {}),
                        "is_public": True,
                        "raw": api,
                    })
            except Exception as _e:
                logger.debug(f"API Gateway v2 discovery error in {region}: {_e}")

        return resources

    async def _discover_ecr(self, region: str) -> list[dict[str, Any]]:
        """Discover ECR repositories."""
        resources = []
        async with self._session.create_client(
            "ecr", region_name=region, **self._get_client_config()
        ) as ecr:
            try:
                paginator = ecr.get_paginator("describe_repositories")
                async for page in paginator.paginate():
                    for repo in page.get("repositories", []):
                        # Check if repo is public (image scan on push, public access)
                        is_public = False
                        try:
                            policy_resp = await ecr.get_repository_policy(
                                repositoryName=repo["repositoryName"]
                            )
                            import json as _json
                            policy = _json.loads(policy_resp.get("policyText", "{}"))
                            for stmt in policy.get("Statement", []):
                                if stmt.get("Principal") == "*":
                                    is_public = True
                                    break
                        except Exception:
                            pass
                        resources.append({
                            "type": "ECRRepository",
                            "id": repo["repositoryArn"],
                            "name": repo["repositoryName"],
                            "region": region,
                            "tags": {},
                            "is_public": is_public,
                            "raw": repo,
                        })
            except Exception as _e:
                logger.debug(f"ECR discovery error in {region}: {_e}")
        return resources

    async def _discover_efs(self, region: str) -> list[dict[str, Any]]:
        """Discover EFS file systems."""
        resources = []
        async with self._session.create_client(
            "efs", region_name=region, **self._get_client_config()
        ) as efs:
            try:
                paginator = efs.get_paginator("describe_file_systems")
                async for page in paginator.paginate():
                    for fs in page.get("FileSystems", []):
                        resources.append({
                            "type": "EFSFileSystem",
                            "id": fs["FileSystemArn"],
                            "name": next(
                                (t["Value"] for t in fs.get("Tags", []) if t["Key"] == "Name"),
                                fs["FileSystemId"],
                            ),
                            "region": region,
                            "tags": {t["Key"]: t["Value"] for t in fs.get("Tags", [])},
                            "raw": fs,
                        })
            except Exception as _e:
                logger.debug(f"EFS discovery error in {region}: {_e}")
        return resources

    async def _discover_cloudtrail(self, region: str) -> list[dict[str, Any]]:
        """Discover CloudTrail trails."""
        resources = []
        async with self._session.create_client(
            "cloudtrail", region_name=region, **self._get_client_config()
        ) as ct:
            try:
                response = await ct.describe_trails(includeShadowTrails=False)
                for trail in response.get("trailList", []):
                    resources.append({
                        "type": "CloudTrailTrail",
                        "id": trail["TrailARN"],
                        "name": trail["Name"],
                        "region": region,
                        "tags": {},
                        "raw": trail,
                    })
            except Exception as _e:
                logger.debug(f"CloudTrail discovery error in {region}: {_e}")
        return resources

    async def _discover_config(self, region: str) -> list[dict[str, Any]]:
        """Discover AWS Config rules."""
        resources = []
        async with self._session.create_client(
            "config", region_name=region, **self._get_client_config()
        ) as config_client:
            try:
                paginator = config_client.get_paginator("describe_config_rules")
                async for page in paginator.paginate():
                    for rule in page.get("ConfigRules", []):
                        resources.append({
                            "type": "ConfigRule",
                            "id": rule["ConfigRuleArn"],
                            "name": rule["ConfigRuleName"],
                            "region": region,
                            "tags": {},
                            "raw": rule,
                        })
            except Exception as _e:
                logger.debug(f"Config rules discovery error in {region}: {_e}")
        return resources
