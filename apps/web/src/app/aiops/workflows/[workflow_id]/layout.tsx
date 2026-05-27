import { getWorkflowWithRedirectSafe } from "@/shared/api/workflows";
import { WorkflowBreadcrumbs } from "./workflow-breadcrumbs";
import WorkflowDetailHeader from "./workflow-detail-header";

export default async function Layout(props: {
  children: React.ReactNode;
  params: { workflow_id: string };
}) {
  const params = props.params;

  const { children } = props;

  const workflow = await getWorkflowWithRedirectSafe(params.workflow_id);
  return (
    <div className="flex flex-col h-full gap-4">
      <WorkflowBreadcrumbs workflowId={params.workflow_id} />
      <WorkflowDetailHeader
        workflowId={params.workflow_id}
        initialData={workflow}
      />
      <div className="flex-1 flex flex-col">{children}</div>
    </div>
  );
}
