from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class Principal(BaseModel):
    id: str
    name: str
    type: str  # User, Role, Service
    provider: str
    risk_score: int
    standing: str  # compliant, excessive, dormant
    entitlements_count: int


class PrincipalList(BaseModel):
    items: List[Principal]


MOCK_PRINCIPALS = [
    Principal(
        id="pr-001",
        name="app-role-prod",
        type="Role",
        provider="aws",
        risk_score=90,
        standing="excessive",
        entitlements_count=12,
    ),
    Principal(
        id="pr-002",
        name="svc-account-backup",
        type="Service",
        provider="azure",
        risk_score=30,
        standing="compliant",
        entitlements_count=2,
    ),
]


@router.get("/api/v1/ciem/principals", response_model=PrincipalList)
def get_principals():
    return PrincipalList(items=MOCK_PRINCIPALS)


@router.get("/api/v1/ciem/principals/{pid}", response_model=Principal)
def get_principal(pid: str):
    for p in MOCK_PRINCIPALS:
        if p.id == pid:
            return p
    return None


@router.get("/api/v1/ciem/stats")
def get_stats():
    return {
        "total_principals": len(MOCK_PRINCIPALS),
        "compliant_principals": len(
            [p for p in MOCK_PRINCIPALS if p.standing == "compliant"]
        ),
        "excessive_principals": len(
            [p for p in MOCK_PRINCIPALS if p.standing == "excessive"]
        ),
        "dormant_principals": len(
            [p for p in MOCK_PRINCIPALS if p.standing == "dormant"]
        ),
    }


@router.post("/api/v1/ciem/scan")
def start_scan():
    return {"scan_id": "ciem-scan-0001"}
