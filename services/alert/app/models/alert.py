"""Database models for Alert service."""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, JSON, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class FindingModel(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    resource_name: Mapped[str] = mapped_column(String(255), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    remediation: Mapped[str] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=True)
    account_id: Mapped[str] = mapped_column(String(255), nullable=True)
    region: Mapped[str] = mapped_column(String(50), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=True)
    tags: Mapped[list] = mapped_column(ARRAY(String), default=list)
    compliance_mapping: Mapped[list] = mapped_column(ARRAY(JSON), default=list)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    assignee_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    regression_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class FindingHistoryModel(Base):
    __tablename__ = "finding_history"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    finding_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("findings.id"), nullable=False, index=True
    )
    old_status: Mapped[str] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(255), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class IncidentModel(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    finding_ids: Mapped[list] = mapped_column(ARRAY(UUID), default=list)
    assignee_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class SuppressionRuleModel(Base):
    __tablename__ = "suppression_rules"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=True)
    resource_tag_key: Mapped[str] = mapped_column(String(100), nullable=True)
    resource_tag_value: Mapped[str] = mapped_column(String(255), nullable=True)
    account_id: Mapped[str] = mapped_column(String(255), nullable=True)
    region: Mapped[str] = mapped_column(String(50), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class NotificationChannelModel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    severity_filter: Mapped[list] = mapped_column(ARRAY(String), default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class NotificationLogModel(Base):
    __tablename__ = "notification_log"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    finding_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("findings.id"), nullable=False
    )
    channel_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("notification_channels.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
