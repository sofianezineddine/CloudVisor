"""
POST /graphql  — GraphQL API endpoint

Spec §3.6: GraphQL API covering assets (with relationship traversal), findings,
rules, and compliance. Proxied to the Graph service which runs the Strawberry/
Ariadne GraphQL server.

Primary use case: complex nested queries like:
  query {
    assets(filter: { is_public: true, risk_score_gte: 70 }) {
      id name resourceType
      findings(status: OPEN, severity: [CRITICAL, HIGH]) {
        title severity remediationSteps
      }
      relatedAssets(relationship: HAS_ACCESS_TO) {
        id name resourceType
      }
    }
  }
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.proxy import get_graph_proxy
from app.schemas.envelope import ok

router = APIRouter(tags=["graphql"])


@router.post("/graphql")
async def graphql_endpoint(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> Any:
    """
    Execute a GraphQL query against the CloudVisor asset graph.

    The request body must be a JSON object with:
      - query: string (required) — the GraphQL query document
      - variables: object (optional) — variable values
      - operationName: string (optional) — operation to execute

    All queries are automatically scoped to the authenticated organization.
    The `org_id` variable is injected server-side — clients cannot override it.
    """
    t0 = time.monotonic()

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON")

    if not isinstance(body, dict) or "query" not in body:
        raise HTTPException(
            status_code=400,
            detail="GraphQL request must include a 'query' field",
        )

    # Inject org_id into variables for tenant isolation
    variables = body.get("variables") or {}
    variables["org_id"] = user.organization_id
    body["variables"] = variables

    graph = get_graph_proxy()
    try:
        result = await graph.post(
            "/graphql",
            json=body,
            headers=user.auth_headers,
        )
        # GraphQL responses are returned as-is (they have their own error format)
        took = int((time.monotonic() - t0) * 1000)
        # Add took_ms as an extension (standard GraphQL extension pattern)
        if isinstance(result, dict):
            extensions = result.get("extensions", {})
            extensions["took_ms"] = took
            result["extensions"] = extensions
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Graph service unavailable: {e}")


@router.get("/graphql")
async def graphql_playground(
    user: AuthenticatedUser = Depends(get_current_user),
) -> Any:
    """
    GraphQL Playground — interactive query editor.
    Returns a simple HTML page that loads the GraphQL Playground UI.
    """
    from fastapi.responses import HTMLResponse
    html = """<!DOCTYPE html>
<html>
<head>
  <title>CloudVisor GraphQL Playground</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="user-scalable=no, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, minimal-ui">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
  <link rel="shortcut icon" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/favicon.png" />
  <script src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js"></script>
</head>
<body>
  <div id="root"></div>
  <script>
    window.addEventListener('load', function (event) {
      GraphQLPlayground.init(document.getElementById('root'), {
        endpoint: '/graphql',
        settings: { 'editor.theme': 'light' }
      })
    })
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)
