import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { BuiltInAgent } from "@copilotkit/runtime/v2";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { NextRequest } from "next/server";

function createRuntime() {
  const apiKey =
    process.env.OPEN_AI_API_KEY ||
    process.env.OPENAI_API_KEY ||
    process.env.OPENROUTER_API_KEY ||
    "";

  const baseURL =
    process.env.OPENAI_BASE_URL ||
    process.env.OPENROUTER_SITE_URL ||
    "https://openrouter.ai/api/v1";

  const modelName =
    process.env.OPENAI_MODEL_NAME ||
    process.env.COPILOT_OPENROUTER_MODEL ||
    "meta-llama/llama-3.3-70b-instruct:free";

  const provider = createOpenAICompatible({ name: "nvidia", apiKey, baseURL });

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
