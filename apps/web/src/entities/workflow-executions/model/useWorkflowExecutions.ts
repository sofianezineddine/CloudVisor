import { AlertToWorkflowExecution } from "@/entities/alerts/model";
import useSWR, { SWRConfiguration } from "swr";
import { useApi } from "@/shared/lib/hooks/useApi";

/**
 * @deprecated Use useWorkflowExecutionsV2 instead.
 */
export const useWorkflowExecutions = (
  options: SWRConfiguration = {
    revalidateOnFocus: false,
  }
) => {
  const api = useApi();

  const swrValue = useSWR<AlertToWorkflowExecution[]>(
    api.isReady() ? "/workflows/executions" : null,
    (url) => api.get(url),
    options
  );

  // Provide safe default when data is undefined
  const safeData = swrValue.data ?? [];

  return {
    ...swrValue,
    data: safeData,
  };
};
