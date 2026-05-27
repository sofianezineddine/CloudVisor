import { ExclamationCircleIcon, ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import { Card, Callout } from "@tremor/react";
import dynamic from "next/dynamic";
import { Suspense } from "react";
import { EmptyBuilderState } from "./empty-builder-state";
import { useProviders } from "@/utils/hooks/useProviders";
import { KeepLoader } from "@/shared/ui";
import clsx from "clsx";

const Builder = dynamic(
  () => import("./workflow-builder").then((mod) => mod.WorkflowBuilder),
  {
    ssr: false, // Prevents server-side rendering
  }
);

interface Props {
  loadedYamlFileContents: string | null;
  workflowRaw?: string;
  workflowId?: string;
  standalone?: boolean;
}

export function WorkflowBuilderCard({
  loadedYamlFileContents,
  workflowRaw,
  workflowId,
  standalone = false,
}: Props) {
  const {
    data: { providers, installed_providers: installedProviders } = {},
    error,
    isLoading,
  } = useProviders();

  // Handle case where API returns error (e.g., auth required) or data is malformed
  const safeProviders = providers || [];
  const safeInstalledProviders = installedProviders || [];

  const cardClassName = clsx(
    "p-0 overflow-hidden",
    standalone
      ? "h-[calc(100vh-100px)]"
      : "h-full rounded-none border-t border-gray-200 shadow-none ring-0"
  );

  if (isLoading)
    return (
      <Card className={cardClassName}>
        <KeepLoader loadingText="Loading providers..." />
      </Card>
    );

  // If error or no providers, show warning but still allow builder to load
  // This allows testing AI features even when providers API fails
  const hasError = error || !providers;

  if (loadedYamlFileContents == "" && !workflowRaw) {
    return (
      <Card className={cardClassName}>
        <EmptyBuilderState />
      </Card>
    );
  }

  return (
    <Suspense
      fallback={<KeepLoader loadingText="Loading workflow builder..." />}
    >
      <Card className={cardClassName}>
        {hasError && (
          <Callout
            className="m-4"
            title="Providers unavailable"
            icon={ExclamationTriangleIcon}
            color="yellow"
          >
            Could not load providers. AI features may still work, but provider actions will be limited.
          </Callout>
        )}
        <Builder
          providers={safeProviders}
          installedProviders={safeInstalledProviders}
          loadedYamlFileContents={loadedYamlFileContents}
          workflowRaw={workflowRaw}
          workflowId={workflowId}
        />
      </Card>
    </Suspense>
  );
}
