"""Multi-source context retrieval service."""

import logging
from typing import Any
import httpx
from elasticsearch import AsyncElasticsearch

from ..core.config import CopilotSettings

logger = logging.getLogger(__name__)


class ContextRetriever:
    """Retrieves context from multiple data sources based on query intent."""

    def __init__(self, settings: CopilotSettings, organization_id: str, session_factory=None):
        """
        Initialize context retriever.

        Args:
            settings: Copilot service settings
            organization_id: Tenant organization ID for RLS
            session_factory: Optional database session factory for PostgreSQL fallback
        """
        self.settings = settings
        self.organization_id = organization_id
        self.timeout = settings.retrieval_timeout_seconds
        self.session_factory = session_factory

        # Initialize Elasticsearch client
        self.es_client = AsyncElasticsearch([settings.elasticsearch_url])

    async def retrieve(
        self,
        intent: str,
        query: str,
        context_finding_id: str | None = None,
        context_asset_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch comprehensive context from all available sources.
        No intent-based filtering - give the LLM full situational awareness.
        """
        import asyncio

        logger.info(f"Fetching comprehensive context for autonomous LLM reasoning")

        context: dict[str, Any] = {
            "sources_used": [],
        }

        async def _safe(name: str, coro):
            try:
                result = await coro
                if result:
                    context[name] = result
                    context["sources_used"].append(name)
            except Exception as e:
                logger.warning(f"Failed to fetch {name}: {e}")

        async def _fetch_assets():
            try:
                assets = await self._fetch_assets_from_graph(query)
                if assets:
                    context["assets"] = assets
                    context["sources_used"].append("assets")
                    return
            except Exception as e:
                logger.warning(f"Graph asset fetch failed: {e}")
            try:
                assets = await self._fetch_assets_from_db()
                if assets:
                    context["assets"] = assets
                    context["sources_used"].append("assets")
            except Exception as e:
                logger.warning(f"DB asset fallback failed: {e}")

        async def _fetch_findings():
            try:
                findings = await self._fetch_findings_from_es(query)
                if not findings:
                    findings = await self._fetch_findings_direct()
                if findings:
                    context["findings"] = findings
                    context["sources_used"].append("findings")
            except Exception as e:
                logger.warning(f"Findings fetch failed: {e}")

        # Fetch all core data sources concurrently
        tasks = [
            _safe("cloud_accounts", self._fetch_cloud_accounts()),
            _safe("posture_snapshots", self._fetch_posture_snapshots()),
            _fetch_findings(),
            _fetch_assets(),
            _safe("resource_posture", self._fetch_resource_posture()),
            _safe("compliance_results", self._fetch_compliance_results()),
            _safe("recent_scans", self._fetch_recent_scans()),
            _safe("users", self._fetch_users()),
        ]

        # Run all tasks concurrently
        await asyncio.gather(*tasks)

        # Specific finding/asset if provided from UI context
        if context_finding_id:
            try:
                finding = await self._fetch_finding_by_id(context_finding_id)
                if finding:
                    context["finding"] = finding
                    context["sources_used"].append("finding_detail")
                    history = await self._fetch_finding_history(context_finding_id)
                    if history:
                        context["finding_history"] = history
            except Exception as e:
                logger.warning(f"Failed to fetch finding {context_finding_id}: {e}")

        if context_asset_id:
            try:
                asset = await self._fetch_asset_by_id(context_asset_id)
                if asset:
                    context["preloaded_asset"] = asset
                    context["sources_used"].append("asset_detail")
            except Exception as e:
                logger.warning(f"Failed to fetch asset {context_asset_id}: {e}")

        logger.info(f"Comprehensive context retrieved from: {context['sources_used']}")
        return context

    async def _retrieve_posture_context(self, query: str) -> dict[str, Any]:
        """Retrieve context for posture & risk queries — all sources fetched concurrently."""
        import asyncio

        context: dict[str, Any] = {}

        async def _safe(coro, key: str, source_tag: str):
            try:
                result = await coro
                if result:
                    context[key] = result
                    context.setdefault("sources_used", []).append(source_tag)
            except Exception as e:
                logger.warning(f"Failed to fetch {source_tag}: {e}")

        async def _fetch_assets_with_fallback():
            try:
                assets = await self._fetch_assets_from_graph(query)
                if assets:
                    context["assets"] = assets
                    context.setdefault("sources_used", []).append("asset_graph")
                    return
            except Exception as e:
                logger.warning(f"Failed to fetch assets from graph: {e}")
            try:
                assets = await self._fetch_assets_from_db()
                if assets:
                    context["assets"] = assets
                    context.setdefault("sources_used", []).append("asset_graph_db")
            except Exception as db_e:
                logger.warning(f"DB asset fallback also failed: {db_e}")

        async def _fetch_findings_with_fallback():
            try:
                findings = await self._fetch_findings_from_es(query)
                if not findings:
                    findings = await self._fetch_findings_direct()
                if findings:
                    context["findings"] = findings
                    context.setdefault("sources_used", []).append("findings")
            except Exception as e:
                logger.warning(f"Failed to fetch findings: {e}")

        await asyncio.gather(
            _fetch_assets_with_fallback(),
            _safe(self._fetch_resource_posture(), "resource_posture", "resource_posture"),
            _fetch_findings_with_fallback(),
            _safe(self._fetch_compliance_results(), "compliance_results", "compliance"),
            _safe(self._fetch_recent_scans(), "recent_scans", "scans"),
            _safe(self._fetch_incidents(), "incidents", "incidents"),
        )

        return context

    async def _retrieve_finding_context(
        self, query: str, finding_id: str | None
    ) -> dict[str, Any]:
        """Retrieve context for finding explanation queries."""
        context = {}

        if finding_id:
            try:
                finding = await self._fetch_finding_by_id(finding_id)
                if finding:
                    context["finding"] = finding
                    context.setdefault("sources_used", []).append("findings")
                    # Fetch history for this finding
                    history = await self._fetch_finding_history(finding_id)
                    if history:
                        context["finding_history"] = history
                    # Fetch related asset
                    asset_id = finding.get("asset_id") or finding.get("resource_id")
                    if asset_id:
                        asset = await self._fetch_asset_by_id(asset_id)
                        if asset:
                            context["asset"] = asset
                            context.setdefault("sources_used", []).append("asset_graph")
            except Exception as e:
                logger.warning(f"Failed to fetch finding {finding_id}: {e}")
        else:
            try:
                findings = await self._fetch_findings_from_es(query)
                if not findings:
                    findings = await self._fetch_findings_direct()
                if findings:
                    context["findings"] = findings
                    context.setdefault("sources_used", []).append("findings")
            except Exception as e:
                logger.warning(f"Failed to search findings: {e}")

        # Suppression rules (relevant for finding context)
        try:
            suppressions = await self._fetch_suppression_rules()
            if suppressions:
                context["suppression_rules"] = suppressions
                context.setdefault("sources_used", []).append("suppression_rules")
        except Exception as e:
            logger.warning(f"Failed to fetch suppression rules: {e}")

        return context

    async def _retrieve_compliance_context(self, query: str) -> dict[str, Any]:
        """Retrieve context for compliance queries."""
        context = {}

        try:
            compliance_data = await self._fetch_compliance_posture(query)
            if compliance_data:
                context["compliance"] = compliance_data
                context.setdefault("sources_used", []).append("compliance_posture")
        except Exception as e:
            logger.warning(f"Failed to fetch compliance posture: {e}")

        try:
            results = await self._fetch_compliance_results()
            if results:
                context["compliance_results"] = results
                context.setdefault("sources_used", []).append("compliance_results")
        except Exception as e:
            logger.warning(f"Failed to fetch compliance results: {e}")

        # Frameworks
        try:
            frameworks = await self._fetch_frameworks()
            if frameworks:
                context["frameworks"] = frameworks
                context.setdefault("sources_used", []).append("frameworks")
        except Exception as e:
            logger.warning(f"Failed to fetch frameworks: {e}")

        # Rules
        try:
            rules = await self._fetch_rules()
            if rules:
                context["rules"] = rules
                context.setdefault("sources_used", []).append("rules")
        except Exception as e:
            logger.warning(f"Failed to fetch rules: {e}")

        try:
            findings = await self._fetch_findings_from_es(query)
            if not findings:
                findings = await self._fetch_findings_direct()
            if findings:
                context["findings"] = findings
                context.setdefault("sources_used", []).append("findings")
        except Exception as e:
            logger.warning(f"Failed to fetch findings: {e}")

        return context

    async def _retrieve_remediation_context(
        self, query: str, finding_id: str | None
    ) -> dict[str, Any]:
        """Retrieve context for remediation code generation (Domain 4)."""
        # Start with finding context (finding details + asset + suppression rules)
        context = await self._retrieve_finding_context(query, finding_id)

        # Also fetch the security rules so Q knows the exact rule being violated
        try:
            rules = await self._fetch_rules()
            if rules:
                context["rules"] = rules
                context.setdefault("sources_used", []).append("rules")
        except Exception as e:
            logger.warning(f"Failed to fetch rules for remediation: {e}")

        # Resource posture gives us ARNs, regions, account IDs needed for exact code
        try:
            resource_posture = await self._fetch_resource_posture()
            if resource_posture:
                context["resource_posture"] = resource_posture
                context.setdefault("sources_used", []).append("resource_posture")
        except Exception as e:
            logger.warning(f"Failed to fetch resource posture for remediation: {e}")

        return context

    async def _retrieve_threat_context(self, query: str) -> dict[str, Any]:
        """Retrieve context for threat investigation (Domain 5)."""
        context = {}

        # Try CDR service first, fall back to audit_log
        try:
            cdr_events = await self._fetch_cdr_events(query)
            if cdr_events:
                context["cdr_events"] = cdr_events
                context.setdefault("sources_used", []).append("cdr")
        except Exception as e:
            logger.warning(f"CDR service unavailable ({e}), falling back to audit_log")
            try:
                # Extract identity hint from query for targeted lookup
                changes = await self._fetch_audit_changes_for_identity(query)
                if changes:
                    context["changes"] = changes
                    context.setdefault("sources_used", []).append("audit_log")
            except Exception as ae:
                logger.warning(f"Audit log fallback also failed: {ae}")

        # Incidents
        try:
            incidents = await self._fetch_incidents()
            if incidents:
                context["incidents"] = incidents
                context.setdefault("sources_used", []).append("incidents")
        except Exception as e:
            logger.warning(f"Failed to fetch incidents: {e}")

        # Assets (for blast radius)
        try:
            assets = await self._fetch_assets_from_db()
            if assets:
                context["assets"] = assets
                context.setdefault("sources_used", []).append("asset_graph")
        except Exception as e:
            logger.warning(f"Failed to fetch assets: {e}")

        # Resource posture (internet-exposed, sensitive data)
        try:
            resource_posture = await self._fetch_resource_posture()
            if resource_posture:
                context["resource_posture"] = resource_posture
                context.setdefault("sources_used", []).append("resource_posture")
        except Exception as e:
            logger.warning(f"Failed to fetch resource posture: {e}")

        return context

    async def _retrieve_drift_context(self, query: str) -> dict[str, Any]:
        """Retrieve context for change & drift analysis (Domain 6)."""
        context = {}

        # Extract time window from query ("last 24 hours", "yesterday", etc.)
        hours = self._extract_time_window_hours(query)

        try:
            changes = await self._fetch_audit_changes_windowed(hours)
            if changes:
                context["changes"] = changes
                context["time_window_hours"] = hours
                context.setdefault("sources_used", []).append("audit_log")
        except Exception as e:
            logger.warning(f"Failed to fetch audit changes: {e}")

        try:
            scans = await self._fetch_recent_scans()
            if scans:
                context["recent_scans"] = scans
                context.setdefault("sources_used", []).append("scans")
        except Exception as e:
            logger.warning(f"Failed to fetch scans: {e}")

        # Asset snapshots for before/after comparison
        try:
            snapshots = await self._fetch_asset_snapshots_windowed(hours)
            if snapshots:
                context["asset_snapshots"] = snapshots
                context.setdefault("sources_used", []).append("asset_snapshots")
        except Exception as e:
            logger.warning(f"Failed to fetch asset snapshots: {e}")

        return context

    def _extract_time_window_hours(self, query: str) -> int:
        """Extract time window in hours from natural language query."""
        q = query.lower()
        if "last hour" in q or "past hour" in q:
            return 1
        if "last 6 hours" in q or "past 6 hours" in q:
            return 6
        if "last 12 hours" in q or "past 12 hours" in q:
            return 12
        if "last 24 hours" in q or "past 24 hours" in q or "today" in q or "this morning" in q:
            return 24
        if "yesterday" in q or "last day" in q:
            return 48
        if "last week" in q or "past week" in q or "last 7 days" in q:
            return 168
        if "last month" in q or "past month" in q or "last 30 days" in q:
            return 720
        # Default: 24 hours
        return 24

    # ─────────────────────────────────────────────────────────────
    # Internal HTTP client methods for each data source
    # ─────────────────────────────────────────────────────────────

    async def _fetch_assets_from_graph(self, query: str) -> list[dict]:
        """Fetch ALL assets from Graph service using pagination."""
        all_assets = []
        page = 1
        page_size = 100  # Graph service max page size

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                response = await client.get(
                    f"{self.settings.graph_service_url}/internal/assets",
                    params={
                        "org_id": self.organization_id,
                        "page_size": page_size,
                        "page": page,
                    },
                )
                response.raise_for_status()
                data = response.json()
                assets = data.get("assets", [])
                all_assets.extend(assets)

                total = data.get("total", 0)
                logger.info(
                    f"Fetched page {page}: {len(assets)} assets "
                    f"(total so far: {len(all_assets)}/{total})"
                )

                # Stop if we've fetched everything or got an empty page
                if len(assets) < page_size or len(all_assets) >= total:
                    break

                page += 1

        logger.info(f"Retrieved {len(all_assets)} total assets from graph service")
        return all_assets

    async def _fetch_asset_by_id(self, asset_id: str) -> dict | None:
        """Fetch a specific asset by ID."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.settings.graph_service_url}/internal/assets/{asset_id}",
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def _fetch_findings_from_es(self, query: str) -> list[dict]:
        """Fetch findings from Elasticsearch or PostgreSQL fallback."""
        # Try Elasticsearch first
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"organization_id.keyword": self.organization_id}},
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title", "description", "resource_name"],
                                }
                            },
                        ]
                    }
                },
                "size": self.settings.max_retrieval_results,
                "sort": [{"severity_score": {"order": "desc"}}, {"created_at": {"order": "desc"}}],
            }

            result = await self.es_client.search(
                index=self.settings.elasticsearch_findings_index, body=search_body
            )

            hits = result.get("hits", {}).get("hits", [])
            if hits:
                return [hit["_source"] for hit in hits]
        except Exception as e:
            logger.debug(f"Elasticsearch search failed, falling back to PostgreSQL: {e}")

        # Fallback to PostgreSQL direct query — merge both tables
        return await self._fetch_findings_direct()

    async def _fetch_finding_by_id(self, finding_id: str) -> dict | None:
        """Fetch a specific finding by ID."""
        try:
            result = await self.es_client.get(
                index=self.settings.elasticsearch_findings_index, id=finding_id
            )
            return result["_source"]
        except Exception:
            return None

    async def _fetch_compliance_posture(self, query: str) -> dict:
        """Fetch compliance posture from Policy service."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.settings.policy_service_url}/policy/compliance",
                params={"x_org_id": self.organization_id},
            )
            response.raise_for_status()
            return response.json()

    async def _fetch_cdr_events(self, query: str) -> list[dict]:
        """Fetch CDR events from CDR service."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.settings.cdr_service_url}/internal/events",
                params={
                    "org_id": self.organization_id,
                    "limit": self.settings.max_retrieval_results,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("events", [])

    async def _fetch_audit_changes(self, query: str) -> list[dict]:
        """Fetch audit log changes."""
        try:
            if not self.session_factory:
                return []
            
            async with self.session_factory() as session:
                from sqlalchemy import text
                
                sql = text("""
                    SELECT 
                        id::text,
                        organization_id::text,
                        user_id::text,
                        action,
                        resource_type,
                        resource_id,
                        changes,
                        timestamp::text,
                        ip_address
                    FROM audit_log
                    WHERE organization_id = :org_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """)
                
                result = await session.execute(
                    sql,
                    {"org_id": self.organization_id, "limit": min(50, self.settings.max_retrieval_results)}
                )
                
                changes = []
                for row in result:
                    changes.append({
                        "id": row[0],
                        "organization_id": row[1],
                        "user_id": row[2],
                        "action": row[3],
                        "resource_type": row[4] or "",
                        "resource_id": row[5] or "",
                        "changes": row[6] or {},
                        "timestamp": row[7],
                        "ip_address": row[8] or "",
                    })
                
                logger.info(f"Retrieved {len(changes)} audit log entries")
                return changes
                
        except Exception as e:
            logger.error(f"Failed to fetch audit changes: {e}")
            return []

    async def _fetch_cloud_accounts(self) -> list[dict]:
        """Fetch connected cloud accounts."""
        try:
            if not self.session_factory:
                return []
            
            async with self.session_factory() as session:
                from sqlalchemy import text
                
                sql = text("""
                    SELECT 
                        id::text,
                        organization_id::text,
                        provider,
                        account_id,
                        name,
                        status,
                        sync_status,
                        last_sync_at::text,
                        resource_count,
                        created_at::text
                    FROM connector_cloud_accounts
                    WHERE organization_id = :org_id
                    ORDER BY created_at DESC
                """)
                
                result = await session.execute(sql, {"org_id": self.organization_id})
                
                accounts = []
                for row in result:
                    accounts.append({
                        "id": row[0],
                        "organization_id": row[1],
                        "provider": row[2],
                        "account_id": row[3],
                        "account_name": row[4] or "",
                        "status": row[5],
                        "sync_status": row[6],
                        "last_sync_at": row[7],
                        "resource_count": row[8] or 0,
                        "created_at": row[9],
                    })
                
                logger.info(f"Retrieved {len(accounts)} cloud accounts")
                return accounts
                
        except Exception as e:
            logger.error(f"Failed to fetch cloud accounts: {e}")
            return []

    async def _fetch_compliance_results(self) -> list[dict]:
        """Fetch compliance scan results."""
        try:
            if not self.session_factory:
                return []
            
            async with self.session_factory() as session:
                from sqlalchemy import text
                
                sql = text("""
                    SELECT 
                        id::text,
                        organization_id::text,
                        framework,
                        control_id,
                        status,
                        finding_count,
                        last_evaluated_at::text
                    FROM cspm_compliance_results
                    WHERE organization_id = :org_id
                    ORDER BY last_evaluated_at DESC
                    LIMIT :limit
                """)
                
                result = await session.execute(
                    sql,
                    {"org_id": self.organization_id, "limit": self.settings.max_retrieval_results}
                )
                
                results = []
                for row in result:
                    results.append({
                        "id": row[0],
                        "organization_id": row[1],
                        "framework": row[2],
                        "control_id": row[3],
                        "status": row[4] or "unknown",
                        "finding_count": row[5] or 0,
                        "last_evaluated_at": row[6],
                    })
                
                logger.info(f"Retrieved {len(results)} compliance results")
                return results
                
        except Exception as e:
            logger.error(f"Failed to fetch compliance results: {e}")
            return []

    async def _fetch_recent_scans(self) -> list[dict]:
        """Fetch recent security scans."""
        try:
            if not self.session_factory:
                return []
            
            async with self.session_factory() as session:
                from sqlalchemy import text
                
                sql = text("""
                    SELECT 
                        id::text,
                        organization_id::text,
                        scan_type,
                        status,
                        started_at::text,
                        completed_at::text,
                        resources_scanned,
                        findings_created,
                        findings_resolved,
                        error_message
                    FROM cspm_scans
                    WHERE organization_id = :org_id
                    ORDER BY started_at DESC
                    LIMIT 10
                """)
                
                result = await session.execute(sql, {"org_id": self.organization_id})
                
                scans = []
                for row in result:
                    scans.append({
                        "id": row[0],
                        "organization_id": row[1],
                        "scan_type": row[2],
                        "status": row[3],
                        "started_at": row[4],
                        "completed_at": row[5],
                        "resources_scanned": row[6] or 0,
                        "findings_created": row[7] or 0,
                        "findings_resolved": row[8] or 0,
                        "error_message": row[9] or "",
                    })
                
                logger.info(f"Retrieved {len(scans)} recent scans")
                return scans
                
        except Exception as e:
            logger.error(f"Failed to fetch scans: {e}")
            return []

    async def _fetch_users(self) -> list[dict]:
        """Fetch organization users."""
        try:
            if not self.session_factory:
                return []
            
            async with self.session_factory() as session:
                from sqlalchemy import text
                
                sql = text("""
                    SELECT 
                        u.id::text,
                        u.email,
                        u.full_name,
                        u.is_active,
                        u.created_at::text,
                        u.last_login_at::text,
                        array_agg(r.name) as roles
                    FROM users u
                    LEFT JOIN user_roles ur ON u.id = ur.user_id
                    LEFT JOIN roles r ON ur.role_id = r.id
                    WHERE u.organization_id = :org_id
                    GROUP BY u.id, u.email, u.full_name, u.is_active, u.created_at, u.last_login_at
                    ORDER BY u.created_at DESC
                """)
                
                result = await session.execute(sql, {"org_id": self.organization_id})
                
                users = []
                for row in result:
                    users.append({
                        "id": row[0],
                        "email": row[1],
                        "full_name": row[2] or "",
                        "is_active": row[3],
                        "created_at": row[4],
                        "last_login_at": row[5],
                        "roles": row[6] or [],
                    })
                
                logger.info(f"Retrieved {len(users)} users")
                return users
                
        except Exception as e:
            logger.error(f"Failed to fetch users: {e}")
            return []

    async def _fetch_rules(self) -> list[dict]:
        """Fetch security rules."""
        try:
            if not self.session_factory:
                return []
            
            async with self.session_factory() as session:
                from sqlalchemy import text
                
                sql = text("""
                    SELECT 
                        id::text,
                        rule_id,
                        title,
                        description,
                        severity,
                        category,
                        framework_mappings,
                        is_enabled
                    FROM rules
                    WHERE is_enabled = true
                    ORDER BY severity DESC, title
                    LIMIT :limit
                """)
                
                result = await session.execute(
                    sql,
                    {"limit": self.settings.max_retrieval_results}
                )
                
                rules = []
                for row in result:
                    rules.append({
                        "id": row[0],
                        "rule_id": row[1],
                        "title": row[2],
                        "description": row[3] or "",
                        "severity": row[4],
                        "category": row[5] or "",
                        "framework_mappings": row[6] or {},
                        "is_enabled": row[7],
                    })
                
                logger.info(f"Retrieved {len(rules)} rules")
                return rules
                
        except Exception as e:
            logger.error(f"Failed to fetch rules: {e}")
            return []

    async def _fetch_assets_from_db(self) -> list[dict]:
        """Fetch assets directly from PostgreSQL as fallback."""
        try:
            if not self.session_factory:
                return []

            async with self.session_factory() as session:
                from sqlalchemy import text

                sql = text("""
                    SELECT
                        id::text,
                        cloud_resource_id,
                        provider,
                        account_id,
                        region,
                        resource_type,
                        name,
                        tags,
                        is_public,
                        environment,
                        last_seen_at::text
                    FROM connector_discovered_resources
                    WHERE organization_id = :org_id
                    AND is_deleted = false
                    ORDER BY resource_type, name
                """)

                result = await session.execute(sql, {"org_id": self.organization_id})

                assets = []
                for row in result:
                    assets.append({
                        "id": row[1],  # use cloud_resource_id as id
                        "cloud_resource_id": row[1],
                        "provider": row[2],
                        "account_id": row[3],
                        "region": row[4],
                        "resource_type": row[5],
                        "name": row[6],
                        "tags": row[7] or {},
                        "is_public": row[8],
                        "environment": row[9],
                        "last_seen_at": row[10],
                        "risk_score": 0,
                        "open_findings_count": 0,
                    })

                logger.info(f"Retrieved {len(assets)} assets from PostgreSQL fallback")
                return assets

        except Exception as e:
            logger.error(f"Failed to fetch assets from DB: {e}")
            return []

    # ── New data sources ──────────────────────────────────────────────────────

    async def _fetch_posture_snapshots(self) -> list[dict]:
        """Fetch posture score history (last 30 days)."""
        try:
            if not self.session_factory:
                return []
            async with self.session_factory() as session:
                from sqlalchemy import text
                sql = text("""
                    SELECT
                        snapshot_date::text,
                        posture_score,
                        critical_count,
                        high_count,
                        medium_count,
                        low_count
                    FROM cspm_posture_snapshots
                    WHERE organization_id = :org_id
                    ORDER BY snapshot_date DESC
                    LIMIT 30
                """)
                result = await session.execute(sql, {"org_id": self.organization_id})
                rows = []
                for row in result:
                    rows.append({
                        "snapshot_date": row[0],
                        "posture_score": row[1],
                        "critical_count": row[2],
                        "high_count": row[3],
                        "medium_count": row[4],
                        "low_count": row[5],
                    })
                logger.info(f"Retrieved {len(rows)} posture snapshots")
                return rows
        except Exception as e:
            logger.error(f"Failed to fetch posture snapshots: {e}")
            return []

    async def _fetch_incidents(self) -> list[dict]:
        """Fetch open incidents for the org."""
        try:
            if not self.session_factory:
                return []
            async with self.session_factory() as session:
                from sqlalchemy import text
                sql = text("""
                    SELECT
                        id::text,
                        title,
                        description,
                        severity,
                        status,
                        array_length(finding_ids, 1) as finding_count,
                        created_at::text,
                        updated_at::text
                    FROM incidents
                    WHERE organization_id = :org_id
                    ORDER BY
                        CASE severity
                            WHEN 'CRITICAL' THEN 1
                            WHEN 'HIGH' THEN 2
                            WHEN 'MEDIUM' THEN 3
                            ELSE 4
                        END,
                        created_at DESC
                    LIMIT 50
                """)
                result = await session.execute(sql, {"org_id": self.organization_id})
                rows = []
                for row in result:
                    rows.append({
                        "id": row[0],
                        "title": row[1],
                        "description": row[2] or "",
                        "severity": row[3],
                        "status": row[4],
                        "finding_count": row[5] or 0,
                        "created_at": row[6],
                        "updated_at": row[7],
                    })
                logger.info(f"Retrieved {len(rows)} incidents")
                return rows
        except Exception as e:
            logger.error(f"Failed to fetch incidents: {e}")
            return []

    async def _fetch_findings_direct(self, status_filter: str = "open") -> list[dict]:
        """Fetch ALL findings from BOTH findings and cspm_findings tables, merged and deduplicated."""
        all_findings = []

        # ── Table 1: findings (alert service) ────────────────────────────────
        try:
            if self.session_factory:
                async with self.session_factory() as session:
                    from sqlalchemy import text
                    sql = text("""
                        SELECT
                            id::text,
                            rule_id,
                            resource_id,
                            resource_name,
                            severity,
                            status,
                            title,
                            description,
                            remediation,
                            provider,
                            account_id,
                            region,
                            resource_type,
                            first_seen_at::text,
                            last_seen_at::text,
                            regression_count
                        FROM findings
                        WHERE organization_id = :org_id
                        ORDER BY
                            CASE severity
                                WHEN 'CRITICAL' THEN 1
                                WHEN 'HIGH' THEN 2
                                WHEN 'MEDIUM' THEN 3
                                WHEN 'LOW' THEN 4
                                ELSE 5
                            END,
                            last_seen_at DESC
                        LIMIT :limit
                    """)
                    result = await session.execute(sql, {
                        "org_id": self.organization_id,
                        "limit": self.settings.max_retrieval_results,
                    })
                    for row in result:
                        all_findings.append({
                            "id": row[0],
                            "rule_id": row[1] or "",
                            "resource_id": row[2] or "",
                            "resource_name": row[3] or "",
                            "severity": row[4],
                            "status": row[5],
                            "title": row[6],
                            "description": row[7] or "",
                            "remediation": row[8] or "",
                            "provider": row[9] or "",
                            "account_id": row[10] or "",
                            "region": row[11] or "",
                            "resource_type": row[12] or "",
                            "created_at": row[13],
                            "last_seen_at": row[14],
                            "source": "findings",
                        })
                    logger.info(f"Retrieved {len(all_findings)} findings from findings table")
        except Exception as e:
            logger.error(f"Failed to fetch from findings table: {e}")

        # ── Table 2: cspm_findings (CSPM service) ─────────────────────────────
        try:
            if self.session_factory:
                async with self.session_factory() as session:
                    from sqlalchemy import text
                    sql = text("""
                        SELECT
                            id::text,
                            title,
                            description,
                            severity,
                            status,
                            resource_name,
                            resource_type,
                            rule_id,
                            created_at::text,
                            organization_id::text
                        FROM cspm_findings
                        WHERE organization_id = :org_id
                        ORDER BY
                            CASE severity
                                WHEN 'CRITICAL' THEN 1
                                WHEN 'HIGH' THEN 2
                                WHEN 'MEDIUM' THEN 3
                                WHEN 'LOW' THEN 4
                                ELSE 5
                            END,
                            created_at DESC
                        LIMIT :limit
                    """)
                    result = await session.execute(sql, {
                        "org_id": self.organization_id,
                        "limit": self.settings.max_retrieval_results,
                    })
                    cspm_count = 0
                    for row in result:
                        all_findings.append({
                            "id": row[0],
                            "title": row[1],
                            "description": row[2] or "",
                            "severity": row[3],
                            "status": row[4],
                            "resource_name": row[5] or "",
                            "resource_type": row[6] or "",
                            "rule_id": row[7] or "",
                            "created_at": row[8],
                            "organization_id": row[9],
                            "source": "cspm_findings",
                        })
                        cspm_count += 1
                    logger.info(f"Retrieved {cspm_count} findings from cspm_findings table")
        except Exception as e:
            logger.error(f"Failed to fetch from cspm_findings table: {e}")

        # Sort merged list by severity
        severity_order = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}
        all_findings.sort(key=lambda f: severity_order.get(f.get("severity", "LOW"), 5))

        logger.info(f"Total findings from all tables: {len(all_findings)}")
        return all_findings

    async def _fetch_resource_posture(self) -> list[dict]:
        """Fetch per-resource posture scores (internet-exposed, sensitive data, etc.)."""
        try:
            if not self.session_factory:
                return []
            async with self.session_factory() as session:
                from sqlalchemy import text
                sql = text("""
                    SELECT
                        resource_id,
                        resource_name,
                        resource_type,
                        provider,
                        account_id,
                        region,
                        environment,
                        risk_score,
                        is_internet_exposed,
                        contains_sensitive_data,
                        critical_count,
                        high_count,
                        medium_count,
                        low_count,
                        last_scanned_at::text
                    FROM cspm_resource_posture
                    WHERE organization_id = :org_id
                    ORDER BY risk_score DESC, critical_count DESC
                    LIMIT :limit
                """)
                result = await session.execute(sql, {
                    "org_id": self.organization_id,
                    "limit": self.settings.max_retrieval_results,
                })
                rows = []
                for row in result:
                    rows.append({
                        "resource_id": row[0],
                        "resource_name": row[1] or "",
                        "resource_type": row[2] or "",
                        "provider": row[3] or "",
                        "account_id": row[4] or "",
                        "region": row[5] or "",
                        "environment": row[6] or "",
                        "risk_score": row[7] or 0,
                        "is_internet_exposed": row[8] or False,
                        "contains_sensitive_data": row[9] or False,
                        "critical_count": row[10] or 0,
                        "high_count": row[11] or 0,
                        "medium_count": row[12] or 0,
                        "low_count": row[13] or 0,
                        "last_scanned_at": row[14],
                    })
                logger.info(f"Retrieved {len(rows)} resource posture records")
                return rows
        except Exception as e:
            logger.error(f"Failed to fetch resource posture: {e}")
            return []

    async def _fetch_suppression_rules(self) -> list[dict]:
        """Fetch active suppression rules."""
        try:
            if not self.session_factory:
                return []
            async with self.session_factory() as session:
                from sqlalchemy import text
                sql = text("""
                    SELECT
                        id::text,
                        rule_id,
                        resource_tag_key,
                        resource_tag_value,
                        account_id,
                        region,
                        reason,
                        created_by,
                        expires_at::text,
                        created_at::text
                    FROM suppression_rules
                    WHERE organization_id = :org_id
                    AND is_active = true
                    ORDER BY created_at DESC
                """)
                result = await session.execute(sql, {"org_id": self.organization_id})
                rows = []
                for row in result:
                    rows.append({
                        "id": row[0],
                        "rule_id": row[1] or "",
                        "resource_tag_key": row[2] or "",
                        "resource_tag_value": row[3] or "",
                        "account_id": row[4] or "",
                        "region": row[5] or "",
                        "reason": row[6] or "",
                        "created_by": row[7],
                        "expires_at": row[8],
                        "created_at": row[9],
                    })
                logger.info(f"Retrieved {len(rows)} suppression rules")
                return rows
        except Exception as e:
            logger.error(f"Failed to fetch suppression rules: {e}")
            return []

    async def _fetch_frameworks(self) -> list[dict]:
        """Fetch compliance frameworks."""
        try:
            if not self.session_factory:
                return []
            async with self.session_factory() as session:
                from sqlalchemy import text
                sql = text("""
                    SELECT
                        id::text,
                        name,
                        display_name,
                        description,
                        version,
                        array_length(controls, 1) as control_count
                    FROM frameworks
                    ORDER BY name
                """)
                result = await session.execute(sql)
                rows = []
                for row in result:
                    rows.append({
                        "id": row[0],
                        "name": row[1],
                        "display_name": row[2],
                        "description": row[3] or "",
                        "version": row[4],
                        "control_count": row[5] or 0,
                    })
                logger.info(f"Retrieved {len(rows)} frameworks")
                return rows
        except Exception as e:
            logger.error(f"Failed to fetch frameworks: {e}")
            return []

    async def _fetch_finding_history(self, finding_id: str) -> list[dict]:
        """Fetch status history for a specific finding."""
        try:
            if not self.session_factory:
                return []
            async with self.session_factory() as session:
                from sqlalchemy import text
                sql = text("""
                    SELECT
                        id::text,
                        old_status,
                        new_status,
                        changed_by::text,
                        changed_at::text,
                        comment
                    FROM finding_history
                    WHERE finding_id = :finding_id
                    ORDER BY changed_at DESC
                    LIMIT 20
                """)
                result = await session.execute(sql, {"finding_id": finding_id})
                rows = []
                for row in result:
                    rows.append({
                        "id": row[0],
                        "old_status": row[1],
                        "new_status": row[2],
                        "changed_by": row[3],
                        "changed_at": row[4],
                        "comment": row[5] or "",
                    })
                return rows
        except Exception as e:
            logger.error(f"Failed to fetch finding history: {e}")
            return []

    async def _fetch_audit_changes_windowed(self, hours: int = 24) -> list[dict]:
        """Fetch audit log changes within a time window."""
        try:
            if not self.session_factory:
                return []
            async with self.session_factory() as session:
                from sqlalchemy import text
                sql = text("""
                    SELECT
                        id::text,
                        user_id::text,
                        action,
                        resource_type,
                        resource_id,
                        changes,
                        timestamp::text,
                        ip_address
                    FROM audit_log
                    WHERE organization_id = :org_id
                    AND timestamp >= NOW() - INTERVAL ':hours hours'
                    ORDER BY timestamp DESC
                    LIMIT 100
                """)
                # Use string interpolation for interval (SQLAlchemy doesn't bind interval well)
                sql = text(f"""
                    SELECT
                        id::text,
                        user_id::text,
                        action,
                        resource_type,
                        resource_id,
                        changes,
                        timestamp::text,
                        ip_address
                    FROM audit_log
                    WHERE organization_id = :org_id
                    AND timestamp >= NOW() - INTERVAL '{hours} hours'
                    ORDER BY timestamp DESC
                    LIMIT 100
                """)
                result = await session.execute(sql, {"org_id": self.organization_id})
                rows = []
                for row in result:
                    rows.append({
                        "id": row[0],
                        "user_id": row[1],
                        "action": row[2],
                        "resource_type": row[3] or "",
                        "resource_id": row[4] or "",
                        "changes": row[5] or {},
                        "timestamp": row[6],
                        "ip_address": row[7] or "",
                    })
                logger.info(f"Retrieved {len(rows)} audit changes in last {hours}h")
                return rows
        except Exception as e:
            logger.error(f"Failed to fetch windowed audit changes: {e}")
            return []

    async def _fetch_audit_changes_for_identity(self, query: str) -> list[dict]:
        """Fetch audit log filtered by identity hint extracted from query."""
        try:
            if not self.session_factory:
                return []
            async with self.session_factory() as session:
                from sqlalchemy import text
                # Broad fetch — LLM will filter by identity from the query
                sql = text("""
                    SELECT
                        id::text,
                        user_id::text,
                        action,
                        resource_type,
                        resource_id,
                        changes,
                        timestamp::text,
                        ip_address
                    FROM audit_log
                    WHERE organization_id = :org_id
                    AND timestamp >= NOW() - INTERVAL '48 hours'
                    ORDER BY timestamp DESC
                    LIMIT 200
                """)
                result = await session.execute(sql, {"org_id": self.organization_id})
                rows = []
                for row in result:
                    rows.append({
                        "id": row[0],
                        "user_id": row[1],
                        "action": row[2],
                        "resource_type": row[3] or "",
                        "resource_id": row[4] or "",
                        "changes": row[5] or {},
                        "timestamp": row[6],
                        "ip_address": row[7] or "",
                    })
                logger.info(f"Retrieved {len(rows)} audit entries for identity investigation")
                return rows
        except Exception as e:
            logger.error(f"Failed to fetch identity audit changes: {e}")
            return []

    async def _fetch_asset_snapshots_windowed(self, hours: int = 24) -> list[dict]:
        """Fetch asset snapshots within a time window for drift analysis."""
        try:
            if not self.session_factory:
                return []
            async with self.session_factory() as session:
                from sqlalchemy import text
                sql = text(f"""
                    SELECT
                        asset_id,
                        provider,
                        account_id,
                        region,
                        resource_type,
                        name,
                        environment,
                        is_public,
                        risk_score,
                        open_findings_count,
                        diff_from_previous,
                        snapshot_timestamp::text
                    FROM asset_snapshots
                    WHERE organization_id = :org_id
                    AND snapshot_timestamp >= NOW() - INTERVAL '{hours} hours'
                    AND diff_from_previous IS NOT NULL
                    ORDER BY snapshot_timestamp DESC
                    LIMIT 100
                """)
                result = await session.execute(sql, {"org_id": self.organization_id})
                rows = []
                for row in result:
                    rows.append({
                        "asset_id": row[0],
                        "provider": row[1],
                        "account_id": row[2],
                        "region": row[3],
                        "resource_type": row[4],
                        "name": row[5],
                        "environment": row[6],
                        "is_public": bool(row[7]),
                        "risk_score": row[8] or 0,
                        "open_findings_count": row[9] or 0,
                        "diff_from_previous": row[10] or {},
                        "snapshot_timestamp": row[11],
                    })
                logger.info(f"Retrieved {len(rows)} asset snapshots with diffs in last {hours}h")
                return rows
        except Exception as e:
            logger.error(f"Failed to fetch asset snapshots: {e}")
            return []

    async def close(self):
        """Close Elasticsearch client."""
        await self.es_client.close()
