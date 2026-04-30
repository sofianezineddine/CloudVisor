'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient, { Finding } from '@/lib/api/apiClient';
import { useScopeStore } from '@/stores/scope';

// ─── Query key factory ────────────────────────────────────────────────────────

export const findingKeys = {
  all:    () => ['findings'] as const,
  lists:  () => [...findingKeys.all(), 'list'] as const,
  list:   (params: Record<string, unknown>) => [...findingKeys.lists(), params] as const,
  detail: (id: string) => [...findingKeys.all(), 'detail', id] as const,
  stats:  () => [...findingKeys.all(), 'stats'] as const,
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

export interface FindingsListParams {
  severity?: string;
  status?: string;
  provider?: string;
  account_id?: string;
  region?: string;
  limit?: number;
  offset?: number;
}

export function useFindings(params: FindingsListParams = {}) {
  const accountIds = useScopeStore(s => s.accountIds);
  const scopeAccountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const scopeProvider = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
  const effectiveParams = {
    ...params,
    account_id: params.account_id ?? scopeAccountId,
    provider: !params.account_id && !scopeAccountId ? scopeProvider : undefined,
  };
  return useQuery({
    queryKey: findingKeys.list({ ...effectiveParams, _scope: accountIds } as Record<string, unknown>),
    queryFn: async () => {
      const resp = await apiClient.findings.list(effectiveParams);
      const findings = (resp?.data as any[]) ?? [];
      // Client-side filter to enforce scope isolation
      const scoped = findings.filter(f => {
        if (effectiveParams.account_id) return f.account_id === effectiveParams.account_id;
        if (scopeProvider) return f.provider === scopeProvider;
        return accountIds.includes(f.account_id);
      });
      return { ...resp, data: scoped };
    },
    staleTime: 30_000,
    enabled: accountIds.length > 0,
  });
}

export function useFindingDetail(id: string | null) {
  return useQuery({
    queryKey: findingKeys.detail(id ?? ''),
    queryFn: () => apiClient.findings.get(id!),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useFindingStats() {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const provider = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
  return useQuery({
    queryKey: [...findingKeys.stats(), accountIds],
    queryFn: async () => {
      // Fetch findings scoped to current account/provider and compute stats client-side
      const resp = await apiClient.findings.list({
        limit: 500,
        account_id: accountId,
        provider: !accountId ? provider : undefined,
      });
      const findings = (resp?.data as any[]) ?? [];
      const scoped = findings.filter(f => {
        if (accountId) return f.account_id === accountId;
        if (provider) return f.provider === provider;
        return accountIds.includes(f.account_id);
      });
      const bySeverity: Record<string, number> = {};
      const byStatus: Record<string, number> = {};
      for (const f of scoped) {
        bySeverity[f.severity] = (bySeverity[f.severity] ?? 0) + 1;
        byStatus[f.status] = (byStatus[f.status] ?? 0) + 1;
      }
      return {
        data: { total: scoped.length, by_severity: bySeverity, by_status: byStatus },
      };
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    enabled: accountIds.length > 0,
  });
}

export function useUpdateFinding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { status?: string; assignee_id?: string; note?: string } }) =>
      apiClient.findings.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: findingKeys.all() });
      queryClient.invalidateQueries({ queryKey: findingKeys.detail(id) });
    },
  });
}

export function useSuppressFinding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      apiClient.findings.suppress(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: findingKeys.all() });
    },
  });
}

export function useBulkUpdateFindings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ids, status }: { ids: string[]; status: string }) =>
      apiClient.findings.bulkUpdate(ids, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: findingKeys.all() });
    },
  });
}
