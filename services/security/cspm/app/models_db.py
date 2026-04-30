"""CSPM database models."""
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .db_helper import Base


class CSPMScanModel(Base):
    __tablename__ = "cspm_scans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=True)
    scan_type = Column(String, default="scheduled")  # scheduled, on_demand, event_driven
    status = Column(String, default="running")  # running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    resources_scanned = Column(Integer, default=0)
    findings_created = Column(Integer, default=0)
    findings_resolved = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)


class CSPMFindingModel(Base):
    __tablename__ = "cspm_findings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    fingerprint = Column(String, unique=True, nullable=False, index=True)
    rule_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String, nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    status = Column(String, default="open", index=True)  # open, resolved, suppressed, accepted_risk
    resource_id = Column(String, nullable=False, index=True)
    resource_name = Column(String, nullable=True)
    resource_type = Column(String, nullable=True)
    provider = Column(String, nullable=True, index=True)
    account_id = Column(String, nullable=True, index=True)
    region = Column(String, nullable=True)
    remediation = Column(Text, nullable=True)
    compliance_mapping = Column(JSON, default=list)
    regression_count = Column(Integer, default=0)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cspm_findings_org_severity", "organization_id", "severity"),
        Index("ix_cspm_findings_org_status", "organization_id", "status"),
    )


class CSPMResourcePostureModel(Base):
    __tablename__ = "cspm_resource_posture"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    resource_id = Column(String, nullable=False, index=True)
    resource_name = Column(String, nullable=True)
    resource_type = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    account_id = Column(String, nullable=True)
    region = Column(String, nullable=True)
    environment = Column(String, nullable=True)
    risk_score = Column(Integer, default=0)
    is_internet_exposed = Column(Boolean, default=False)
    contains_sensitive_data = Column(Boolean, default=False)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    last_scanned_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cspm_posture_org_resource", "organization_id", "resource_id", unique=True),
    )


class CSPMComplianceResultModel(Base):
    __tablename__ = "cspm_compliance_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    framework = Column(String, nullable=False, index=True)
    control_id = Column(String, nullable=False)
    status = Column(String, default="pass")  # pass, fail, not_applicable
    finding_count = Column(Integer, default=0)
    last_evaluated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cspm_compliance_org_framework", "organization_id", "framework"),
    )


class CSPMPostureSnapshotModel(Base):
    """Daily posture score snapshots for trend tracking."""
    __tablename__ = "cspm_posture_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False)
    posture_score = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cspm_snapshots_org_date", "organization_id", "snapshot_date", unique=True),
    )


class CSPMReportModel(Base):
    """Generated CSPM reports (PDF/CSV)."""
    __tablename__ = "cspm_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    report_type = Column(String, nullable=False)   # compliance, posture, findings_export
    framework = Column(String, nullable=True)       # CIS-AWS, SOC2, etc. (for compliance reports)
    format = Column(String, default="csv")          # csv, pdf
    status = Column(String, default="pending")      # pending, generating, ready, failed
    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)
    account_ids = Column(JSON, default=list)        # list of account IDs to include
    file_path = Column(String, nullable=True)       # internal storage path
    file_size_bytes = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    requested_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_cspm_reports_org", "organization_id"),
    )
