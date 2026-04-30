from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()


class Framework(BaseModel):
    id: str
    name: str
    version: str
    compliance_score: int = 0


MOCK_FRAMEWORKS = [
    Framework(id="fw-ai-1", name="AIOps Core", version="1.0", compliance_score=88)
]


@router.get("/api/v1/aiops/frameworks", response_model=List[Framework])
def get_frameworks():
    return MOCK_FRAMEWORKS


@router.get("/api/v1/aiops/stats")
def get_stats():
    return {"total_frameworks": len(MOCK_FRAMEWORKS), "compliant": 1}


@router.post("/api/v1/aiops/scan")
def start_scan():
    return {"scan_id": "aiops-scan-001"}
