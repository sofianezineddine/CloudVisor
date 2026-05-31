import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { BuiltInAgent } from "@copilotkit/runtime/v2";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { NextRequest } from "next/server";

/**
 * AI Router Integration
 * 
 * Routes all LLM requests through the CloudVisor AI Router service
 * for unified provider management, rate limiting, and monitoring.
 * 
 * Internal Docker network: http://cv-ai-router:8015
 * API Gateway: /v1/ai/ (for authenticated requests)
 */
function createRuntime() {
  // Use AI Router service - it handles provider selection internally
  const aiRouterURL = process.env.AI_ROUTER_URL || "http://cv-ai-router:8015/v1";
  
  // AI Router uses its own API key configuration from env
  // We pass a dummy key since auth is handled at the service level
  const apiKey = "ai-router-internal";

  // Model selection - AI Router will map to appropriate provider
  // Available models depend on configured providers (openai, openrouter, nvidia)
  const modelName =
    process.env.AI_ROUTER_MODEL ||
    process.env.OPENAI_MODEL_NAME ||
    process.env.COPILOT_OPENROUTER_MODEL ||
    "meta-llama/llama-3.3-70b-instruct:free";

  const provider = createOpenAICompatible({ 
    name: "ai-router", 
    apiKey, 
    baseURL: aiRouterURL 
  });

  const builtInAgent = new BuiltInAgent({
    model: provider(modelName),
    maxSteps: 5,
    forwardSystemMessages: true,
  });

  return new CopilotRuntime({
    agents: { default: builtInAgent },
  });
}

export const POST = async (req: NextRequest) => {
  const runtime = createRuntime();
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};

export const GET = async (req: NextRequest) => {
  const runtime = createRuntime();
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
