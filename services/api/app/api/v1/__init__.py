"""
CloudVisor Public API — v1 router aggregator.

Registered route prefixes:
  /v1/assets          assets.py
  /v1/findings        findings.py
  /v1/accounts        accounts.py
  /v1/compliance      compliance.py
  /v1/rules           rules.py
  /v1/risk            graph.py  (attack-paths, top-assets)
  /v1/notifications   notifications.py
  /v1/incidents       incidents.py
  /v1/cspm            cspm.py
  /v1/copilot         copilot.py
  /v1/keep            keep.py   (catch-all proxy to Keep AIOps)
  /v1/reports         reports.py
  /v1/webhooks        webhooks.py
  /v1/scan            scans.py     (POST /v1/scan)
  /v1/scans           scans.py     (GET /v1/scans/{id})
  /graphql            graphql.py   (POST /graphql — GraphQL API)
"""

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
from .reports import router as reports_router
from .webhooks import router as webhooks_router
from .scans import router as scans_router
from .graphql import router as graphql_router
from .suppressions import router as suppressions_router
from .posture import router as posture_router
from .activity import router as activity_router
from .modules import router as modules_router
from .keep import router as keep_router


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
v1_router.include_router(reports_router)
v1_router.include_router(webhooks_router)
v1_router.include_router(scans_router)
v1_router.include_router(suppressions_router)
v1_router.include_router(posture_router)
v1_router.include_router(activity_router)
v1_router.include_router(modules_router)
v1_router.include_router(keep_router)


# GraphQL is mounted at /graphql (no /v1 prefix — standard convention)
graphql_standalone_router = APIRouter()
graphql_standalone_router.include_router(graphql_router)

__all__ = ["v1_router", "graphql_standalone_router"]
