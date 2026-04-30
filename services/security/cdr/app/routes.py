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


MOCK_FRAMEWORKS = [
    Framework(id="fw-cdr-1", name="CDR Core", version="1.0", compliance_score=76),
    Framework(id="fw-cdr-2", name="CDR Pro", version="2.0", compliance_score=89),
]


@router.get("/api/v1/cdr/frameworks", response_model=List[Framework])
def get_frameworks():
    return MOCK_FRAMEWORKS


@router.get("/api/v1/cdr/stats")
def get_stats():
    return {
        "total_frameworks": len(MOCK_FRAMEWORKS),
        "compliant": 1,
        "non_compliant": 1,
    }
