from pydantic import BaseModel
from typing import List, Optional
from .models_db import CWPPWorkload


class CWPPWorkloadSchema(BaseModel):
    id: str
    name: str
    type: str
    provider: str
    risk_score: int
    status: str
    findings_count: int

    class Config:
        orm_mode = True


class CWPPWorkloadListSchema(BaseModel):
    items: List[CWPPWorkloadSchema]
