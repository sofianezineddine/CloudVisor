"""Pydantic schemas for CSPM service."""
from pydantic import BaseModel
from typing import List, Optional


class FindingSchema(BaseModel):
    id: str
    organization_id: str
    fingerprint: str
    rule_id: str
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    resource_id: str
    resource_name: Optional[str] = None
    resource_type: Optional[str] = None
    provider: Optional[str] = None
    account_id: Optional[str] = None
    region: Optional[str] = None
    remediation: Optional[str] = None

    class Config:
        from_attributes = True


class FindingListSchema(BaseModel):
    items: List[FindingSchema]
    total: int = 0
