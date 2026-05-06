"""Database models for Policy service."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RuleModel(Base):
    """Rule model for OPA policies."""

    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    rego_code: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    # Use JSON instead of ARRAY(JSON) for portability
    compliance_mapping: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("rule_id", "organization_id", name="uq_rule_id_org"),
        Index("idx_rules_category", "category"),
        Index("idx_rules_provider", "provider"),
        Index("idx_rules_severity", "severity"),
        Index("idx_rules_enabled", "is_enabled"),
    )


class RuleDisableModel(Base):
    """Organization-specific rule disablement — stores rule_id string (not FK)."""

    __tablename__ = "rule_disables"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # rule_id is the string identifier (e.g. "aws-s3-public-access"), not the UUID PK
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    disabled_by: Mapped[str] = mapped_column(String(255), nullable=False)
    disabled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("rule_id", "organization_id", name="uq_rule_disable_org"),
    )


class FrameworkModel(Base):
    """Compliance framework model."""

    __tablename__ = "frameworks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    controls: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class EvaluationCacheModel(Base):
    """Cache for rule evaluation results."""

    __tablename__ = "evaluation_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


DEFAULT_FRAMEWORKS = {
    "CIS-AWS": {
        "name": "CIS-AWS",
        "display_name": "CIS AWS Foundations Benchmark",
        "description": "Center for Internet Security AWS Foundations Benchmark",
        "version": "3.0.0",
        "controls": [
            {"id": "1.1", "name": "Identity and Access Management", "description": "IAM controls"},
            {"id": "1.2", "name": "IAM Root User", "description": "Root account controls"},
            {"id": "2.1", "name": "Storage", "description": "S3 and storage controls"},
            {"id": "3.1", "name": "Logging", "description": "CloudTrail and logging controls"},
            {"id": "4.1", "name": "Monitoring", "description": "CloudWatch monitoring controls"},
            {"id": "5.1", "name": "Networking", "description": "VPC and network controls"},
        ],
    },
    "SOC2": {
        "name": "SOC2",
        "display_name": "SOC 2 Type II",
        "description": "Service Organization Control 2",
        "version": "2017",
        "controls": [
            {"id": "CC6.1", "name": "Logical Access Controls", "description": "Access control"},
            {"id": "CC6.6", "name": "Network Security", "description": "Network controls"},
            {"id": "CC7.1", "name": "System Operations", "description": "Operations controls"},
            {"id": "CC7.2", "name": "Monitoring", "description": "Monitoring controls"},
        ],
    },
    "PCI-DSS": {
        "name": "PCI-DSS",
        "display_name": "PCI Data Security Standard",
        "description": "Payment Card Industry Data Security Standard",
        "version": "4.0",
        "controls": [
            {"id": "1.3", "name": "Firewall Configuration", "description": "Network controls"},
            {"id": "3.6", "name": "Key Management", "description": "Encryption key controls"},
            {"id": "10.1", "name": "Audit Logging", "description": "Logging controls"},
        ],
    },
    "HIPAA": {
        "name": "HIPAA",
        "display_name": "Health Insurance Portability and Accountability Act",
        "description": "US healthcare data protection regulation",
        "version": "1996",
        "controls": [
            {"id": "164.312", "name": "Access Control", "description": "Technical safeguards"},
        ],
    },
    "ISO27001": {
        "name": "ISO27001",
        "display_name": "ISO/IEC 27001:2022",
        "description": "Information Security Management",
        "version": "2022",
        "controls": [
            {"id": "A.5.1", "name": "Information Security Policies", "description": "Policy controls"},
            {"id": "A.8.1", "name": "Asset Management", "description": "Asset controls"},
        ],
    },
    "NIST-800-53": {
        "name": "NIST-800-53",
        "display_name": "NIST SP 800-53",
        "description": "Security and Privacy Controls for Federal Information Systems",
        "version": "Rev 5",
        "controls": [
            {"id": "AC-1", "name": "Access Control Policy", "description": "Access controls"},
            {"id": "AU-1", "name": "Audit Policy", "description": "Audit controls"},
        ],
    },
    "GDPR": {
        "name": "GDPR",
        "display_name": "General Data Protection Regulation",
        "description": "EU data protection and privacy regulation",
        "version": "2018",
        "controls": [
            {"id": "Art.25", "name": "Data Protection by Design", "description": "Privacy controls"},
            {"id": "Art.32", "name": "Security of Processing", "description": "Security controls"},
        ],
    },
}


class RuleVersionHistoryModel(Base):
    """Stores previous versions of rules for rollback support — spec §3.4."""

    __tablename__ = "rule_version_history"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    rego_code: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_mapping: Mapped[list] = mapped_column(JSON, default=list)
    changed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_rule_history_rule_id", "rule_id"),
        Index("idx_rule_history_org", "organization_id"),
    )
