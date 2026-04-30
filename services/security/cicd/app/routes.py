from fastapi import APIRouter, HTTPException
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
    Framework(
        id="fw-ci-1", name="CICD Security Core", version="1.0", compliance_score=72
    ),
    Framework(
        id="fw-ci-2", name="CICD Security Pro", version="1.2", compliance_score=84
    ),
]


@router.get("/api/v1/cicd/frameworks", response_model=List[Framework])
def get_frameworks():
    return MOCK_FRAMEWORKS


@router.get("/api/v1/cicd/stats")
def get_stats():
    return {
        "total_frameworks": len(MOCK_FRAMEWORKS),
        "compliant": 1,
        "non_compliant": 1,
    }


@router.post("/api/v1/cicd/scan")
def start_scan():
    return {"scan_id": "cicd-scan-001"}


class CicdFinding(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    pipeline_id: str
    remediation: Optional[str] = None


class CicdFindingList(BaseModel):
    items: List[CicdFinding]


MOCK_CICD_FINDINGS = [
    CicdFinding(
        id="fci-001",
        title="CI/CD pipeline issue",
        severity="high",
        status="open",
        pipeline_id="pipe-1",
    )
]


@router.get("/api/v1/cicd/findings", response_model=CicdFindingList)
def cicd_findings_list():
    return CicdFindingList(items=MOCK_CICD_FINDINGS)


@router.get("/api/v1/cicd/findings/{finding_id}", response_model=CicdFinding)
def cicd_findings_detail(finding_id: str):
    for f in MOCK_CICD_FINDINGS:
        if f.id == finding_id:
            return f
    raise HTTPException(status_code=404, detail="Finding not found")


@router.post("/api/v1/cicd/findings/{finding_id}/remediate")
def cicd_findings_remediate(finding_id: str):
    return {"id": finding_id, "status": "remediated"}


@router.post("/api/v1/cicd/findings/{finding_id}/dismiss")
def cicd_findings_dismiss(finding_id: str):
    return {"id": finding_id, "status": "dismissed"}
