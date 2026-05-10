"""Refactored RAG pipeline — intent-routed, minimal-context, multi-turn aware.

Flow:
1. Classify the query (regex-based, instant — no LLM call)
2. Fetch only the data sources the classification says we need
3. Build a focused system prompt for this specific query type
4. Pass conversation history as proper chat messages
5. Call the LLM and return the answer
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator

from ..core.config import CopilotSettings
from ..schemas.request import CopilotQueryRequest
from ..schemas.response import CopilotQueryResponse, Citation, SuggestedAction
from .llm_client import get_llm_client
from .prompt_builder import PromptBuilder
from .query_router import QueryType, classify_query
from .retriever import ContextRetriever

logger = logging.getLogger(__name__)


# Mapping of needed_sources → retriever methods. Keeps the pipeline decoupled
# from the retriever's internal method names.
_SOURCE_FETCHERS = {
    "cloud_accounts": lambda r: r._fetch_cloud_accounts(),
    "posture_snapshots": lambda r: r._fetch_posture_snapshots(),
    "findings": lambda r: r._fetch_findings_direct(),
    "assets": lambda r: r._fetch_assets_from_db(),
    "resource_posture": lambda r: r._fetch_resource_posture(),
    "compliance_results": lambda r: r._fetch_compliance_results(),
    "frameworks": lambda r: r._fetch_frameworks(),
    "rules": lambda r: r._fetch_rules(),
    "recent_scans": lambda r: r._fetch_recent_scans(),
}


class RAGPipeline:
    """Orchestrates the refactored pipeline."""

    def __init__(
        self,
        settings: CopilotSettings,
        organization_id: str,
        user_id: str,
        session_factory=None,
    ):
        self.settings = settings
        self.organization_id = organization_id
        self.user_id = user_id
        self.retriever = ContextRetriever(settings, organization_id, session_factory)
        self.prompt_builder = PromptBuilder()
        self.llm_client = get_llm_client(settings)

    async def execute(
        self, request: CopilotQueryRequest
    ) -> CopilotQueryResponse | AsyncGenerator[str, None]:
        """Execute the full pipeline for a single query."""
        start_time = time.time()
        query_id = self._new_query_id()

        # ── 1. Classify the query ──────────────────────────────────────────
        history = [m.model_dump() for m in (request.conversation_history or [])]
        classification = classify_query(request.query, conversation_history=history)
        logger.info(
            f"query_id={query_id} classified as {classification.query_type} "
            f"(needs_data={classification.needs_data}, "
            f"sources={classification.needed_sources})"
        )

        # ── 2. Retrieve targeted context (only what's needed) ──────────────
        context = await self._retrieve_context(classification.needed_sources, request)

        # Preloaded finding/asset from UI
        if request.context:
            if request.context.finding_id:
                await self._attach_finding(context, request.context.finding_id)
            if request.context.asset_id:
                await self._attach_asset(context, request.context.asset_id)

        # ── 3. Build messages (system + history + user) ─────────────────────
        ui_context = request.ui_context.model_dump() if request.ui_context else None
        if ui_context:
            context["ui_context"] = ui_context

        messages = self.prompt_builder.build_messages(
            query=request.query,
            context=context,
            query_type=classification.query_type,
            conversation_history=history,
        )

        # ── 4. Call the LLM ─────────────────────────────────────────────────
        if request.stream:
            return self._stream(query_id, messages, context, classification, start_time)
        return await self._complete(query_id, messages, context, classification, start_time)

    # ─────────────────────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────────────────────

    async def _retrieve_context(
        self, needed_sources: list[str], request: CopilotQueryRequest
    ) -> dict[str, Any]:
        """Fetch only the data sources the classifier asked for, concurrently."""
        context: dict[str, Any] = {"sources_used": []}

        if not needed_sources:
            return context

        async def _fetch(name: str) -> None:
            fetcher = _SOURCE_FETCHERS.get(name)
            if not fetcher:
                return
            try:
                result = await fetcher(self.retriever)
                if result:
                    context[name] = result
                    context["sources_used"].append(name)
            except Exception as exc:
                logger.warning(f"Failed to fetch {name}: {exc}")

        await asyncio.gather(*[_fetch(src) for src in needed_sources])
        logger.info(f"Retrieved context from: {context['sources_used']}")
        return context

    async def _attach_finding(self, context: dict, finding_id: str) -> None:
        try:
            finding = await self.retriever._fetch_finding_by_id(finding_id)
            if finding:
                context["finding"] = finding
                context["sources_used"].append("finding_detail")
        except Exception as exc:
            logger.warning(f"Failed to attach finding {finding_id}: {exc}")

    async def _attach_asset(self, context: dict, asset_id: str) -> None:
        try:
            asset = await self.retriever._fetch_asset_by_id(asset_id)
            if asset:
                context["preloaded_asset"] = asset
                context["sources_used"].append("asset_detail")
        except Exception as exc:
            logger.warning(f"Failed to attach asset {asset_id}: {exc}")

    async def _complete(
        self,
        query_id: str,
        messages: list[dict],
        context: dict,
        classification,
        start_time: float,
    ) -> CopilotQueryResponse:
        """Non-streaming response."""
        answer = await self.llm_client.generate_from_messages(messages, stream=False)
        processing_ms = int((time.time() - start_time) * 1000)

        return CopilotQueryResponse(
            query_id=query_id,
            answer=answer,
            intent=self._map_intent(classification.query_type),
            citations=[],
            suggested_actions=self._suggest_actions(context, classification.query_type),
            data_freshness=datetime.utcnow(),
            processing_ms=processing_ms,
            data_sources_used=context.get("sources_used", []),
        )

    async def _stream(
        self,
        query_id: str,
        messages: list[dict],
        context: dict,
        classification,
        start_time: float,
    ) -> AsyncGenerator[str, None]:
        """Streaming response — yields tokens as they arrive."""
        stream = await self.llm_client.generate_from_messages(messages, stream=True)
        async for token in stream:
            yield token

    def _suggest_actions(
        self, context: dict, query_type: QueryType
    ) -> list[SuggestedAction]:
        """Contextual actions based on query type."""
        actions: list[SuggestedAction] = []

        if query_type == QueryType.FINDINGS and context.get("findings"):
            actions.append(SuggestedAction(
                label="View All Findings", action="navigate", target="/findings"
            ))

        if query_type == QueryType.ASSETS and context.get("assets"):
            actions.append(SuggestedAction(
                label="View All Assets", action="navigate", target="/assets"
            ))

        if query_type == QueryType.COMPLIANCE:
            actions.append(SuggestedAction(
                label="View Compliance", action="navigate", target="/compliance"
            ))

        if query_type == QueryType.POSTURE:
            actions.append(SuggestedAction(
                label="View Dashboard", action="navigate", target="/dashboard"
            ))

        if query_type == QueryType.REMEDIATION and context.get("finding"):
            actions.append(SuggestedAction(
                label="Generate Fix",
                action="remediation",
                finding_id=context["finding"].get("id"),
            ))

        return actions

    @staticmethod
    def _map_intent(query_type: QueryType) -> str:
        """Map QueryType to the legacy intent enum."""
        mapping = {
            QueryType.SMALL_TALK: "GENERAL",
            QueryType.META: "GENERAL",
            QueryType.COUNT: "GENERAL",
            QueryType.LIST: "GENERAL",
            QueryType.POSTURE: "POSTURE",
            QueryType.FINDINGS: "FINDING",
            QueryType.ASSETS: "POSTURE",
            QueryType.COMPLIANCE: "COMPLIANCE",
            QueryType.REMEDIATION: "REMEDIATION",
            QueryType.ACCOUNTS: "GENERAL",
            QueryType.GENERAL: "GENERAL",
        }
        return mapping.get(query_type, "GENERAL")

    @staticmethod
    def _new_query_id() -> str:
        return f"q_{uuid.uuid4().hex[:12]}"

    async def close(self) -> None:
        await self.retriever.close()
