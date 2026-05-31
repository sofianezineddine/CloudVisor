import { MappingRule } from "@/app/aiops/mapping/models";
import useSWR, { SWRConfiguration } from "swr";
import { useApi } from "@/shared/lib/hooks/useApi";

export const useMappings = (
  options: SWRConfiguration = {
    revalidateOnFocus: false,
  }
) => {
  const api = useApi();

  const swrValue = useSWR<MappingRule[]>(
    api.isReady() ? "/mapping" : null,
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

export const useMappingRule = (
  id: number | null,
  options: SWRConfiguration = {}
) => {
  const api = useApi();
  const swrValue = useSWR<MappingRule>(
    api.isReady() && id !== null ? `/mapping/${id}` : null,
    (url) => api.get(url),
    options
  );

  // Return as-is for single item fetches
  return swrValue;
};
