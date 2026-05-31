import { DeduplicationRule } from "@/app/aiops/deduplication/models";
import { SWRConfiguration } from "swr";
import useSWRImmutable from "swr/immutable";
import { useApi } from "@/shared/lib/hooks/useApi";

export const useDeduplicationRules = (options: SWRConfiguration = {}) => {
  const api = useApi();

  const swrValue = useSWRImmutable<DeduplicationRule[]>(
    api.isReady() ? "/deduplications" : null,
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

export const useDeduplicationFields = (options: SWRConfiguration = {}) => {
  const api = useApi();

  const swrValue = useSWRImmutable<Record<string, string[]>>(
    api.isReady() ? "/deduplications/fields" : null,
    (url) => api.get(url),
    options
  );

  // Provide safe default when data is undefined
  const safeData = swrValue.data ?? {};

  return {
    ...swrValue,
    data: safeData,
  };
};
