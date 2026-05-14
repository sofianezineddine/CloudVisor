"""Attack Path Engine database models."""

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
)

from ..db_helper import Base


class AttackPathModel(Base):
    """Stores discovered attack paths from entry points to sensitive resources."""

    __tablename__ = "cspm_attack_paths"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    entry_resource_id = Column(String, nullable=False)
    target_resource_id = Column(String, nullable=False)
    path_hops = Column(Integer, nullable=False)
    path_nodes = Column(JSON, default=list)  # ordered list of resource IDs
    path_edges = Column(JSON, default=list)  # list of {from, to, relationship_type}
    severity = Column(String, nullable=False)
    mitre_technique_id = Column(String, nullable=True)
    mitre_technique_name = Column(String, nullable=True)
    is_lateral_movement = Column(Boolean, default=False)
    blast_radius_count = Column(Integer, default=0)
    discovered_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_attack_path_org_severity", "organization_id", "severity"),
    )


class ToxicCombinationModel(Base):
    """Stores detected toxic combinations of misconfigurations."""

    __tablename__ = "cspm_toxic_combinations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    pattern_id = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    component_finding_ids = Column(JSON, default=list)  # list of contributing finding IDs
    component_details = Column(JSON, default=list)  # list of {rule_id, severity, description}
    elevated_severity = Column(String, nullable=False)
    description = Column(String, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_toxic_combo_org", "organization_id"),
    )
