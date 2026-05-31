import { SWRConfiguration } from "swr";
import { ProvidersResponse } from "@/shared/api/providers";
import useSWRImmutable from "swr/immutable";
import { useApi } from "@/shared/lib/hooks/useApi";

export const useProviders = (
  options: SWRConfiguration = { revalidateOnFocus: false }
) => {
  const api = useApi();

  const swrValue = useSWRImmutable<ProvidersResponse>(
    api.isReady() ? "/providers" : null,
    (url) => api.get(url),
    options
  );

  // Provide safe default when data is undefined
  const safeData = swrValue.data ?? { providers: [], installed_providers: [] };

  return {
    ...swrValue,
    data: safeData,
  };
};

export const useProvidersWithHealthCheck = (
  options: SWRConfiguration = { revalidateOnFocus: false }
) => {
  const api = useApi();

  const swrValue = useSWRImmutable<ProvidersResponse>(
    api.isReady() ? "/providers/healthcheck" : null,
    (url) => api.get(url),
    options
  );

  // Provide safe default when data is undefined
  const safeData = swrValue.data ?? { providers: [], installed_providers: [] };

  return {
    ...swrValue,
    data: safeData,
  };
};
