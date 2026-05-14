"""IAM Analysis database models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
)

from ..db_helper import Base


class IAMAnalysisResultModel(Base):
    """Stores IAM identity analysis results including excess permissions and risk scores."""

    __tablename__ = "cspm_iam_analysis_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    identity_arn = Column(String, nullable=False, index=True)
    identity_type = Column(String, nullable=False)  # user, role, service_account, group
    provider = Column(String, nullable=False)
    account_id = Column(String, nullable=False)
    granted_permissions = Column(JSON, default=list)  # list of permission strings
    used_permissions = Column(JSON, default=list)  # from CloudTrail
    excess_permissions = Column(JSON, default=list)  # granted - used
    excess_ratio = Column(Float, default=0.0)  # len(excess) / len(granted)
    is_dormant = Column(Boolean, default=False)
    last_activity_at = Column(DateTime, nullable=True)
    has_mfa = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    risk_score = Column(Integer, default=0)
    recommended_policy = Column(JSON, nullable=True)  # least-privilege policy
    lookback_days = Column(Integer, default=90)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_iam_analysis_org_identity", "organization_id", "identity_arn", unique=True),
    )


class IAMCrossAccountTrustModel(Base):
    """Stores cross-account trust relationships and their risk assessments."""

    __tablename__ = "cspm_iam_cross_account_trusts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    source_account_id = Column(String, nullable=False)
    target_account_id = Column(String, nullable=False)
    trusted_principal = Column(String, nullable=False)
    trust_conditions = Column(JSON, default=dict)
    has_external_id = Column(Boolean, default=False)
    has_wildcard_principal = Column(Boolean, default=False)
    is_overly_permissive = Column(Boolean, default=False)
    risk_score = Column(Integer, default=0)
    discovered_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cross_account_org", "organization_id"),
    )


class IAMEscalationPathModel(Base):
    """Stores discovered privilege escalation paths."""

    __tablename__ = "cspm_iam_escalation_paths"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    source_identity = Column(String, nullable=False)
    target_identity = Column(String, nullable=False)
    path_hops = Column(Integer, nullable=False)
    path_details = Column(JSON, default=list)  # list of {identity, permission, action}
    target_privilege_level = Column(String, nullable=False)  # admin, power_user, read_only
    severity = Column(String, nullable=False)
    pattern_ids = Column(JSON, default=list)  # which known patterns matched
    discovered_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_escalation_org_severity", "organization_id", "severity"),
    )


class IAMServiceAccountModel(Base):
    """Stores service account risk analysis results."""

    __tablename__ = "cspm_iam_service_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=False)
    service_account_id = Column(String, nullable=False)
    permission_breadth = Column(Integer, default=0)  # number of distinct permissions
    resource_scope = Column(JSON, default=list)  # list of resource ARN patterns
    intended_scope = Column(JSON, default=list)  # expected scope
    has_scope_violation = Column(Boolean, default=False)
    last_key_rotation = Column(DateTime, nullable=True)
    key_age_days = Column(Integer, default=0)
    risk_score = Column(Integer, default=0)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
