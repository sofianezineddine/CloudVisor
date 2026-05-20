'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { keepApi } from '@/lib/api/keep';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AIOpsProvider {
  id: string;
  type: string;
  name: string;
  status: 'connected' | 'disconnected' | 'not_configured';
  config?: Record<string, unknown>;
  poll_interval_seconds?: number;
  last_sync?: string;
  created_at: string;
}

export interface ProviderTestResult {
  success: boolean;
  message: string;
}

// ─── Query key factory ────────────────────────────────────────────────────────

export const aiopsProviderKeys = {
  all: () => ['aiops', 'providers'] as const,
  lists: () => [...aiopsProviderKeys.all(), 'list'] as const,
  list: () => [...aiopsProviderKeys.lists()] as const,
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useAIOpsProviders() {
  return useQuery({
    queryKey: aiopsProviderKeys.list(),
    queryFn: async () => {
      const { data } = await keepApi.get<{
        providers: unknown[];
        installed_providers: AIOpsProvider[];
        linked_providers: AIOpsProvider[];
        is_localhost: boolean;
      }>('/providers');
      return [...data.installed_providers, ...data.linked_providers];
    },
    staleTime: 30_000,
  });
}

export function useInstallProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ type, config }: { type: string; config: Record<string, unknown> }) => {
      const { data } = await keepApi.post<{ data: AIOpsProvider }>('/providers/install', {
        provider_type: type,
        provider_id: type,
        provider_name: (config.name as string) || type,
        ...config,
      });
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiopsProviderKeys.all() });
    },
  });
}

export function useTestProvider() {
  return useMutation({
    mutationFn: async ({ id }: { id: string }) => {
      const { data } = await keepApi.post<{ data: ProviderTestResult }>(`/providers/${id}/scopes`);
      return data.data;
    },
  });
}

export function useDeleteProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ type, id }: { type: string; id: string }) => {
      await keepApi.delete(`/providers/${type}/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiopsProviderKeys.all() });
    },
  });
}
