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
    Framework(id="fw-d1", name="DSPM Core", version="1.0", compliance_score=70),
    Framework(id="fw-d2", name="DSPM Pro", version="1.2", compliance_score=82),
]


@router.get("/api/v1/dspm/frameworks", response_model=List[Framework])
def get_frameworks():
    return MOCK_FRAMEWORKS


@router.get("/api/v1/dspm/stats")
def get_stats():
    return {
        "total_frameworks": len(MOCK_FRAMEWORKS),
        "compliant": 1,
        "non_compliant": 1,
    }
