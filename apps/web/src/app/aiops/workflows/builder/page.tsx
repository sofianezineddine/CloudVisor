import { WorkflowBuilderWidget } from "@/widgets/workflow-builder";
import { Metadata } from "next";

type PageProps = {
  params: { workflow: string; workflowId: string };
  searchparams: { [key: string]: string | string[] | undefined };
};

export default async function WorkflowBuilderPage(props: PageProps) {
  const params = props.params;
  return (
    <WorkflowBuilderWidget
      workflowRaw={params.workflow}
      workflowId={params.workflowId}
      standalone={true}
    />
  );
}

export const metadata: Metadata = {
  title: "Keep - Workflow Builder",
  description: "Build workflows with a UI builder.",
};
