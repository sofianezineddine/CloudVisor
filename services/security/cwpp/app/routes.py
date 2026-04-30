from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class Workload(BaseModel):
    id: str
    name: str
    type: str  # VM, Container, Serverless
    provider: str
    risk_score: int
    status: str  # secure, warning, critical
    findings_count: int


class WorkloadList(BaseModel):
    items: List[Workload]


MOCK_WORKLOADS = [
    Workload(
        id="wl-001",
        name="web-prod-01",
        type="VM",
        provider="aws",
        risk_score=85,
        status="critical",
        findings_count=3,
    ),
    Workload(
        id="wl-002",
        name="api-service",
        type="Container",
        provider="azure",
        risk_score=45,
        status="warning",
        findings_count=1,
    ),
]


@router.get("/api/v1/cwpp/workloads", response_model=WorkloadList)
def get_workloads():
    return WorkloadList(items=MOCK_WORKLOADS)


@router.get("/api/v1/cwpp/workloads/{wl_id}", response_model=Workload)
def get_workload(wl_id: str):
    for wl in MOCK_WORKLOADS:
        if wl.id == wl_id:
            return wl
    return None


@router.get("/api/v1/cwpp/stats")
def get_stats():
    return {
        "total_workloads": len(MOCK_WORKLOADS),
        "secure_workloads": len([w for w in MOCK_WORKLOADS if w.status == "secure"]),
        "warning_workloads": len([w for w in MOCK_WORKLOADS if w.status == "warning"]),
        "critical_workloads": len(
            [w for w in MOCK_WORKLOADS if w.status == "critical"]
        ),
    }


@router.post("/api/v1/cwpp/scan")
def start_scan():
    return {"scan_id": "cwpp-scan-0001"}


# Additional Findings/Controls surface (in-memory) to progress CSPM-like API surface
from pydantic import BaseModel
from typing import List, Optional
from fastapi import HTTPException


class Finding(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    resource_id: str


class FindingList(BaseModel):
    items: List[Finding]


MOCK_FINDINGS = [
    Finding(
        id="fwd-cwpp-001",
        title="Container vulnerability",
        severity="high",
        status="open",
        resource_id="container-01",
    )
]


@router.get("/api/v1/cwpp/findings", response_model=FindingList)
def cwpp_findings_list():
    return FindingList(items=MOCK_FINDINGS)


@router.get("/api/v1/cwpp/findings/{finding_id}", response_model=Finding)
def cwpp_findings_detail(finding_id: str):
    for f in MOCK_FINDINGS:
        if f.id == finding_id:
            return f
    raise HTTPException(status_code=404, detail="Finding not found")


@router.post("/api/v1/cwpp/findings/{finding_id}/remediate")
def cwpp_findings_remediate(finding_id: str):
    for f in MOCK_FINDINGS:
        if f.id == finding_id:
            f.status = "remediated"
            return f
    raise HTTPException(status_code=404, detail="Finding not found")


@router.post("/api/v1/cwpp/findings/{finding_id}/dismiss")
def cwpp_findings_dismiss(finding_id: str):
    for f in MOCK_FINDINGS:
        if f.id == finding_id:
            f.status = "dismissed"
            return f
    raise HTTPException(status_code=404, detail="Finding not found")


class Control(BaseModel):
    id: str
    framework_id: str
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    remediation_steps: Optional[str] = None
    severity: Optional[str] = None


MOCK_CONTROLS = [
    Control(
        id="ctrl-cwpp-001",
        framework_id="fw-001",
        name="Container Scanning",
        description="Scan containers",
        severity="critical",
    )
]


@router.get("/api/v1/cwpp/controls", response_model=List[Control])
def cwpp_controls_list():
    return MOCK_CONTROLS


@router.get("/api/v1/cwpp/controls/{control_id}", response_model=Control)
def cwpp_control_detail(control_id: str):
    for c in MOCK_CONTROLS:
        if c.id == control_id:
            return c
    raise HTTPException(status_code=404, detail="Control not found")


@router.post("/api/v1/cwpp/controls/{control_id}/remediate")
def cwpp_control_remediate(control_id: str):
    for c in MOCK_CONTROLS:
        if c.id == control_id:
            c.status = "remediated"
            return c
    raise HTTPException(status_code=404, detail="Control not found")
