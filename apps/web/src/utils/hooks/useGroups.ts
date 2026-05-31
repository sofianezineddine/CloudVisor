import { Group } from "@/app/aiops/settings/models";
import { SWRConfiguration } from "swr";
import useSWRImmutable from "swr/immutable";
import { useApi } from "@/shared/lib/hooks/useApi";

export const useGroups = (options: SWRConfiguration = {}) => {
  const api = useApi();

  const swrValue = useSWRImmutable<Group[]>(
    api.isReady() ? "/auth/groups" : null,
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
