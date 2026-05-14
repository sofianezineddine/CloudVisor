"""IaC Scanner database models."""

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


class IaCScanModel(Base):
    """Stores IaC scan execution records."""

    __tablename__ = "cspm_iac_scans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    source_type = Column(String, nullable=False)  # webhook, api, cli
    git_provider = Column(String, nullable=True)  # github, gitlab, bitbucket
    repository = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    commit_sha = Column(String, nullable=True)
    pull_request_id = Column(String, nullable=True)
    template_type = Column(String, nullable=False)  # terraform, cloudformation, kubernetes, helm
    enforcement_mode = Column(String, default="advisory")  # advisory, blocking
    status = Column(String, default="running")  # running, completed, failed
    total_files = Column(Integer, default=0)
    total_findings = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    passed = Column(Boolean, nullable=True)  # null=running, true=passed, false=failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_iac_scan_org", "organization_id"),
    )


class IaCFindingModel(Base):
    """Stores individual findings from IaC scans."""

    __tablename__ = "cspm_iac_findings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    scan_id = Column(String, nullable=False, index=True)
    file_path = Column(String, nullable=False)
    line_number = Column(Integer, nullable=True)
    resource_identifier = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    rule_id = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    remediation = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False)
    secret_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IaCWebhookConfigModel(Base):
    """Stores webhook configurations for Git provider integrations."""

    __tablename__ = "cspm_iac_webhook_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    git_provider = Column(String, nullable=False)
    repository = Column(String, nullable=False)
    webhook_secret = Column(String, nullable=False)  # for signature verification
    enforcement_mode = Column(String, default="advisory")
    scan_paths = Column(JSON, default=list)  # paths to scan
    excluded_paths = Column(JSON, default=list)  # paths to exclude
    severity_threshold = Column(String, default="HIGH")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
