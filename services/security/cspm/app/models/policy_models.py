"""Policy Engine database models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    JSON,
    String,
    Text,
)

from ..db_helper import Base


class CustomRegoRuleModel(Base):
    """Stores custom Rego rules created by organizations."""

    __tablename__ = "cspm_custom_rego_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    rule_id = Column(String, nullable=False)  # user-defined identifier
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    rego_content = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_custom_rule_org_id", "organization_id", "rule_id"),
    )


class RegoRuleVersionModel(Base):
    """Stores version history for Rego rules to support rollback."""

    __tablename__ = "cspm_rego_rule_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String, nullable=False, index=True)
    organization_id = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
    rego_content = Column(Text, nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_rule_version_rule", "rule_id", "version"),
    )


class PolicyHierarchyModel(Base):
    """Stores policy assignments at different hierarchy levels."""

    __tablename__ = "cspm_policy_hierarchy"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    level = Column(String, nullable=False)  # organization, team, project
    level_id = Column(String, nullable=False)  # org_id, team_id, or project_id
    rule_id = Column(String, nullable=False)
    enforcement_mode = Column(String, default="alert")  # alert, block, auto_remediate
    is_override = Column(Boolean, default=False)
    override_justification = Column(Text, nullable=True)
    overridden_by = Column(String, nullable=True)
    overridden_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_policy_hierarchy_org_level", "organization_id", "level", "level_id"),
    )


class PolicyExceptionModel(Base):
    """Stores policy exceptions (suppressions) with expiry and justification."""

    __tablename__ = "cspm_policy_exceptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    rule_id = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    justification = Column(Text, nullable=False)
    granted_by = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_policy_exception_org_rule", "organization_id", "rule_id"),
        Index("ix_policy_exception_expires", "expires_at"),
    )


class PolicyAuditLogModel(Base):
    """Stores audit trail of all policy changes and actions."""

    __tablename__ = "cspm_policy_audit_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # rule_created, rule_updated, exception_granted, mode_changed
    rule_id = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    actor = Column(String, nullable=False)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_policy_audit_org", "organization_id"),
        Index("ix_policy_audit_timestamp", "timestamp"),
    )
