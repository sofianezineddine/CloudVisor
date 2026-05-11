"""Kafka consumers for real-time cloud event streams.

Each consumer polls its cloud provider's event stream and translates
provider-specific events into CloudVisor Kafka events (resource.updated /
resource.deleted).  The consumers are intentionally lightweight — they
detect *that* a resource changed and trigger a targeted re-fetch, rather
than trying to reconstruct the full resource state from the event payload.
"""

import asyncio
import json
import logging
from typing import Any

from ..core.time_utils import utcnow
from ..producers import ResourceEventProducer

logger = logging.getLogger(__name__)


# ─── AWS CloudTrail → SQS consumer ───────────────────────────────────────────

class CloudTrailConsumer:
    """
    Polls an SQS queue that receives CloudTrail S3 notifications.

    Flow: CloudTrail → S3 → S3 Event Notification → SQS → This consumer → Kafka

    The consumer:
    1. Long-polls the SQS queue for messages (up to 10 at a time, 20s wait)
    2. Parses the S3 notification to get the CloudTrail log object key
    3. Downloads and parses the CloudTrail log from S3
    4. For each CloudTrail record, identifies the affected resource ARN
    5. Emits resource.updated / resource.deleted Kafka events
    6. Deletes the SQS message on success
    """

    # CloudTrail event names that indicate a resource was created/modified
    WRITE_EVENTS = frozenset([
        "RunInstances", "StartInstances", "StopInstances", "TerminateInstances",
        "CreateBucket", "DeleteBucket", "PutBucketPolicy", "PutBucketAcl",
        "CreateRole", "DeleteRole", "AttachRolePolicy", "DetachRolePolicy",
        "CreateUser", "DeleteUser",
        "CreateSecurityGroup", "DeleteSecurityGroup", "AuthorizeSecurityGroupIngress",
        "CreateVpc", "DeleteVpc",
        "CreateSubnet", "DeleteSubnet",
        "CreateFunction20150331", "DeleteFunction20150331",
        "CreateDBInstance", "DeleteDBInstance",
        "CreateCluster",  # EKS
        "CreateKey", "DisableKey", "EnableKey",  # KMS
        "CreateSecret", "DeleteSecret",  # Secrets Manager
    ])

    def __init__(
        self,
        sqs_queue_url: str,
        event_producer: ResourceEventProducer,
        credentials: dict[str, Any],
        organization_id: str,
        account_id: str,
        region: str = "us-east-1",
    ):
        self._sqs_queue_url = sqs_queue_url
        self._producer = event_producer
        self._credentials = credentials
        self._organization_id = organization_id
        self._account_id = account_id
        self._region = region
        self._running = False
        self._poll_interval = 5  # seconds between polls when queue is empty

    async def start(self) -> None:
        """Start the consumer loop in the background."""
        self._running = True
        logger.info(f"CloudTrail consumer started for account {self._account_id}")
        asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        """Signal the consumer loop to stop."""
        self._running = False
        logger.info(f"CloudTrail consumer stopped for account {self._account_id}")

    async def _consume_loop(self) -> None:
        """Main polling loop."""
        import aiobotocore.session
        session = aiobotocore.session.get_session()

        while self._running:
            try:
                async with session.create_client(
                    "sqs",
                    region_name=self._region,
                    **self._get_creds(),
                ) as sqs:
                    response = await sqs.receive_message(
                        QueueUrl=self._sqs_queue_url,
                        MaxNumberOfMessages=10,
                        WaitTimeSeconds=20,  # long-poll
                        AttributeNames=["All"],
                    )
                    messages = response.get("Messages", [])
                    if not messages:
                        continue

                    for msg in messages:
                        try:
                            await self._process_sqs_message(msg, session)
                            # Delete on success
                            await sqs.delete_message(
                                QueueUrl=self._sqs_queue_url,
                                ReceiptHandle=msg["ReceiptHandle"],
                            )
                        except Exception as e:
                            logger.warning(f"Failed to process SQS message: {e}")

            except Exception as e:
                logger.error(f"CloudTrail consumer error: {e}")
                await asyncio.sleep(self._poll_interval)

    async def _process_sqs_message(
        self, msg: dict[str, Any], session: Any
    ) -> None:
        """Parse an SQS message and emit Kafka events for affected resources."""
        body = json.loads(msg["Body"])

        # S3 event notification wraps the actual message
        if "Message" in body:
            body = json.loads(body["Message"])

        records = body.get("Records", [])
        for record in records:
            if record.get("eventSource") != "aws:s3":
                continue
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]

            # Download and parse the CloudTrail log
            await self._process_cloudtrail_log(session, bucket, key)

    async def _process_cloudtrail_log(
        self, session: Any, bucket: str, key: str
    ) -> None:
        """Download a CloudTrail log from S3 and emit events for each record."""
        import gzip
        import io

        async with session.create_client(
            "s3", region_name=self._region, **self._get_creds()
        ) as s3:
            response = await s3.get_object(Bucket=bucket, Key=key)
            body = await response["Body"].read()

        # CloudTrail logs are gzip-compressed JSON
        if key.endswith(".gz"):
            body = gzip.decompress(body)

        log_data = json.loads(body)
        for record in log_data.get("Records", []):
            await self._process_cloudtrail_record(record)

    async def _process_cloudtrail_record(self, record: dict[str, Any]) -> None:
        """Emit a Kafka event for a single CloudTrail record."""
        event_name = record.get("eventName", "")
        resources = record.get("resources", [])
        correlation_id = record.get("eventID", "")

        for resource in resources:
            arn = resource.get("ARN", "")
            if not arn:
                continue

            if "Delete" in event_name or "Terminate" in event_name or "Remove" in event_name:
                await self._producer.emit_resource_deleted(
                    cloud_resource_id=arn,
                    account_id=self._account_id,
                    organization_id=self._organization_id,
                    provider="aws",
                    region=record.get("awsRegion", "global"),
                    correlation_id=correlation_id,
                )
            else:
                # For create/modify events, emit a minimal updated event.
                # The graph service will re-fetch the full resource state.
                from cloudvisor_types.models import CloudResource, CloudProvider, Environment
                import uuid

                resource_obj = CloudResource(
                    id=str(uuid.uuid4()),
                    cloud_resource_id=arn,
                    provider=CloudProvider.AWS,
                    account_id=self._account_id,
                    region=record.get("awsRegion", "global"),
                    resource_type=f"aws::{resource.get('type', 'unknown').lower()}",
                    name=arn.split("/")[-1] or arn.split(":")[-1],
                    tags={},
                    raw=record,
                    organization_id=self._organization_id,
                    is_public=False,
                    environment=Environment.UNKNOWN,
                    first_seen_at=utcnow(),
                    last_seen_at=utcnow(),
                )
                await self._producer.emit_resource_updated(
                    resource=resource_obj,
                    correlation_id=correlation_id,
                )

    def _get_creds(self) -> dict[str, Any]:
        creds = {
            "aws_access_key_id": self._credentials.get("access_key"),
            "aws_secret_access_key": self._credentials.get("secret_key"),
        }
        if self._credentials.get("session_token"):
            creds["aws_session_token"] = self._credentials["session_token"]
        return creds


# ─── Azure Monitor → Event Hub consumer ──────────────────────────────────────

class AzureMonitorConsumer:
    """
    Consumes Azure Monitor activity log events via Azure Event Hub.

    Flow: Azure Monitor → Event Hub → This consumer → Kafka

    Requires:
    - An Event Hub namespace + hub configured to receive Azure Monitor activity logs
    - A consumer group (default: $Default)
    - Connection string with Listen permission
    """

    def __init__(
        self,
        event_hub_connection_string: str,
        event_hub_name: str,
        event_producer: ResourceEventProducer,
        organization_id: str,
        subscription_id: str,
        consumer_group: str = "$Default",
    ):
        self._connection_string = event_hub_connection_string
        self._event_hub_name = event_hub_name
        self._consumer_group = consumer_group
        self._producer = event_producer
        self._organization_id = organization_id
        self._subscription_id = subscription_id
        self._running = False

    async def start(self) -> None:
        """Start consuming Azure Monitor events."""
        self._running = True
        logger.info(f"Azure Monitor consumer started for subscription {self._subscription_id}")
        asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        """Stop consuming Azure Monitor events."""
        self._running = False
        logger.info(f"Azure Monitor consumer stopped for subscription {self._subscription_id}")

    async def _consume_loop(self) -> None:
        """Main Event Hub consumer loop."""
        try:
            from azure.eventhub.aio import EventHubConsumerClient

            async with EventHubConsumerClient.from_connection_string(
                self._connection_string,
                consumer_group=self._consumer_group,
                eventhub_name=self._event_hub_name,
            ) as client:
                await client.receive(
                    on_event=self._on_event,
                    starting_position="-1",  # start from latest
                )
        except ImportError:
            logger.warning("azure-eventhub not installed — Azure Monitor consumer disabled")
        except Exception as e:
            logger.error(f"Azure Monitor consumer error: {e}")

    async def _on_event(self, partition_context: Any, event: Any) -> None:
        """Handle a single Event Hub event."""
        if not self._running:
            return
        try:
            body = json.loads(event.body_as_str())
            records = body.get("records", [body])  # activity logs wrap in "records"
            for record in records:
                await self._process_activity_log(record)
            await partition_context.update_checkpoint(event)
        except Exception as e:
            logger.warning(f"Azure event processing error: {e}")

    async def _process_activity_log(self, record: dict[str, Any]) -> None:
        """Process a single Azure activity log record."""
        operation = record.get("operationName", {})
        if isinstance(operation, dict):
            operation_name = operation.get("value", "")
        else:
            operation_name = str(operation)

        resource_id = record.get("resourceId", "")
        if not resource_id:
            return

        status = record.get("status", {})
        if isinstance(status, dict):
            status_value = status.get("value", "")
        else:
            status_value = str(status)

        # Only process succeeded operations
        if status_value.lower() not in ("succeeded", "success"):
            return

        correlation_id = record.get("correlationId", "")
        region = record.get("location", "global")

        if "/delete" in operation_name.lower():
            await self._producer.emit_resource_deleted(
                cloud_resource_id=resource_id,
                account_id=self._subscription_id,
                organization_id=self._organization_id,
                provider="azure",
                region=region,
                correlation_id=correlation_id,
            )
        elif "/write" in operation_name.lower():
            from cloudvisor_types.models import CloudResource, CloudProvider, Environment
            import uuid

            # Extract resource type from the resource ID path
            parts = resource_id.split("/")
            resource_type = f"{parts[-3]}/{parts[-2]}" if len(parts) >= 4 else "unknown"

            resource_obj = CloudResource(
                id=str(uuid.uuid4()),
                cloud_resource_id=resource_id,
                provider=CloudProvider.AZURE,
                account_id=self._subscription_id,
                region=region,
                resource_type=f"azure::{resource_type.lower()}",
                name=parts[-1] if parts else resource_id,
                tags={},
                raw=record,
                organization_id=self._organization_id,
                is_public=False,
                environment=Environment.UNKNOWN,
                first_seen_at=utcnow(),
                last_seen_at=utcnow(),
            )
            await self._producer.emit_resource_updated(
                resource=resource_obj,
                correlation_id=correlation_id,
            )


# ─── GCP Cloud Asset Inventory → Pub/Sub consumer ────────────────────────────

class GCPAssetConsumer:
    """
    Consumes GCP Cloud Asset Inventory change feeds via Pub/Sub.

    Flow: Cloud Asset Inventory → Pub/Sub topic → This consumer → Kafka

    Setup required in GCP:
    1. Enable Cloud Asset API
    2. Create a Pub/Sub topic for asset feeds
    3. Create a feed: gcloud asset feeds create cloudvisor-feed --project=PROJECT
       --asset-types="compute.googleapis.com/Instance,storage.googleapis.com/Bucket,..."
       --content-type=RESOURCE --pubsub-topic=projects/PROJECT/topics/TOPIC
    """

    def __init__(
        self,
        pubsub_subscription: str,
        event_producer: ResourceEventProducer,
        credentials: dict[str, Any],
        organization_id: str,
        project_id: str,
    ):
        self._subscription = pubsub_subscription
        self._producer = event_producer
        self._credentials = credentials
        self._organization_id = organization_id
        self._project_id = project_id
        self._running = False

    async def start(self) -> None:
        """Start consuming GCP asset events."""
        self._running = True
        logger.info(f"GCP Asset consumer started for project {self._project_id}")
        asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        """Stop consuming GCP asset events."""
        self._running = False
        logger.info(f"GCP Asset consumer stopped for project {self._project_id}")

    async def _consume_loop(self) -> None:
        """Pull messages from Pub/Sub subscription.

        google-cloud-pubsub's ``subscribe`` calls back from a separate thread,
        so we cannot call ``asyncio.create_task`` from inside it — that requires
        a running loop on the calling thread. We capture the current (asyncio)
        event loop and use ``run_coroutine_threadsafe`` to hand work back to it.
        """
        main_loop = asyncio.get_running_loop()

        try:
            from google.cloud import pubsub_v1
            from google.oauth2 import service_account

            sa_json = self._credentials.get("service_account_json")
            if isinstance(sa_json, str):
                sa_json = json.loads(sa_json)

            if sa_json:
                gcp_creds = service_account.Credentials.from_service_account_info(
                    sa_json,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
            else:
                import google.auth
                gcp_creds, _ = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )

            subscriber = pubsub_v1.SubscriberClient(credentials=gcp_creds)

            def callback(message: Any) -> None:
                """Runs on Pub/Sub's thread — marshal work to the asyncio loop."""
                try:
                    data = json.loads(message.data.decode("utf-8"))
                    # Schedule the async handler on the asyncio loop
                    future = asyncio.run_coroutine_threadsafe(
                        self._process_asset_event(data), main_loop
                    )
                    # Block this thread until processing finishes so we can
                    # ack/nack deterministically.
                    future.result(timeout=30)
                    message.ack()
                except Exception as e:
                    logger.warning(f"GCP asset message processing error: {e}")
                    message.nack()

            streaming_pull = subscriber.subscribe(self._subscription, callback=callback)
            logger.info(f"GCP: listening on {self._subscription}")

            while self._running:
                await asyncio.sleep(1)

            streaming_pull.cancel()
            try:
                await asyncio.to_thread(streaming_pull.result, 5)
            except Exception:
                pass

        except ImportError:
            logger.warning("google-cloud-pubsub not installed — GCP Asset consumer disabled")
        except Exception as e:
            logger.error(f"GCP Asset consumer error: {e}")

    async def _process_asset_event(self, data: dict[str, Any]) -> None:
        """Process a single Cloud Asset Inventory change event."""
        asset = data.get("asset", {})
        asset_name = asset.get("name", "")
        asset_type = asset.get("assetType", "")
        update_time = data.get("window", {}).get("startTime", "")

        if not asset_name:
            return

        # Determine if this is a deletion (asset has no resource data)
        is_deleted = not asset.get("resource") and not asset.get("iamPolicy")

        region = self._extract_gcp_region(asset_name)
        correlation_id = data.get("priorAssetState", "")

        if is_deleted:
            await self._producer.emit_resource_deleted(
                cloud_resource_id=asset_name,
                account_id=self._project_id,
                organization_id=self._organization_id,
                provider="gcp",
                region=region,
                correlation_id=correlation_id,
            )
        else:
            from cloudvisor_types.models import CloudResource, CloudProvider, Environment
            import uuid

            resource_type = asset_type.replace("googleapis.com/", "").lower()
            name = asset_name.split("/")[-1]

            resource_obj = CloudResource(
                id=str(uuid.uuid4()),
                cloud_resource_id=asset_name,
                provider=CloudProvider.GCP,
                account_id=self._project_id,
                region=region,
                resource_type=f"gcp::{resource_type}",
                name=name,
                tags=dict(asset.get("resource", {}).get("data", {}).get("labels", {})),
                raw=asset,
                organization_id=self._organization_id,
                is_public=False,
                environment=Environment.UNKNOWN,
                first_seen_at=utcnow(),
                last_seen_at=utcnow(),
            )
            await self._producer.emit_resource_updated(
                resource=resource_obj,
                correlation_id=correlation_id,
            )

    @staticmethod
    def _extract_gcp_region(asset_name: str) -> str:
        """Extract region/zone from a GCP resource name."""
        parts = asset_name.split("/")
        for i, part in enumerate(parts):
            if part in ("regions", "zones", "locations") and i + 1 < len(parts):
                return parts[i + 1]
        return "global"


# ─── OCI Events Service consumer ─────────────────────────────────────────────

class OCIEventsConsumer:
    """
    Polls OCI Events Service for resource change notifications.

    Flow: OCI resource change → OCI Events → Notifications → Streaming → This consumer → Kafka

    OCI Events can be delivered to:
    - OCI Streaming (Kafka-compatible) — preferred
    - OCI Notifications (email/HTTPS webhook) — not used here

    This consumer polls an OCI Stream (Kafka-compatible endpoint).
    """

    def __init__(
        self,
        stream_ocid: str,
        stream_endpoint: str,
        event_producer: ResourceEventProducer,
        credentials: dict[str, Any],
        organization_id: str,
        tenancy_ocid: str,
        region: str = "us-ashburn-1",
    ):
        self._stream_ocid = stream_ocid
        self._stream_endpoint = stream_endpoint
        self._producer = event_producer
        self._credentials = credentials
        self._organization_id = organization_id
        self._tenancy_ocid = tenancy_ocid
        self._region = region
        self._running = False
        self._cursor: str | None = None

    async def start(self) -> None:
        """Start consuming OCI events."""
        self._running = True
        logger.info(f"OCI Events consumer started for tenancy {self._tenancy_ocid}")
        asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        """Stop consuming OCI events."""
        self._running = False
        logger.info(f"OCI Events consumer stopped for tenancy {self._tenancy_ocid}")

    async def _consume_loop(self) -> None:
        """Poll OCI Streaming for events.

        The OCI Streaming API returns an ``opc-next-cursor`` header on each
        ``get_messages`` response — we use that as the cursor for the next
        call so we don't re-read the same messages. ``consumer_heartbeat`` is
        for group coordination and is NOT the right API for cursor advancement.
        """
        try:
            import oci

            oci_config = {
                "tenancy": self._tenancy_ocid,
                "user": self._credentials.get("user_ocid", ""),
                "fingerprint": self._credentials.get("fingerprint", ""),
                "key_content": self._credentials.get("private_key", ""),
                "region": self._region,
            }

            stream_client = oci.streaming.StreamClient(
                oci_config,
                service_endpoint=self._stream_endpoint,
            )

            # Get initial cursor (LATEST = only new messages)
            if not self._cursor:
                partitions = stream_client.list_partitions(self._stream_ocid).data
                if partitions:
                    cursor_resp = stream_client.create_cursor(
                        self._stream_ocid,
                        oci.streaming.models.CreateCursorDetails(
                            partition=partitions[0].id,
                            type=oci.streaming.models.CreateCursorDetails.TYPE_LATEST,
                        ),
                    )
                    self._cursor = cursor_resp.data.value

            while self._running and self._cursor:
                try:
                    response = stream_client.get_messages(
                        self._stream_ocid,
                        self._cursor,
                        limit=100,
                    )
                    messages = response.data or []
                    if messages:
                        import base64
                        for msg in messages:
                            try:
                                body = json.loads(
                                    base64.b64decode(msg.value).decode("utf-8")
                                )
                                await self._process_oci_event(body)
                            except Exception as e:
                                logger.warning(f"OCI message parse error: {e}")

                    # Advance the cursor using the opc-next-cursor header.
                    # Fall back to the header from response_headers in any casing.
                    next_cursor = None
                    try:
                        headers = getattr(response, "headers", {}) or {}
                        next_cursor = (
                            headers.get("opc-next-cursor")
                            or headers.get("Opc-Next-Cursor")
                            or headers.get("OPC-NEXT-CURSOR")
                        )
                    except Exception:
                        pass

                    if next_cursor:
                        self._cursor = next_cursor
                    elif not messages:
                        # No new messages and no advance cursor — just sleep.
                        await asyncio.sleep(5)

                    if not messages:
                        await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"OCI stream poll error: {e}")
                    await asyncio.sleep(10)

        except ImportError:
            logger.warning("oci SDK not installed — OCI Events consumer disabled")
        except Exception as e:
            logger.error(f"OCI Events consumer error: {e}")

    async def _process_oci_event(self, event: dict[str, Any]) -> None:
        """Process a single OCI event."""
        event_type = event.get("eventType", "")
        resource_id = event.get("data", {}).get("resourceId", "")
        compartment_id = event.get("data", {}).get("compartmentId", "")
        region = event.get("data", {}).get("region", self._region)
        correlation_id = event.get("eventId", "")

        if not resource_id:
            return

        is_delete = any(
            kw in event_type.lower()
            for kw in ("delete", "terminate", "destroy")
        )

        if is_delete:
            await self._producer.emit_resource_deleted(
                cloud_resource_id=resource_id,
                account_id=self._tenancy_ocid,
                organization_id=self._organization_id,
                provider="oci",
                region=region,
                correlation_id=correlation_id,
            )
        else:
            from cloudvisor_types.models import CloudResource, CloudProvider, Environment
            import uuid

            # Derive resource type from event type (e.g. "com.oraclecloud.computeapi.launchinstance")
            parts = event_type.split(".")
            resource_type = parts[-1].lower() if parts else "unknown"

            resource_obj = CloudResource(
                id=str(uuid.uuid4()),
                cloud_resource_id=resource_id,
                provider=CloudProvider.OCI,
                account_id=self._tenancy_ocid,
                region=region,
                resource_type=f"oci::{resource_type}",
                name=resource_id.split(".")[-1],
                tags={},
                raw=event,
                organization_id=self._organization_id,
                is_public=False,
                environment=Environment.UNKNOWN,
                first_seen_at=utcnow(),
                last_seen_at=utcnow(),
            )
            await self._producer.emit_resource_updated(
                resource=resource_obj,
                correlation_id=correlation_id,
            )
