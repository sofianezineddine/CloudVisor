from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class Framework(BaseModel):
    id: str
    name: str
    version: str
    description: Optional[str] = None
    compliance_score: int = 0
    passed_controls: int = 0
    failed_controls: int = 0


MOCK_FRAMEWORKS = [
    Framework(
        id="fw-s1",
        name="KSPM Basic",
        version="1.0",
        compliance_score=72,
        passed_controls=18,
        failed_controls=6,
    ),
    Framework(
        id="fw-s2",
        name="KSPM Advanced",
        version="1.1",
        compliance_score=85,
        passed_controls=25,
        failed_controls=3,
    ),
]


@router.get("/api/v1/kspm/frameworks", response_model=List[Framework])
def get_frameworks():
    return MOCK_FRAMEWORKS


@router.get("/api/v1/kspm/frameworks/{fw_id}", response_model=Framework)
def get_framework(fw_id: str):
    for f in MOCK_FRAMEWORKS:
        if f.id == fw_id:
            return f
    return None


@router.get("/api/v1/kspm/stats")
def get_stats():
    return {
        "total_frameworks": len(MOCK_FRAMEWORKS),
        "compliant": 1,
        "non_compliant": 1,
    }


@router.post("/api/v1/kspm/scan")
def start_scan():
    return {"scan_id": "kspm-scan-001"}
