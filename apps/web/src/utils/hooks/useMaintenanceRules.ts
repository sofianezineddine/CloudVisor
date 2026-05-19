import { MaintenanceRule } from "@/app/aiops/maintenance/model";
import useSWR, { SWRConfiguration } from "swr";
import { useApi } from "@/shared/lib/hooks/useApi";

export const useMaintenanceRules = (
  options: SWRConfiguration = {
    revalidateOnFocus: false,
  }
) => {
  const api = useApi();

  return useSWR<MaintenanceRule[]>(
    api.isReady() ? "/aiops/maintenance" : null,
    (url) => api.get(url),
    options
  );
};
