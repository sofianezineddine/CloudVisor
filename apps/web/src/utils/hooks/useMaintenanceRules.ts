import { MaintenanceRule } from "@/app/aiops/maintenance/model";
import useSWR, { SWRConfiguration } from "swr";
import { useApi } from "@/shared/lib/hooks/useApi";

export const useMaintenanceRules = (
  options: SWRConfiguration = {
    revalidateOnFocus: false,
  }
) => {
  const api = useApi();

  const swrValue = useSWR<MaintenanceRule[]>(
    api.isReady() ? "/maintenance" : null,
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
