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
from app.services.retry import RetryConfig, retry_async, RateLimitException, TemporaryException
from app.services.circuit_breaker import CircuitBreakerRegistry, CircuitBreakerOpenException

logger = logging.getLogger(__name__)

# Global circuit breaker registry
_circuit_breaker_registry = CircuitBreakerRegistry()

# Retry configuration for AWS API calls
_retry_config = RetryConfig(
    max_retries=5,
    initial_delay_seconds=1.0,
    max_delay_seconds=60.0,
    exponential_base=2.0,
    jitter=True,
)


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

    async def _call_with_retry_and_circuit_breaker(
        self,
        service_name: str,
        func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Call an AWS API function with retry logic and circuit breaker protection.

        Args:
            service_name: Name of the AWS service (for circuit breaker identification)
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of the function call

        Raises:
            CircuitBreakerOpenException: If circuit breaker is open
            RateLimitException: If rate limited (429)
            TemporaryException: If temporary error (5xx, timeout)
            Exception: Any other exception from the function
        """
        # Get or create circuit breaker for this service
        breaker = await _circuit_breaker_registry.get_or_create(
            name=f"aws-{service_name}",
            failure_threshold=0.5,  # 50% error rate
            failure_window_seconds=300,  # 5 minutes
            recovery_timeout_seconds=60,  # 1 minute before trying again
            min_requests_for_threshold=10,  # Need at least 10 requests
        )

        # Execute through circuit breaker with retry logic
        async def call_with_retry():
            try:
                return await func(*args, **kwargs)
            except botocore.exceptions.ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                status_code = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)

                # Handle rate limiting (429)
                if status_code == 429 or error_code == "ThrottlingException":
                    retry_after = e.response.get("ResponseMetadata", {}).get("HTTPHeaders", {}).get("retry-after")
                    retry_after_seconds = float(retry_after) if retry_after else None
                    raise RateLimitException(retry_after_seconds)

                # Handle temporary errors (5xx, timeouts)
                if status_code >= 500 or error_code in ("RequestTimeout", "ConnectionError"):
                    raise TemporaryException(f"AWS API error: {error_code} ({status_code})")

                # Handle auth errors (don't retry)
                if status_code in (401, 403) or error_code in ("UnauthorizedOperation", "AccessDenied"):
                    logger.error(f"AWS auth error: {error_code} - credentials may be invalid")
                    raise

                # Other client errors - don't retry
                raise

            except (TimeoutError, ConnectionError, asyncio.TimeoutError) as e:
                raise TemporaryException(f"Connection error: {type(e).__name__}")

        # Apply retry decorator
        @retry_async(config=_retry_config, retryable_exceptions=(RateLimitException, TemporaryException))
        async def call_with_retry_decorated():
            return await call_with_retry()

        # Execute through circuit breaker
        return await breaker.call(call_with_retry_decorated)

    async def list_resources(self, region: str | None = None) -> list[dict[str, Any]]:
        """List all resources across all supported types and regions.

        Fans out region × service discovery concurrently, but caps overall
        concurrency with a semaphore so we don't open hundreds of client
        sessions against AWS simultaneously (which trips throttling).
        """
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

        # Cap concurrent discoveries so we respect cloud API session limits.
        # 20 is conservative; tune via env if needed.
        sem = asyncio.Semaphore(20)

        async def _bounded(svc: str, r: str) -> list[dict[str, Any]]:
            async with sem:
                return await self._discover_resource_type(svc, r)

        resource_tasks: list[Any] = []

        # Global services — run once
        for svc in global_services:
            if svc in self.RESOURCE_TYPE_MAPPING:
                resource_tasks.append(_bounded(svc, "us-east-1"))

        # Regional services — run for each region
        for svc in regional_services:
            if svc in self.RESOURCE_TYPE_MAPPING:
                for r in target_regions:
                    resource_tasks.append(_bounded(svc, r))

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

        # Try to discover all enabled regions — wrapped in retry/CB so a
        # transient throttle doesn't kill the whole sync.
        try:
            async with self._session.create_client(
                "ec2", region_name="us-east-1", **self._get_client_config()
            ) as ec2:
                async def _describe():
                    return await ec2.describe_regions(
                        Filters=[{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}]
                    )

                resp = await self._call_with_retry_and_circuit_breaker("ec2", _describe)
                regions = [r["RegionName"] for r in resp.get("Regions", [])]
                if regions:
                    return regions
        except Exception as e:
            logger.warning(f"describe_regions failed, using fallback region list: {e}")

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
        try:
            async with self._session.create_client(
                "ec2", region_name=region, **self._get_client_config()
            ) as ec2:
                # Discover EC2 instances
                try:
                    paginator = ec2.get_paginator("describe_instances")
                    async for page in paginator.paginate():
                        for reservation in page.get("Reservations", []):
                            for instance in reservation.get("Instances", []):
                                resources.append(self._normalize_ec2_instance(instance, region))
                except Exception as e:
                    logger.warning(f"EC2 instances discovery failed in {region}: {e}")

                # Discover VPCs
                try:
                    paginator = ec2.get_paginator("describe_vpcs")
                    async for page in paginator.paginate():
                        for vpc in page.get("Vpcs", []):
                            resources.append(self._normalize_vpc(vpc, region))
                except Exception as e:
                    logger.warning(f"EC2 VPCs discovery failed in {region}: {e}")

                # Discover Subnets
                try:
                    paginator = ec2.get_paginator("describe_subnets")
                    async for page in paginator.paginate():
                        for subnet in page.get("Subnets", []):
                            resources.append(self._normalize_subnet(subnet, region))
                except Exception as e:
                    logger.warning(f"EC2 subnets discovery failed in {region}: {e}")

                # Discover Security Groups
                try:
                    paginator = ec2.get_paginator("describe_security_groups")
                    async for page in paginator.paginate():
                        for sg in page.get("SecurityGroups", []):
                            resources.append(self._normalize_security_group(sg, region))
                except Exception as e:
                    logger.warning(f"EC2 security groups discovery failed in {region}: {e}")

                # Discover Elastic IPs
                try:
                    eip_resp = await self._call_with_retry_and_circuit_breaker(
                        "ec2",
                        ec2.describe_addresses
                    )
                    for eip in eip_resp.get("Addresses", []):
                        resources.append(self._normalize_eip(eip, region))
                except Exception as e:
                    logger.debug(f"EC2 EIP discovery failed in {region}: {e}")

        except CircuitBreakerOpenException as e:
            logger.warning(f"EC2 circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"EC2 discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")

        return resources

    async def _discover_s3(self, region: str) -> list[dict[str, Any]]:
        """Discover S3 buckets."""
        resources = []
        try:
            async with self._session.create_client(
                "s3", region_name=region, **self._get_client_config()
            ) as s3:
                response = await self._call_with_retry_and_circuit_breaker(
                    "s3",
                    s3.list_buckets
                )
                for bucket in response.get("Buckets", []):
                    try:
                        tags_response = await self._call_with_retry_and_circuit_breaker(
                            "s3",
                            s3.get_bucket_tagging,
                            Bucket=bucket["Name"]
                        )
                        tags = {t["Key"]: t["Value"] for t in tags_response.get("Tags", [])}
                    except Exception:
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"S3 circuit breaker open: {e}")
        except Exception as e:
            logger.error(f"S3 discovery failed: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_iam(self, region: str) -> list[dict[str, Any]]:
        """Discover IAM users, roles, and policies."""
        resources = []
        try:
            async with self._session.create_client(
                "iam", region_name="us-east-1", **self._get_client_config()
            ) as iam:
                # List users
                try:
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
                except Exception as e:
                    logger.warning(f"IAM users discovery failed: {e}")

                # List roles
                try:
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
                except Exception as e:
                    logger.warning(f"IAM roles discovery failed: {e}")

                # List policies (customer-managed only)
                try:
                    paginator = iam.get_paginator("list_policies")
                    async for page in paginator.paginate():
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
                except Exception as e:
                    logger.warning(f"IAM policies discovery failed: {e}")

        except CircuitBreakerOpenException as e:
            logger.warning(f"IAM circuit breaker open: {e}")
        except Exception as e:
            logger.error(f"IAM discovery failed: {type(e).__name__}: {str(e)[:200]}")

        return resources

    async def _discover_rds(self, region: str) -> list[dict[str, Any]]:
        """Discover RDS instances."""
        resources = []
        try:
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"RDS circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"RDS discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_lambda(self, region: str) -> list[dict[str, Any]]:
        """Discover Lambda functions."""
        resources = []
        try:
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"Lambda circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"Lambda discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_eks(self, region: str) -> list[dict[str, Any]]:
        """Discover EKS clusters."""
        resources = []
        try:
            async with self._session.create_client(
                "eks", region_name=region, **self._get_client_config()
            ) as eks:
                response = await self._call_with_retry_and_circuit_breaker(
                    "eks",
                    eks.list_clusters
                )
                for cluster_name in response.get("clusters", []):
                    try:
                        cluster = await self._call_with_retry_and_circuit_breaker(
                            "eks",
                            eks.describe_cluster,
                            name=cluster_name
                        )
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
                    except Exception as e:
                        logger.debug(f"EKS cluster describe error: {e}")
        except CircuitBreakerOpenException as e:
            logger.warning(f"EKS circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"EKS discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_kms(self, region: str) -> list[dict[str, Any]]:
        """Discover KMS keys."""
        resources = []
        try:
            async with self._session.create_client(
                "kms", region_name=region, **self._get_client_config()
            ) as kms:
                paginator = kms.get_paginator("list_keys")
                async for page in paginator.paginate():
                    for key in page.get("Keys", []):
                        try:
                            key_info = await self._call_with_retry_and_circuit_breaker(
                                "kms",
                                kms.describe_key,
                                KeyId=key["KeyId"]
                            )
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
                        except Exception as e:
                            logger.debug(f"KMS key describe error: {e}")
        except CircuitBreakerOpenException as e:
            logger.warning(f"KMS circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"KMS discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_sns(self, region: str) -> list[dict[str, Any]]:
        """Discover SNS topics."""
        resources = []
        try:
            async with self._session.create_client(
                "sns", region_name=region, **self._get_client_config()
            ) as sns:
                paginator = sns.get_paginator("list_topics")
                async for page in paginator.paginate():
                    for topic in page.get("Topics", []):
                        topic_arn = topic["TopicArn"]
                        name = topic_arn.split(":")[-1]
                        try:
                            attrs_resp = await self._call_with_retry_and_circuit_breaker(
                                "sns",
                                sns.get_topic_attributes,
                                TopicArn=topic_arn
                            )
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"SNS circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"SNS discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_sqs(self, region: str) -> list[dict[str, Any]]:
        """Discover SQS queues."""
        resources = []
        try:
            async with self._session.create_client(
                "sqs", region_name=region, **self._get_client_config()
            ) as sqs:
                response = await self._call_with_retry_and_circuit_breaker(
                    "sqs",
                    sqs.list_queues
                )
                for queue_url in response.get("QueueUrls", []):
                    name = queue_url.split("/")[-1]
                    try:
                        attrs_resp = await self._call_with_retry_and_circuit_breaker(
                            "sqs",
                            sqs.get_queue_attributes,
                            QueueUrl=queue_url,
                            AttributeNames=["All"]
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"SQS circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"SQS discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_dynamodb(self, region: str) -> list[dict[str, Any]]:
        """Discover DynamoDB tables."""
        resources = []
        try:
            async with self._session.create_client(
                "dynamodb", region_name=region, **self._get_client_config()
            ) as dynamodb:
                paginator = dynamodb.get_paginator("list_tables")
                async for page in paginator.paginate():
                    for table_name in page.get("TableNames", []):
                        try:
                            desc_resp = await self._call_with_retry_and_circuit_breaker(
                                "dynamodb",
                                dynamodb.describe_table,
                                TableName=table_name
                            )
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"DynamoDB circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"DynamoDB discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_secretsmanager(self, region: str) -> list[dict[str, Any]]:
        """Discover Secrets Manager secrets."""
        resources = []
        try:
            async with self._session.create_client(
                "secretsmanager", region_name=region, **self._get_client_config()
            ) as sm:
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"Secrets Manager circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"Secrets Manager discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
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
        try:
            async with self._session.create_client(
                "cloudfront", region_name="us-east-1", **self._get_client_config()
            ) as cloudfront:
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"CloudFront circuit breaker open: {e}")
        except Exception as e:
            logger.error(f"CloudFront discovery failed: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_ecs(self, region: str) -> list[dict[str, Any]]:
        """Discover ECS clusters and task definitions."""
        resources = []
        try:
            async with self._session.create_client(
                "ecs", region_name=region, **self._get_client_config()
            ) as ecs:
                paginator = ecs.get_paginator("list_clusters")
                async for page in paginator.paginate():
                    for cluster_arn in page.get("clusterArns", []):
                        try:
                            cluster = await self._call_with_retry_and_circuit_breaker(
                                "ecs",
                                ecs.describe_clusters,
                                clusters=[cluster_arn]
                            )
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
                        except Exception as e:
                            logger.debug(f"ECS cluster describe error: {e}")
        except CircuitBreakerOpenException as e:
            logger.warning(f"ECS circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"ECS discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_elasticache(self, region: str) -> list[dict[str, Any]]:
        """Discover ElastiCache clusters."""
        resources = []
        try:
            async with self._session.create_client(
                "elasticache", region_name=region, **self._get_client_config()
            ) as elasticache:
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"ElastiCache circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"ElastiCache discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_config(self, region: str) -> list[dict[str, Any]]:
        """Discover Config rules."""
        resources = []
        try:
            async with self._session.create_client(
                "config", region_name=region, **self._get_client_config()
            ) as config_client:
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"Config circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"Config discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_route53(self, region: str) -> list[dict[str, Any]]:
        """Discover Route53 hosted zones (global service)."""
        resources = []
        try:
            async with self._session.create_client(
                "route53", region_name="us-east-1", **self._get_client_config()
            ) as r53:
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"Route53 circuit breaker open: {e}")
        except Exception as e:
            logger.error(f"Route53 discovery failed: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_elbv2(self, region: str) -> list[dict[str, Any]]:
        """Discover ALB and NLB load balancers."""
        resources = []
        try:
            async with self._session.create_client(
                "elbv2", region_name=region, **self._get_client_config()
            ) as elbv2:
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"ELBv2 circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"ELBv2 discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_elb(self, region: str) -> list[dict[str, Any]]:
        """Discover Classic Load Balancers."""
        resources = []
        try:
            async with self._session.create_client(
                "elb", region_name=region, **self._get_client_config()
            ) as elb:
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"ELB circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"ELB discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_apigateway(self, region: str) -> list[dict[str, Any]]:
        """Discover API Gateway REST APIs and HTTP APIs."""
        resources = []
        try:
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
                except Exception as e:
                    logger.warning(f"API Gateway v1 discovery failed in {region}: {e}")

            # HTTP APIs (v2)
            async with self._session.create_client(
                "apigatewayv2", region_name=region, **self._get_client_config()
            ) as apigwv2:
                try:
                    response = await self._call_with_retry_and_circuit_breaker(
                        "apigateway",
                        apigwv2.get_apis
                    )
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
                except Exception as e:
                    logger.warning(f"API Gateway v2 discovery failed in {region}: {e}")
        except CircuitBreakerOpenException as e:
            logger.warning(f"API Gateway circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"API Gateway discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")

        return resources

    async def _discover_ecr(self, region: str) -> list[dict[str, Any]]:
        """Discover ECR repositories."""
        resources = []
        try:
            async with self._session.create_client(
                "ecr", region_name=region, **self._get_client_config()
            ) as ecr:
                # get_paginator is synchronous in aiobotocore — do NOT await it
                paginator = ecr.get_paginator("describe_repositories")
                async for page in paginator.paginate():
                    for repo in page.get("repositories", []):
                        is_public = False
                        try:
                            policy_resp = await self._call_with_retry_and_circuit_breaker(
                                "ecr",
                                ecr.get_repository_policy,
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"ECR circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"ECR discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_efs(self, region: str) -> list[dict[str, Any]]:
        """Discover EFS file systems."""
        resources = []
        try:
            async with self._session.create_client(
                "efs", region_name=region, **self._get_client_config()
            ) as efs:
                # get_paginator is synchronous in aiobotocore — do NOT await it
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
        except CircuitBreakerOpenException as e:
            logger.warning(f"EFS circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"EFS discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

    async def _discover_cloudtrail(self, region: str) -> list[dict[str, Any]]:
        """Discover CloudTrail trails."""
        resources = []
        try:
            async with self._session.create_client(
                "cloudtrail", region_name=region, **self._get_client_config()
            ) as ct:
                response = await self._call_with_retry_and_circuit_breaker(
                    "cloudtrail",
                    ct.describe_trails,
                    includeShadowTrails=False
                )
                for trail in response.get("trailList", []):
                    resources.append({
                        "type": "CloudTrailTrail",
                        "id": trail["TrailARN"],
                        "name": trail["Name"],
                        "region": region,
                        "tags": {},
                        "raw": trail,
                    })
        except CircuitBreakerOpenException as e:
            logger.warning(f"CloudTrail circuit breaker open in {region}: {e}")
        except Exception as e:
            logger.error(f"CloudTrail discovery failed in {region}: {type(e).__name__}: {str(e)[:200]}")
        
        return resources

