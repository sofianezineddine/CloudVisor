import { useCallback, useEffect, useMemo, useState } from "react";
import { Provider } from "@/shared/api/providers";
import {
  DefinitionV2,
  IncidentEvent,
  ToolboxConfiguration,
  V2ActionStep,
  V2Step,
  V2StepCondition,
  V2StepStep,
  V2StepTrigger,
} from "@/entities/workflows/model/types";
import {
  IncidentEventEnum,
  V2ActionSchema,
  V2StepConditionSchema,
  V2StepStepSchema,
  V2StepTriggerSchema,
} from "@/entities/workflows/model/schema";
import {
  CopilotChat,
  CopilotKitCSSProperties,
  useCopilotChatSuggestions,
} from "@copilotkit/react-ui";
import { useWorkflowStore } from "@/entities/workflows";
import {
  useCopilotAction,
  useCopilotChat,
  useCopilotReadable,
} from "@copilotkit/react-core";
import { Button } from "@/components/ui";
import { GENERAL_INSTRUCTIONS } from "@/features/workflows/ai-assistant/lib/constants";
import { showSuccessToast } from "@/shared/ui/utils/showSuccessToast";
import { AddTriggerUI } from "./AddTriggerUI";
import { SuggestionResult } from "./SuggestionStatus";
import { AddStepUI } from "./AddStepUI";
import { useAvailableAlertFields } from "@/entities/alerts/model";
import {
  getErrorMessage,
  getWorkflowSummaryForCopilot,
} from "@/features/workflows/ai-assistant/lib/utils";
import { AddTriggerOrStepSkeleton } from "./AddTriggerOrStepSkeleton";
import { foreachTemplate, getTriggerTemplate } from "../../builder/lib/utils";
import { capture } from "@/shared/lib/capture";
import { useConfig } from "@/utils/hooks/useConfig";
import "@copilotkit/react-ui/styles.css";
import "./chat.css";

export interface WorkflowBuilderChatProps {
  definition: DefinitionV2;
  installedProviders: Provider[];
}

export function WorkflowBuilderChat({
  definition,
  installedProviders,
}: WorkflowBuilderChatProps) {
  const { data: config } = useConfig();
  const {
    nodes,
    edges,
    toolboxConfiguration,
    selectedEdge,
    selectedNode,
    deleteNodes,
    validationErrors,
    v2Properties: properties,
    updateV2Properties: setProperties,
  } = useWorkflowStore();

  const steps = useMemo(() => {
    if (!toolboxConfiguration || !toolboxConfiguration.groups) {
      return [];
    }
    const result = [];
    for (const group of toolboxConfiguration.groups) {
      if (group.name !== "Triggers") {
        // Type guard to filter out triggers
        const nonTriggerSteps = group.steps.filter(
          (step): step is Omit<V2Step, "id"> => step.componentType !== "trigger"
        );
        result.push(...nonTriggerSteps);
      }
    }
    return result;
  }, [toolboxConfiguration]);

  const workflowSummary = useMemo(() => {
    return getWorkflowSummaryForCopilot(nodes, edges);
  }, [nodes, edges]);

  useCopilotReadable(
    {
      description: "Current workflow",
      value: workflowSummary,
    },
    [workflowSummary]
  );

  useCopilotReadable(
    {
      description: "Installed providers",
      value: installedProviders,
      convert: (description, installedProviders: Provider[]) => {
        if (!installedProviders || !Array.isArray(installedProviders)) {
          return "";
        }
        return installedProviders
          .map((p) => `${p.type}, id: ${p.id}`)
          .join(", ");
      },
    },
    [installedProviders]
  );

  useCopilotReadable(
    {
      description: "These are steps that you can add to the workflow",
      value: toolboxConfiguration,
      convert: (description, toolboxConfiguration: ToolboxConfiguration) => {
        const result: string[] = [];
        toolboxConfiguration?.groups?.forEach((group) => {
          if (!group.steps || group.steps.length === 0) {
            return;
          }
          result.push(
            `==== ${group.name}, componentType: ${group.steps[0]?.componentType} ====`
          );
          group.steps.forEach((step) => {
            result.push(
              `${step.type}, properties: ${JSON.stringify(step.properties)}`
            );
          });
        });
        return result.join("\n");
      },
    },
    [steps]
  );

  useCopilotReadable(
    {
      description: "Selected node id",
      value: selectedNode,
    },
    [selectedNode]
  );

  useCopilotReadable(
    {
      description: "Validation errors",
      value: validationErrors,
    },
    [validationErrors]
  );

  // Explicit node list so the LLM knows exact IDs to use for removeStepNode
  const removableNodesSummary = useMemo(() => {
    if (!nodes || !Array.isArray(nodes)) return "No nodes in workflow yet.";
    const removable = nodes.filter(
      (n) =>
        !["start", "end", "trigger_start", "trigger_end"].includes(n.id) &&
        !n.id.includes("__empty") &&
        !n.id.includes("__end")
    );
    if (removable.length === 0) return "No nodes in workflow yet.";
    return removable
      .map((n) => `id="${n.id}" type="${n.data?.type ?? ""}" name="${n.data?.name ?? ""}" componentType="${n.data?.componentType ?? ""}"`)
      .join("\n");
  }, [nodes]);

  useCopilotReadable(
    {
      description: "Current workflow nodes — use these exact IDs when calling removeStepNode or removeTriggerNode",
      value: removableNodesSummary,
    },
    [removableNodesSummary]
  );

  useCopilotChatSuggestions(
    {
      instructions:
        "Suggest the most relevant next actions. E.g. if workflow is empty ask what workflow user is trying to build, if workflow already has some steps, suggest either to explain or add a new step. If some step is selected, suggest to explain it or help to configure it. If there are validation errors, suggest to fix them. If you waiting for user to accept or reject the suggestion, suggest relevant short answers.",
      minSuggestions: 1,
      maxSuggestions: 3,
    },
    [nodes, steps, selectedNode]
  );

  const { setMessages } = useCopilotChat();

  useCopilotAction({
    name: "changeWorkflowName",
    description: "Change the name of the workflow",
    parameters: [
      {
        name: "name",
        description: "The new name of the workflow",
        type: "string",
        required: true,
      },
    ],
    handler: ({ name }: { name: string }) => {
      setProperties({ ...properties, name });
      showSuccessToast("Workflow name updated");
    },
  });

  useCopilotAction({
    name: "changeWorkflowDescription",
    description: "Change the description of the workflow",
    parameters: [
      {
        name: "description",
        description: "The new description of the workflow",
        type: "string",
        required: true,
      },
    ],
    handler: ({ description }: { description: string }) => {
      setProperties({ ...properties, description });
      showSuccessToast("Workflow description updated");
    },
  });

  useCopilotAction({
    name: "removeStepNode",
    description: "Remove a step or action from the workflow. Use the node id shown in the workflow canvas (e.g. 'slack-action', 'send-email'). If unsure of the exact id, use the step type (e.g. 'action-slack') or name.",
    parameters: [
      {
        name: "stepType",
        description: "The type of step to remove (e.g. 'action-slack', 'action-email')",
        type: "string",
        required: true,
      },
      {
        name: "stepId",
        description: "The id of the step to remove. Use the exact node id from the workflow (visible in the canvas). If unknown, pass the step name or type.",
        type: "string",
        required: true,
      },
    ],
    renderAndWaitForResponse: ({ status, args, respond }) => {
      if (status === "inProgress") {
        return <div>Loading...</div>;
      }

      // Resolve the actual node id — the LLM may pass a name, type, or partial id
      const resolveNodeId = (hint: string): string | null => {
        const currentNodes = nodes;
        // 1. Exact id match
        if (currentNodes.find((n) => n.id === hint)) return hint;
        // 2. Match by data.name
        const byName = currentNodes.find(
          (n) => n.data?.name === hint || n.data?.name?.toLowerCase() === hint.toLowerCase()
        );
        if (byName) return byName.id;
        // 3. Match by data.type (e.g. "action-slack")
        const byType = currentNodes.find(
          (n) => n.data?.type === hint || n.data?.type?.toLowerCase() === hint.toLowerCase()
        );
        if (byType) return byType.id;
        // 4. Partial match on id (e.g. "slack" matches "slack-action")
        const byPartialId = currentNodes.find(
          (n) =>
            !["start", "end", "trigger_start", "trigger_end"].includes(n.id) &&
            (n.id.toLowerCase().includes(hint.toLowerCase()) ||
              hint.toLowerCase().includes(n.id.toLowerCase()))
        );
        if (byPartialId) return byPartialId.id;
        // 5. Partial match on type (e.g. "slack" matches "action-slack")
        const byPartialType = currentNodes.find(
          (n) =>
            n.data?.type?.toLowerCase().includes(hint.toLowerCase()) ||
            hint.toLowerCase().includes((n.data?.type ?? "").toLowerCase().replace("action-", "").replace("step-", ""))
        );
        if (byPartialType) return byPartialType.id;
        return null;
      };

      const resolvedId = resolveNodeId(args.stepId) ?? resolveNodeId(args.stepType);

      if (!resolvedId) {
        respond?.("Step removal failed: could not find a node matching '" + args.stepId + "'");
        return <p>Step removal failed: no node found matching &quot;{args.stepId}&quot;</p>;
      }

      if (confirm(`Are you sure you want to remove the "${resolvedId}" step?`)) {
        try {
          const deletedNodeIds = deleteNodes(resolvedId);
          if (deletedNodeIds.length > 0) {
            respond?.("Step removed");
            return <p>Step {resolvedId} removed</p>;
          } else {
            respond?.("Step removal failed");
            return <p>Step removal failed</p>;
          }
        } catch (e) {
          respond?.({
            status: "error",
            message: getErrorMessage(e, "Step removal failed"),
          });
          return <p>Step removal failed</p>;
        }
      } else {
        respond?.("User cancelled the step removal");
        return <p>Step removal cancelled</p>;
      }
    },
  });

  useCopilotAction({
    name: "removeTriggerNode",
    description: "Remove a trigger from the workflow",
    parameters: [
      {
        name: "triggerNodeId",
        description:
          "The id of the trigger to remove. One of 'manual', 'alert', 'incident', 'interval'",
        type: "string",
        required: true,
      },
    ],
    renderAndWaitForResponse: ({ status, args, respond }) => {
      if (status === "inProgress") {
        return <div>Loading...</div>;
      }
      const triggerNodeId = args.triggerNodeId;

      // TODO: nice UI for this
      if (
        confirm(`Are you sure you want to remove ${triggerNodeId} trigger?`)
      ) {
        try {
          const deletedNodeIds = deleteNodes(triggerNodeId);
          if (deletedNodeIds.length > 0) {
            respond?.("Trigger removed");
            return <p>Trigger {triggerNodeId} removed</p>;
          } else {
            respond?.("Trigger removal failed");
            return <p>Trigger removal failed</p>;
          }
        } catch (e) {
          respond?.({
            status: "error",
            message: getErrorMessage(e, "Trigger removal failed"),
          });
          return <p>Trigger removal failed</p>;
        }
      } else {
        respond?.("User cancelled the trigger removal");
        return <p>Trigger removal cancelled</p>;
      }
    },
  });

  /**
   * Get the definition of a trigger
   * @param triggerType - The type of trigger
   * @param triggerProperties - The properties of the trigger
   * @returns The definition of the trigger
   * @throws ZodError if the trigger type is not supported or triggerProperties are invalid
   */
  function getTriggerDefinitionFromCopilotAction(
    triggerType: string,
    triggerProperties: V2StepTrigger["properties"]
  ) {
    const triggerTemplate = getTriggerTemplate(triggerType);

    const triggerDefinition = {
      ...triggerTemplate,
      properties: {
        ...triggerTemplate.properties,
        ...triggerProperties,
      },
    };
    return V2StepTriggerSchema.parse(triggerDefinition);
  }

  useCopilotAction({
    name: "addManualTrigger",
    description:
      "Add a manual trigger to the workflow. There could be only one manual trigger in the workflow.",
    parameters: [],
    renderAndWaitForResponse: (args) => {
      if (args.status === "inProgress") {
        return <AddTriggerOrStepSkeleton />;
      }

      const trigger = getTriggerDefinitionFromCopilotAction("manual", {
        manual: "true",
      });

      if (args.status === "complete" && "result" in args) {
        return (
          <AddTriggerUI
            status="complete"
            trigger={trigger}
            respond={undefined}
            result={args.result as SuggestionResult}
          />
        );
      }

      return (
        <AddTriggerUI
          status="executing"
          trigger={trigger}
          respond={args.respond}
          result={undefined}
          autoConfirm={true}
        />
      );
    },
  });

  useCopilotAction({
    name: "addAlertTrigger",
    description:
      "Add an alert trigger to the workflow. There could be only one alert trigger in the workflow, if you need more combine them into one alert trigger, using the CEL expression.",
    parameters: [
      {
        name: "alertFilters",
        description:
          "The CEL expression to filter alerts. For all alerts, use empty string ''. For critical alerts use: alert.severity == 'critical'",
        type: "string",
      },
    ],
    renderAndWaitForResponse: (args) => {
      const status = args.status as string;
      const alertFilters = (args.args?.alertFilters as string) || "";

      const properties = {
        alert: {
          cel: alertFilters,
        },
      };

      const trigger = getTriggerDefinitionFromCopilotAction(
        "alert",
        properties
      );

      if (args.status === "complete" && "result" in args) {
        return (
          <AddTriggerUI
            status="complete"
            trigger={trigger}
            respond={undefined}
            result={args.result as SuggestionResult}
          />
        );
      }

      return (
        <AddTriggerUI
          status="executing"
          trigger={trigger}
          respond={args.respond}
          result={undefined}
          autoConfirm={true}
        />
      );
    },
  });

  const { fields } = useAvailableAlertFields();
  const possibleAlertProperties = useMemo(() => {
    if (!fields || fields.length === 0) {
      return ["source", "severity", "status", "message", "timestamp"];
    }
    return fields?.map((field) => field.split(".").pop());
  }, [fields]);

  useCopilotReadable({
    description: "Possible alert properties",
    value: possibleAlertProperties,
  });

  useCopilotAction({
    name: "addAlertTrigger",
    description:
      "Add an alert trigger to the workflow. There could be only one alert trigger in the workflow, if you need more combine them into one alert trigger, using the CEL expression.",
    parameters: [
      {
        name: "alertFilters",
        description: "The filters of the alert trigger as a CEL expression",
        type: "string",
        required: true,
        attributes: [
          {
            name: "value",
            description: "The value of the alert filter in CEL expression",
            type: "string",
            required: true,
          },
        ],
      },
    ],
    renderAndWaitForResponse: (args) => {
      if (args.status === "inProgress") {
        return <AddTriggerOrStepSkeleton />;
      }

      const properties = {
        cel: args.args.alertFilters,
      };

      const trigger = getTriggerDefinitionFromCopilotAction(
        "alert",
        properties
      );

      if (args.status === "complete" && "result" in args) {
        return (
          <AddTriggerUI
            status="complete"
            trigger={trigger}
            respond={undefined}
            result={args.result as SuggestionResult}
          />
        );
      }

      return (
        <AddTriggerUI
          status="executing"
          trigger={trigger}
          respond={args.respond}
          result={undefined}
        />
      );
    },
  });

  useCopilotAction({
    name: "addIntervalTrigger",
    description:
      "Add an interval trigger to the workflow. There could be only one interval trigger in the workflow.",
    parameters: [
      {
        name: "interval",
        description: "The interval of the interval trigger in seconds",
        type: "number",
        required: true,
      },
    ],
    renderAndWaitForResponse: (args) => {
      if (args.status === "inProgress") {
        return <AddTriggerOrStepSkeleton />;
      }

      const properties = {
        interval: args.args.interval,
      };

      const trigger = getTriggerDefinitionFromCopilotAction(
        "interval",
        properties
      );

      if (args.status === "complete" && "result" in args) {
        return (
          <AddTriggerUI
            status="complete"
            trigger={trigger}
            respond={undefined}
            result={args.result as SuggestionResult}
          />
        );
      }

      return (
        <AddTriggerUI
          status="executing"
          trigger={trigger}
          respond={args.respond}
          result={undefined}
          autoConfirm={true}
        />
      );
    },
  });

  useCopilotAction({
    name: "addIncidentTrigger",
    description:
      "Add an incident trigger to the workflow. There could be only one incident trigger in the workflow.",
    parameters: [
      {
        name: "incidentEvents",
        description: `The events of the incident trigger, one of: ${IncidentEventEnum.options
          .map((o) => `"${o}"`)
          .join(", ")}`,
        type: "string[]",
        required: true,
      },
    ],
    renderAndWaitForResponse: (args) => {
      if (args.status === "inProgress") {
        return <AddTriggerOrStepSkeleton />;
      }

      // Normalize incidentEvents to always be an array (handle string input from AI)
      const incidentEvents = args.args.incidentEvents;
      const normalizedEvents = Array.isArray(incidentEvents)
        ? incidentEvents
        : typeof incidentEvents === "string"
        ? [incidentEvents]
        : [];

      const properties = {
        incident: {
          events: normalizedEvents as IncidentEvent[],
        },
      };

      const trigger = getTriggerDefinitionFromCopilotAction(
        "incident",
        properties
      );

      if (args.status === "complete" && "result" in args) {
        return (
          <AddTriggerUI
            status="complete"
            trigger={trigger}
            respond={undefined}
            result={args.result as SuggestionResult}
          />
        );
      }

      return (
        <AddTriggerUI
          status="executing"
          trigger={trigger}
          respond={args.respond}
          result={undefined}
          autoConfirm={true}
        />
      );
    },
  });

  /**
   * Safely parse a params list that the LLM may send as:
   *  - A real array: [{name:"to", value:"admin@example.com"}, ...]
   *  - A JSON string: '[{"name":"to","value":"admin@example.com"}]'
   *  - A flat object string: '{"to":"admin@example.com"}'
   *  - undefined / null
   */
  function parseParamsList(
    raw: string | { name: string; value: string }[] | undefined | null
  ): { name: string; value: string }[] {
    if (!raw) return [];
    if (Array.isArray(raw)) return raw;
    try {
      const parsed = JSON.parse(raw as string);
      if (Array.isArray(parsed)) return parsed;
      if (parsed && typeof parsed === "object") {
        return Object.entries(parsed).map(([name, value]) => ({
          name,
          value: String(value),
        }));
      }
    } catch {
      // Not valid JSON — try key=value extraction as last resort
      const pairs: { name: string; value: string }[] = [];
      const matches = (raw as string).matchAll(/["']?(\w+)["']?\s*[:=]\s*["']?([^"',}\]]+)["']?/g);
      for (const m of matches) {
        pairs.push({ name: m[1], value: m[2].trim() });
      }
      if (pairs.length > 0) return pairs;
    }
    return [];
  }

  function getActionStepFromCopilotAction(args: {
    actionId: string;
    actionType: string;
    actionName: string;
    providerName: string;
    withActionParams: string | { name: string; value: string }[];
  }) {
    // Normalise the action type — ensure it starts with "action-"
    const actionType = args.actionType.startsWith("action-")
      ? args.actionType
      : `action-${args.actionType}`;

    // Try to find an installed-provider template first
    const template = steps.find(
      (step): step is V2ActionStep =>
        step.type === actionType &&
        step.componentType === "task" &&
        "actionParams" in step.properties
    );

    // Safely parse params — the LLM sometimes sends a JSON string instead of an array
    const parsedParams = parseParamsList(args.withActionParams);

    // Build the `with` map from the params the LLM provided
    const withParams = parsedParams.reduce(
      (acc, param) => {
        if (param?.name) acc[param.name] = param.value ?? "";
        return acc;
      },
      {} as Record<string, string>
    );

    // If no installed template exists, build a generic action so the workflow
    // can still be constructed. The user will need to configure the provider
    // separately, but the node will appear in the canvas.
    const action: V2ActionStep = template
      ? {
          ...template,
          id: args.actionId,
          name: args.actionName,
          properties: {
            ...template.properties,
            with: withParams,
          },
        }
      : {
          id: args.actionId,
          name: args.actionName,
          componentType: "task",
          type: actionType,
          properties: {
            actionParams: Object.keys(withParams),
            with: withParams,
          },
        };

    return V2ActionSchema.parse(action);
  }

  useCopilotAction({
    name: "addAction",
    description:
      "Add an action to the workflow. Actions send notifications/data to a provider (email, Slack, Jira, webhook, etc.). NEVER use addStep for notifications — always use addAction.",
    parameters: [
      {
        name: "withActionParams",
        description: `JSON string of action parameters array. Format: '[{"name":"to","value":"admin@example.com"},{"name":"subject","value":"Alert: {{ alert.name }}"}]'. Always use this exact JSON array string format.`,
        type: "string",
        required: true,
      },
      {
        name: "actionId",
        description: "The id of the action to add",
        type: "string",
        required: true,
      },
      {
        name: "actionType",
        description: "The type of the action. Must start with 'action-'. Examples: 'action-email', 'action-slack', 'action-jira', 'action-pagerduty', 'action-webhook', 'action-teams', 'action-smtp'",
        type: "string",
        required: true,
      },
      {
        name: "actionName",
        description: "The kebab-case name of the action to add",
        type: "string",
        required: true,
      },
      {
        name: "providerName",
        description: "The name of the provider to add",
        type: "string",
        required: true,
      },
      {
        name: "addBeforeNodeId",
        description: `The id of the node to add the action before. For workflows with no steps, use 'end'. Cannot be a trigger node. For condition branches: use '__empty_true' or '__empty_false' suffix.`,
        type: "string",
        required: true,
      },
    ],
    renderAndWaitForResponse: ({ status, args, respond, result }) => {
      if (status === "inProgress") {
        return <AddTriggerOrStepSkeleton />;
      }
      let action: ReturnType<typeof getActionStepFromCopilotAction>;
      try {
        action = getActionStepFromCopilotAction(args);
      } catch (e) {
        respond?.({ status: "error", error: getErrorMessage(e, "Action definition is invalid") });
        return <div>Action definition is invalid: {getErrorMessage(e)}</div>;
      }

      if (status === "complete") {
        return (
          <AddStepUI
            status={status}
            step={action}
            addBeforeNodeId={args.addBeforeNodeId}
            result={result}
            respond={undefined}
          />
        );
      }

      return (
        <AddStepUI
          status={status}
          step={action}
          addBeforeNodeId={args.addBeforeNodeId}
          result={undefined}
          respond={respond}
          autoConfirm={true}
        />
      );
    },
  });

  function getStepStepFromCopilotAction(args: {
    stepId: string;
    stepType: string;
    stepName: string;
    providerName: string;
    withStepParams: string | { name: string; value: string }[];
  }) {
    // Normalise the step type — ensure it starts with "step-"
    const stepType = args.stepType.startsWith("step-")
      ? args.stepType
      : `step-${args.stepType}`;

    const template = steps.find(
      (step): step is V2StepStep => step.type === stepType
    );

    // Safely parse params — the LLM sometimes sends a JSON string instead of an array
    const parsedParams = parseParamsList(args.withStepParams);

    const withParams = parsedParams.reduce(
      (acc, param) => {
        if (param?.name) acc[param.name] = param.value ?? "";
        return acc;
      },
      {} as Record<string, string>
    );

    // Build a generic step when no installed template exists
    const step: V2StepStep = template
      ? {
          ...template,
          id: args.stepId,
          name: args.stepName,
          properties: {
            ...template.properties,
            with: withParams,
          },
        }
      : {
          id: args.stepId,
          name: args.stepName,
          componentType: "task",
          type: stepType,
          properties: {
            stepParams: Object.keys(withParams),
            with: withParams,
          },
        };

    return V2StepStepSchema.parse(step);
  }

  useCopilotAction({
    name: "addStep",
    description:
      "Add a step to the workflow. Steps FETCH data from a provider (query/read). Use addAction instead for sending notifications, emails, Slack messages, or any write/notify operation.",
    parameters: [
      {
        name: "withStepParams",
        description: `JSON string of step parameters array. Format: '[{"name":"query","value":"SELECT * FROM alerts"},{"name":"host","value":"db.example.com"}]'. Always use this exact JSON array string format.`,
        type: "string",
        required: true,
      },
      {
        name: "stepId",
        description: "The id of the step to add",
        type: "string",
        required: true,
      },
      {
        name: "stepType",
        description: "The type of the step to add. Must start with 'step-'. Examples: 'step-datadog', 'step-prometheus', 'step-sql', 'step-http'",
        type: "string",
        required: true,
      },
      {
        name: "stepName",
        description: "The kebab-case name of the step to add",
        type: "string",
        required: true,
      },
      {
        name: "providerName",
        description: "The name of the provider to add",
        type: "string",
        required: true,
      },
      {
        name: "addBeforeNodeId",
        description: `The id of the node to add the step before. For workflows with no steps, use 'end'. Cannot be a trigger node. For condition branches: use '__empty_true' or '__empty_false' suffix.`,
        type: "string",
        required: true,
      },
    ],
    renderAndWaitForResponse: ({ status, args, respond, result }) => {
      if (status === "inProgress") {
        return <AddTriggerOrStepSkeleton />;
      }
      let step: ReturnType<typeof getStepStepFromCopilotAction>;
      try {
        step = getStepStepFromCopilotAction(args);
      } catch (e) {
        respond?.({ status: "error", error: getErrorMessage(e, "Step definition is invalid") });
        return <div>Step definition is invalid: {getErrorMessage(e)}</div>;
      }

      if (status === "complete") {
        return (
          <AddStepUI
            status={status}
            step={step}
            addBeforeNodeId={args.addBeforeNodeId}
            result={result}
            respond={undefined}
          />
        );
      }

      return (
        <AddStepUI
          status={status}
          step={step}
          result={undefined}
          addBeforeNodeId={args.addBeforeNodeId}
          respond={respond}
          autoConfirm={true}
        />
      );
    },
  });

  function getConditionStepFromCopilotAction(args: {
    conditionId: string;
    conditionType: string;
    conditionName: string;
    conditionValue: string;
    compareToValue: string;
  }) {
    const template = steps.find(
      (step): step is V2StepCondition => step.type === args.conditionType
    );
    if (!template) {
      throw new Error("Condition type is invalid");
    }

    let condition: V2StepCondition | null = null;

    if (template.type === "condition-assert") {
      condition = {
        ...template,
        id: args.conditionId,
        name: args.conditionName,
        properties: {
          ...template.properties,
          assert: `${args.conditionValue} == ${args.compareToValue}`,
        },
      };
    } else if (template.type === "condition-threshold") {
      condition = {
        ...template,
        id: args.conditionId,
        name: args.conditionName,
        properties: {
          ...template.properties,
          value: args.conditionValue,
          compare_to: args.compareToValue,
        },
      };
    }

    return V2StepConditionSchema.parse(condition);
  }

  useCopilotAction({
    name: "addCondition",
    description: "Add a condition to the workflow.",
    parameters: [
      {
        name: "conditionId",
        description: "The id of the condition to add",
        type: "string",
        required: true,
      },
      {
        name: "conditionType",
        description:
          "The type of the condition to add. One of: 'condition-assert', 'condition-threshold'",
        type: "string",
        required: true,
      },
      {
        name: "conditionName",
        description: "The kebab-case name of the condition to add",
        type: "string",
        required: true,
      },
      {
        name: "conditionValue",
        description: "The value of the condition to add",
        type: "string",
        required: true,
      },
      {
        name: "compareToValue",
        description: "The value to compare the condition to",
        type: "string",
        required: true,
      },
      {
        name: "addBeforeNodeId",
        description: `The id of the node to add the condition before. For workflows with no steps, should be 'end'. Cannot be a node with componentType: 'trigger'. If adding to a condition branch, search for node id:
- Must end with '__empty_true' for true branch
- Must end with '__empty_false' for false branch
Example: 'node_123__empty_true'`,
        type: "string",
        required: true,
      },
    ],
    renderAndWaitForResponse: ({ status, args, respond, result }) => {
      if (status === "inProgress") {
        return <AddTriggerOrStepSkeleton />;
      }
      try {
        const condition = getConditionStepFromCopilotAction(args);
        if (!condition) {
          respond?.({
            status: "error",
            message: "Condition definition is invalid",
          });
          return <div>Condition definition is invalid</div>;
        }
        if (status === "complete") {
          return (
            <AddStepUI
              status={status}
              step={condition}
              result={result}
              addBeforeNodeId={args.addBeforeNodeId}
              respond={respond}
            />
          );
        }
        return (
          <AddStepUI
            status={status}
            step={condition}
            result={undefined}
            addBeforeNodeId={args.addBeforeNodeId}
            respond={respond}
            autoConfirm={true}
          />
        );
      } catch (e: any) {
        respond?.({ status: "error", message: getErrorMessage(e) });
        return <div>Failed to add condition {e?.message}</div>;
      }
    },
  });

  function getForeachStepFromCopilotAction(args: {
    foreachName: string;
    value: string;
    addBeforeNodeId: string;
  }) {
    return {
      ...foreachTemplate,
      name: args.foreachName,
      id: `foreach_${args.foreachName}`,
      properties: {
        ...foreachTemplate.properties,
        value: args.value,
      },
    };
  }

  useCopilotAction({
    name: "addForeach",
    description: "Add a foreach loop to the workflow.",
    parameters: [
      {
        name: "foreachName",
        description: "The kebab-case name of the foreach to add",
        type: "string",
        required: true,
      },
      {
        name: "value",
        description:
          "The value to iterate over. Could refer to results from previous steps: '{{ steps.<stepId>.results }}'.",
        type: "string",
        required: true,
      },
      {
        name: "addBeforeNodeId",
        description: `The id of the node to add the foreach before. For workflows with no steps, should be 'end'. Cannot be a node with componentType: 'trigger'. If adding to a condition branch, search for node id:
- Must end with '__empty_true' for true branch
- Must end with '__empty_false' for false branch
Example: 'node_123__empty_true'`,
        type: "string",
        required: true,
      },
    ],
    renderAndWaitForResponse: ({ status, args, respond, result }) => {
      if (status === "inProgress") {
        return <AddTriggerOrStepSkeleton />;
      }
      const foreach = getForeachStepFromCopilotAction(args);

      if (status === "complete") {
        return (
          <AddStepUI
            status={status}
            step={foreach}
            addBeforeNodeId={args.addBeforeNodeId}
            result={result}
            respond={undefined}
          />
        );
      }
      return (
        <AddStepUI
          status={status}
          step={foreach}
          addBeforeNodeId={args.addBeforeNodeId}
          result={undefined}
          respond={respond}
          autoConfirm={true}
        />
      );
    },
  });

  // const testStep = useTestStep();

  // TODO: add this action
  // useCopilotAction({
  //   name: "testRunStep",
  //   description: "Test run a step with given parameters",
  //   parameters: [
  //     {
  //       name: "providerId",
  //       description: "The id of the provider to test",
  //       type: "string",
  //       required: true,
  //     },
  //     {
  //       name: "providerType",
  //       description: "The type of the provider to test",
  //       type: "string",
  //       required: true,
  //     },
  //     {
  //       name: "stepType",
  //       description: "The type of the step to test: 'action' or 'step'",
  //       type: "string",
  //       required: true,
  //     },
  //     {
  //       name: "stepParams",
  //       description: "The parameters of the step to test",
  //       type: "object[]",
  //       required: true,
  //     },
  //   ],
  //   render: ({
  //     status,
  //     args: { providerId, stepParams, stepType, providerType },
  //     result,
  //   }) => {
  //     if (status === "inProgress") {
  //       return <div>Loading...</div>;
  //     }
  //     const step = steps?.find((step: any) => step.type === stepType) as V2Step;
  //     if (!step) {
  //       return <div>Step not found</div>;
  //     }
  //     const method = stepType === "action" ? "_notify" : "_query";
  //     try {
  //       const result = await testStep(
  //         {
  //           provider_id: providerId,
  //           provider_type: providerType,
  //         },
  //         method,
  //         stepParams
  //       );
  //       return <div>{JSON.stringify(result, null, 2)}</div>;
  //     } catch (e) {
  //       return <div>Failed to test step: {e.toString()}</div>;
  //     }
  //   },
  // });

  const handleSubmitMessage = useCallback((_message: string) => {
    capture("workflow_chat_message_submitted");
  }, []);

  const [debugInfoVisible, setDebugInfoVisible] = useState(false);

  // NOTE: GENERAL_INSTRUCTIONS is already passed as the top-level system prompt
  // via <CopilotKit instructions={GENERAL_INSTRUCTIONS}> in workflow-builder-widget-safe.tsx.
  // Here we only add dynamic, context-specific additions to avoid duplicating the full prompt
  // (duplicate system prompts confuse the LLM and degrade tool-calling reliability).
  const chatInstructions = `
You MUST call the appropriate tool immediately when the user asks to build or modify a workflow.
Do NOT respond with only text when a tool call is needed — call the tool first, then summarize.

When building a complete workflow from a single user request:
1. Call changeWorkflowName with a descriptive name
2. Call changeWorkflowDescription with a brief description
3. Add the trigger (addAlertTrigger / addManualTrigger / addIntervalTrigger / addIncidentTrigger)
4. Add each step/action in sequence

For the addBeforeNodeId parameter: use "end" when the workflow has no steps yet.
`;

  return (
    // using 'workflow-chat' class to apply styles only to that chat component
    <div
      className="flex flex-col h-full max-h-screen grow-0 overflow-auto workflow-chat"
      style={
        {
          "--copilot-kit-primary-color":
            "rgb(249 115 22 / var(--tw-bg-opacity))",
        } as CopilotKitCSSProperties
      }
    >
      {/* Debug info */}
      {config?.KEEP_WORKFLOW_DEBUG && (
        <div className="">
          <div className="flex">
            <Button
              variant="secondary"
              size="xs"
              onClick={() => setMessages([])}
            >
              Reset
            </Button>
            <Button
              variant="secondary"
              size="xs"
              onClick={() => setDebugInfoVisible(!debugInfoVisible)}
            >
              {debugInfoVisible ? "Hide definition" : "Show definition"}
            </Button>
          </div>
          {debugInfoVisible && (
            <>
              <pre>{JSON.stringify(definition.value, null, 2)}</pre>
              <pre>selectedNode={JSON.stringify(selectedNode, null, 2)}</pre>
              <pre>selectedEdge={JSON.stringify(selectedEdge, null, 2)}</pre>
            </>
          )}
        </div>
      )}
      <CopilotChat
        instructions={chatInstructions}
        labels={{
          title: "Workflow Builder",
          initial: "What can I help you automate?",
          placeholder:
            "For example: For each alert about CPU > 80%, send a slack message to the channel #alerts",
        }}
        className="h-full flex-1"
        onSubmitMessage={handleSubmitMessage}
      />
    </div>
  );
}
