from fastapi import APIRouter
from .assets import router as assets_router
from .findings import router as findings_router
from .accounts import router as accounts_router
from .compliance import router as compliance_router
from .rules import router as rules_router
from .graph import router as graph_router
from .notifications import router as notifications_router
from .incidents import router as incidents_router
from .cspm import router as cspm_router
from .copilot import router as copilot_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(assets_router)
v1_router.include_router(findings_router)
v1_router.include_router(accounts_router)
v1_router.include_router(compliance_router)
v1_router.include_router(rules_router)
v1_router.include_router(graph_router)
v1_router.include_router(notifications_router)
v1_router.include_router(incidents_router)
v1_router.include_router(cspm_router)
v1_router.include_router(copilot_router)

__all__ = ["v1_router"]
