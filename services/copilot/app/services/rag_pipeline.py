"""Main RAG pipeline orchestration - the 6-step flow."""

import logging
import time
from datetime import datetime
from typing import AsyncGenerator

from ..core.config import CopilotSettings
from ..schemas.request import CopilotQueryRequest
from ..schemas.response import CopilotQueryResponse, Citation, SuggestedAction, IntentType
from .intent_classifier import IntentClassifier
from .retriever import ContextRetriever
from .prompt_builder import PromptBuilder
from .llm_client import get_llm_client
from .direct_answer import DirectAnswerEngine

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

        self.intent_classifier = IntentClassifier()
        self.retriever = ContextRetriever(settings, organization_id, session_factory)
        self.prompt_builder = PromptBuilder()
        self.llm_client = get_llm_client(settings)
        self.direct_engine = DirectAnswerEngine()

    async def execute(
        self, request: CopilotQueryRequest
    ) -> CopilotQueryResponse | AsyncGenerator[str, None]:
        start_time = time.time()
        query_id = self._generate_query_id()
        logger.info(f"Starting RAG pipeline for query_id={query_id}")

        try:
            # Step 1: Intent Classification
            intent = self._classify_intent(request.query)

            # Step 3: Multi-Source Context Retrieval
            context = await self._retrieve_context(
                intent,
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

            # ── Step 3.5: Direct Answer Engine ──────────────────────────
            # For factual queries (counts, lists, status), answer directly
            # from the retrieved data — no LLM, no hallucination.
            if not request.stream and self.direct_engine.can_answer(request.query, context):
                logger.info(f"Direct answer engine handling query: {request.query[:80]}")
                answer = self.direct_engine.answer(request.query, context)
                processing_ms = int((time.time() - start_time) * 1000)
                logger.info(f"Direct answer generated in {processing_ms}ms")
                return CopilotQueryResponse(
                    query_id=query_id,
                    session_id=request.session_id,
                    answer=answer,
                    intent=intent,
                    citations=[],
                    suggested_actions=self._generate_suggested_actions(intent, context),
                    data_freshness=datetime.utcnow(),
                    processing_ms=processing_ms,
                    data_sources_used=context.get("sources_used", []),
                )

            # Step 4: Prompt Construction (for complex/analytical queries)
            system_prompt, user_prompt = self._build_prompts(request.query, context)

            # Step 5: LLM Call
            if request.stream:
                return self._execute_streaming(
                    query_id, intent, system_prompt, user_prompt, context, start_time
                )
            else:
                return await self._execute_complete(
                    query_id, intent, system_prompt, user_prompt, context, start_time
                )

        except Exception as e:
            logger.error(f"RAG pipeline failed for query_id={query_id}: {e}", exc_info=True)
            raise

    async def _execute_complete(
        self,
        query_id: str,
        intent: IntentType,
        system_prompt: str,
        user_prompt: str,
        context: dict,
        start_time: float,
    ) -> CopilotQueryResponse:
        answer = await self.llm_client.generate(system_prompt, user_prompt, stream=False)
        processing_ms = int((time.time() - start_time) * 1000)
        citations = self._parse_citations(answer)
        suggested_actions = self._generate_suggested_actions(intent, context)

        response = CopilotQueryResponse(
            query_id=query_id,
            session_id=getattr(request, 'session_id', None),
            answer=answer,
            intent=intent,
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
        intent: IntentType,
        system_prompt: str,
        user_prompt: str,
        context: dict,
        start_time: float,
    ) -> AsyncGenerator[str, None]:
        stream = await self.llm_client.generate(system_prompt, user_prompt, stream=True)
        async for token in stream:
            yield token

    def _classify_intent(self, query: str) -> IntentType:
        logger.info("Step 1: Classifying intent")
        intent = self.intent_classifier.classify(query)
        logger.info(f"Intent classified as: {intent}")
        return intent

    async def _retrieve_context(
        self,
        intent: IntentType,
        query: str,
        finding_id: str | None,
        asset_id: str | None,
    ) -> dict:
        logger.info("Step 3: Retrieving context")
        context = await self.retriever.retrieve(intent, query, finding_id, asset_id)
        logger.info(f"Context retrieved from {len(context.get('sources_used', []))} sources")
        return context

    def _build_prompts(self, query: str, context: dict) -> tuple[str, str]:
        logger.info("Step 4: Building prompts")
        system_prompt, user_prompt = self.prompt_builder.build_prompts(query, context)
        logger.info(f"Prompts built: system={len(system_prompt)} chars")
        return system_prompt, user_prompt

    def _parse_citations(self, answer: str) -> list[Citation]:
        return []

    def _generate_suggested_actions(
        self, intent: IntentType, context: dict
    ) -> list[SuggestedAction]:
        actions = []

        if intent == "POSTURE":
            actions.append(SuggestedAction(label="View all findings", action="navigate", target="/findings"))
            if context.get("assets"):
                actions.append(SuggestedAction(label="View assets", action="navigate", target="/assets"))

        elif intent == "FINDING":
            if "finding" in context:
                finding_id = context["finding"].get("id")
                actions.append(SuggestedAction(label="Generate fix", action="remediation", finding_id=finding_id))
            actions.append(SuggestedAction(label="View all findings", action="navigate", target="/findings"))

        elif intent == "COMPLIANCE":
            actions.append(SuggestedAction(label="View compliance", action="navigate", target="/compliance"))
            actions.append(SuggestedAction(label="Export report", action="export", target="/compliance/export"))

        elif intent == "THREAT":
            actions.append(SuggestedAction(label="Investigate in CDR", action="investigate", target="/cdr/events"))

        elif intent == "DRIFT":
            actions.append(SuggestedAction(label="View assets", action="navigate", target="/assets"))

        return actions

    def _generate_query_id(self) -> str:
        import uuid
        return f"q_{uuid.uuid4().hex[:12]}"

    async def close(self):
        await self.retriever.close()
