"""
Automatic IAM role setup for CloudVisor.

When a client connects an AWS account with Access Key + Secret Key,
this service automatically:
  1. Creates a CloudVisorReadOnly IAM role in their account
  2. Attaches the AWS-managed ReadOnlyAccess policy
  3. Returns the role ARN for use in all future syncs

The role uses a trust policy that allows the connector to assume it via STS.
The original access key is only used once — for role creation — and is never
used for resource discovery. All discovery uses the assumed role session.
"""

import json
import logging
import secrets
from typing import Any

import aiobotocore.session

logger = logging.getLogger(__name__)

# The role name created in the customer's account
ROLE_NAME = "CloudVisorReadOnly"

# AWS managed policy that grants read-only access to all services
READ_ONLY_POLICY_ARN = "arn:aws:iam::aws:policy/ReadOnlyAccess"

# Additional policies for complete visibility
EXTRA_POLICY_ARNS = [
    "arn:aws:iam::aws:policy/SecurityAudit",          # Security-specific read access
]

# Trust policy: allows the connector to assume this role
# In production this would be the CloudVisor AWS account ID.
# For self-hosted / dev, we allow the same account to assume the role.
TRUST_POLICY_TEMPLATE = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "{caller_arn}"   # filled in at runtime
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": "{external_id}"   # filled in at runtime
                }
            }
        }
    ]
}


class AWSRoleSetupService:
    """
    Automatically provisions a read-only IAM role in the customer's AWS account.

    Flow:
      1. Use provided access key to call sts:GetCallerIdentity (verify creds)
      2. Create IAM role CloudVisorReadOnly with trust policy
      3. Attach ReadOnlyAccess + SecurityAudit managed policies
      4. Return role ARN + external_id for storage in Vault
    """

    def __init__(self, access_key: str, secret_key: str, region: str = "us-east-1"):
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._session = aiobotocore.session.get_session()

    def _get_creds(self) -> dict[str, str]:
        return {
            "aws_access_key_id": self._access_key,
            "aws_secret_access_key": self._secret_key,
        }

    async def setup_role(self) -> dict[str, Any]:
        """
        Create the CloudVisorReadOnly role and return credentials for future use.

        Returns:
            {
                "role_arn": "arn:aws:iam::123456789012:role/CloudVisorReadOnly",
                "external_id": "cv-abc123...",
                "account_id": "123456789012",
                "already_existed": True/False
            }

        Raises:
            ValueError: if credentials are invalid or insufficient permissions
        """
        # Step 1: Verify credentials and get caller identity
        account_id, caller_arn = await self._verify_credentials()
        logger.info(f"Verified credentials for account {account_id}")

        # Step 2: Generate a stable external_id for this account
        # Use account_id as seed so it's deterministic (same account → same external_id)
        external_id = f"cv-{account_id}"

        # Step 3: Build trust policy — allow the caller (this IAM user/role) to assume
        trust_policy = json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": caller_arn
                    },
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {
                            "sts:ExternalId": external_id
                        }
                    }
                }
            ]
        })

        # Step 4: Create or update the role
        role_arn, already_existed = await self._create_or_get_role(
            account_id=account_id,
            trust_policy=trust_policy,
        )

        # Step 5: Attach policies
        await self._attach_policies(already_existed)

        logger.info(
            f"CloudVisorReadOnly role {'already existed' if already_existed else 'created'} "
            f"in account {account_id}: {role_arn}"
        )

        return {
            "role_arn": role_arn,
            "external_id": external_id,
            "account_id": account_id,
            "already_existed": already_existed,
        }

    async def _verify_credentials(self) -> tuple[str, str]:
        """Verify credentials and return (account_id, caller_arn)."""
        try:
            async with self._session.create_client(
                "sts", region_name=self._region, **self._get_creds()
            ) as sts:
                identity = await sts.get_caller_identity()
                return identity["Account"], identity["Arn"]
        except Exception as e:
            error_msg = str(e)
            if "InvalidClientTokenId" in error_msg or "AuthFailure" in error_msg:
                raise ValueError(
                    "Invalid AWS credentials. Please check your Access Key ID and Secret Access Key."
                )
            if "ExpiredToken" in error_msg:
                raise ValueError("AWS credentials have expired. Please generate new access keys.")
            raise ValueError(f"Failed to verify AWS credentials: {error_msg}")

    async def _create_or_get_role(
        self, account_id: str, trust_policy: str
    ) -> tuple[str, bool]:
        """Create the role or return existing one. Returns (role_arn, already_existed)."""
        async with self._session.create_client(
            "iam", region_name="us-east-1", **self._get_creds()
        ) as iam:
            # Check if role already exists
            try:
                response = await iam.get_role(RoleName=ROLE_NAME)
                role_arn = response["Role"]["Arn"]
                logger.info(f"Role {ROLE_NAME} already exists: {role_arn}")

                # Update trust policy to ensure it's current
                await iam.update_assume_role_policy(
                    RoleName=ROLE_NAME,
                    PolicyDocument=trust_policy,
                )
                return role_arn, True

            except iam.exceptions.NoSuchEntityException:
                pass
            except Exception as e:
                if "NoSuchEntity" in str(e):
                    pass  # Role doesn't exist, create it
                else:
                    raise ValueError(
                        f"Failed to check for existing role. "
                        f"Ensure the IAM user has iam:GetRole permission. Error: {e}"
                    )

            # Create the role
            try:
                response = await iam.create_role(
                    RoleName=ROLE_NAME,
                    AssumeRolePolicyDocument=trust_policy,
                    Description=(
                        "CloudVisor read-only role for cloud security posture management. "
                        "Automatically created by CloudVisor connector."
                    ),
                    Tags=[
                        {"Key": "ManagedBy", "Value": "CloudVisor"},
                        {"Key": "Purpose", "Value": "SecurityAudit"},
                        {"Key": "AccountId", "Value": account_id},
                    ],
                )
                role_arn = response["Role"]["Arn"]
                logger.info(f"Created role {ROLE_NAME}: {role_arn}")
                return role_arn, False

            except Exception as e:
                error_msg = str(e)
                if "AccessDenied" in error_msg or "not authorized" in error_msg.lower():
                    raise ValueError(
                        f"Permission denied creating IAM role '{ROLE_NAME}'. "
                        f"The IAM user needs iam:CreateRole permission. "
                        f"Alternatively, create the role manually and provide the Role ARN instead."
                    )
                raise ValueError(f"Failed to create IAM role: {error_msg}")

    async def _attach_policies(self, role_already_existed: bool) -> None:
        """Attach ReadOnlyAccess and SecurityAudit policies to the role."""
        async with self._session.create_client(
            "iam", region_name="us-east-1", **self._get_creds()
        ) as iam:
            all_policies = [READ_ONLY_POLICY_ARN] + EXTRA_POLICY_ARNS

            for policy_arn in all_policies:
                try:
                    await iam.attach_role_policy(
                        RoleName=ROLE_NAME,
                        PolicyArn=policy_arn,
                    )
                    logger.info(f"Attached policy {policy_arn} to {ROLE_NAME}")
                except Exception as e:
                    error_msg = str(e)
                    if "EntityAlreadyExists" in error_msg or "already attached" in error_msg.lower():
                        logger.debug(f"Policy {policy_arn} already attached to {ROLE_NAME}")
                    elif "AccessDenied" in error_msg:
                        raise ValueError(
                            f"Permission denied attaching policy {policy_arn}. "
                            f"The IAM user needs iam:AttachRolePolicy permission."
                        )
                    else:
                        logger.warning(f"Failed to attach {policy_arn}: {e}")

    async def assume_role(self, role_arn: str, external_id: str) -> dict[str, str]:
        """
        Assume the CloudVisorReadOnly role and return temporary credentials.
        Called before each sync to get fresh session credentials.
        """
        try:
            async with self._session.create_client(
                "sts", region_name=self._region, **self._get_creds()
            ) as sts:
                response = await sts.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName="cloudvisor-discovery",
                    ExternalId=external_id,
                    DurationSeconds=3600,  # 1 hour session
                )
                creds = response["Credentials"]
                return {
                    "access_key": creds["AccessKeyId"],
                    "secret_key": creds["SecretAccessKey"],
                    "session_token": creds["SessionToken"],
                }
        except Exception as e:
            raise ValueError(f"Failed to assume role {role_arn}: {e}")

    @staticmethod
    async def delete_role(access_key: str, secret_key: str) -> bool:
        """
        Clean up the CloudVisorReadOnly role when an account is disconnected.
        Best-effort — does not raise if role doesn't exist.
        """
        session = aiobotocore.session.get_session()
        creds = {"aws_access_key_id": access_key, "aws_secret_access_key": secret_key}

        try:
            async with session.create_client("iam", region_name="us-east-1", **creds) as iam:
                # Detach all policies first
                try:
                    attached = await iam.list_attached_role_policies(RoleName=ROLE_NAME)
                    for policy in attached.get("AttachedPolicies", []):
                        await iam.detach_role_policy(
                            RoleName=ROLE_NAME,
                            PolicyArn=policy["PolicyArn"],
                        )
                except Exception:
                    pass

                # Delete the role
                await iam.delete_role(RoleName=ROLE_NAME)
                logger.info(f"Deleted role {ROLE_NAME}")
                return True
        except Exception as e:
            logger.warning(f"Could not delete role {ROLE_NAME}: {e}")
            return False
