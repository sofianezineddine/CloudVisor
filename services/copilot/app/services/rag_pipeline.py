"""Main RAG pipeline orchestration - autonomous LLM-driven flow."""

import logging
import time
from datetime import datetime
from typing import AsyncGenerator

from ..core.config import CopilotSettings
from ..schemas.request import CopilotQueryRequest
from ..schemas.response import CopilotQueryResponse, Citation, SuggestedAction
from .retriever import ContextRetriever
from .prompt_builder import PromptBuilder
from .llm_client import get_llm_client

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Orchestrates the 6-step RAG pipeline for CloudVisor Q."""

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

        # No intent classifier - let the LLM be autonomous
        self.retriever = ContextRetriever(settings, organization_id, session_factory)
        self.prompt_builder = PromptBuilder()
        self.llm_client = get_llm_client(settings)

    async def execute(
        self, request: CopilotQueryRequest
    ) -> CopilotQueryResponse | AsyncGenerator[str, None]:
        start_time = time.time()
        query_id = self._generate_query_id()
        logger.info(f"Starting RAG pipeline for query_id={query_id}")

        try:
            # Step 1: Fetch comprehensive context (no intent classification)
            # Let the LLM decide what's relevant from all available data
            context = await self._retrieve_comprehensive_context(
                request.query,
                request.context.finding_id if request.context else None,
                request.context.asset_id if request.context else None,
            )

            # Inject UI context and conversation history
            if request.ui_context:
                context["ui_context"] = request.ui_context.model_dump()
            if request.conversation_history:
                context["conversation_history"] = [
                    m.model_dump() for m in request.conversation_history
                ]

            # Step 2: Build prompt with retrieved context
            system_prompt, user_prompt = self._build_prompts(request.query, context)

            # Step 3: LLM Call
            if request.stream:
                return self._execute_streaming(
                    query_id, system_prompt, user_prompt, context, start_time
                )
            else:
                return await self._execute_complete(
                    query_id, system_prompt, user_prompt, context, start_time
                )

        except Exception as e:
            logger.error(f"RAG pipeline failed for query_id={query_id}: {e}", exc_info=True)
            raise

    async def _execute_complete(
        self,
        query_id: str,
        system_prompt: str,
        user_prompt: str,
        context: dict,
        start_time: float,
    ) -> CopilotQueryResponse:
        answer = await self.llm_client.generate(system_prompt, user_prompt, stream=False)
        processing_ms = int((time.time() - start_time) * 1000)
        citations = self._parse_citations(answer)
        
        # Let the LLM determine what actions are relevant based on the query and context
        suggested_actions = self._generate_dynamic_actions(context)

        response = CopilotQueryResponse(
            query_id=query_id,
            answer=answer,
            intent="GENERAL",  # No longer using intent classification
            citations=citations,
            suggested_actions=suggested_actions,
            data_freshness=datetime.utcnow(),
            processing_ms=processing_ms,
            data_sources_used=context.get("sources_used", []),
        )
        logger.info(f"RAG pipeline completed for query_id={query_id} in {processing_ms}ms")
        return response

    async def _execute_streaming(
        self,
        query_id: str,
        system_prompt: str,
        user_prompt: str,
        context: dict,
        start_time: float,
    ) -> AsyncGenerator[str, None]:
        stream = await self.llm_client.generate(system_prompt, user_prompt, stream=True)
        async for token in stream:
            yield token

    async def _retrieve_comprehensive_context(
        self,
        query: str,
        finding_id: str | None,
        asset_id: str | None,
    ) -> dict:
        """
        Retrieve comprehensive context from all available sources.
        Let the LLM decide what's relevant instead of pre-filtering by intent.
        """
        logger.info("Retrieving comprehensive context from all sources")
        
        # Always fetch core data that gives the LLM full situational awareness
        context = await self.retriever.retrieve(
            "COMPREHENSIVE",  # Special mode to fetch everything
            query,
            finding_id,
            asset_id
        )
        
        logger.info(f"Context retrieved from {len(context.get('sources_used', []))} sources")
        return context

    def _build_prompts(self, query: str, context: dict) -> tuple[str, str]:
        logger.info("Building prompts")
        system_prompt, user_prompt = self.prompt_builder.build_prompts(query, context)
        logger.info(f"Prompts built: system={len(system_prompt)} chars")
        return system_prompt, user_prompt

    def _parse_citations(self, answer: str) -> list[Citation]:
        return []

    def _generate_dynamic_actions(self, context: dict) -> list[SuggestedAction]:
        """
        Generate suggested actions based on available data, not intent.
        Provide the most relevant actions based on what data we have.
        """
        actions = []

        # Always offer dashboard as a starting point
        actions.append(SuggestedAction(
            label="View Dashboard",
            action="navigate",
            target="/dashboard"
        ))

        # If we have findings, offer to view them
        if context.get("findings") or context.get("findings_summary"):
            actions.append(SuggestedAction(
                label="View All Findings",
                action="navigate",
                target="/findings"
            ))

        # If we have a specific finding, offer remediation
        if context.get("finding"):
            finding_id = context["finding"].get("id")
            actions.append(SuggestedAction(
                label="Generate Fix",
                action="remediation",
                finding_id=finding_id
            ))

        # If we have assets, offer to view them
        if context.get("assets"):
            actions.append(SuggestedAction(
                label="View Assets",
                action="navigate",
                target="/assets"
            ))

        # If we have compliance data, offer compliance view
        if context.get("compliance") or context.get("compliance_results"):
            actions.append(SuggestedAction(
                label="View Compliance",
                action="navigate",
                target="/compliance"
            ))

        return actions

    def _generate_query_id(self) -> str:
        import uuid
        return f"q_{uuid.uuid4().hex[:12]}"

    async def close(self):
        await self.retriever.close()
