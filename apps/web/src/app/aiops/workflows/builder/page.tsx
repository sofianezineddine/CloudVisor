"use client";

import { WorkflowBuilderWidget } from "@/widgets/workflow-builder";

export default function WorkflowBuilderPage() {
  return (
    <WorkflowBuilderWidget
      workflowRaw={undefined}
      workflowId={undefined}
      standalone={true}
    />
  );
}
