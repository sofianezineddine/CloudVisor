'use client';

import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api/apiClient';
import { connectorAPI } from '@/lib/api/connector';
import { useScopeStore } from '@/stores/scope';

// ─── Query key factory ────────────────────────────────────────────────────────

export const dashboardKeys = {
  all:            () => ['dashboard'] as const,
  stats:          () => [...dashboardKeys.all(), 'stats'] as const,
  recentFindings: () => [...dashboardKeys.all(), 'recent-findings'] as const,
  accounts:       () => [...dashboardKeys.all(), 'accounts'] as const,
  resources:      () => [...dashboardKeys.all(), 'resources'] as const,
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useDashboardStats() {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const provider = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
  return useQuery({
    queryKey: [...dashboardKeys.stats(), accountIds],
    queryFn: async () => {
      const findingsResp = await apiClient.findings.list({
        limit: 500,
        account_id: accountId,
        provider: !accountId ? provider : undefined,
      });
      const findings = (findingsResp?.data as any[]) ?? [];
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
        data: {
          total: scoped.length,
          by_severity: bySeverity,
          by_status: byStatus,
        },
      };
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    enabled: accountIds.length > 0,
  });
}

export function useRecentFindings(limit = 8) {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const provider = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
  return useQuery({
    queryKey: [...dashboardKeys.recentFindings(), accountIds],
    queryFn: async () => {
      const resp = await apiClient.findings.list({
        limit: limit * 3,
        status: 'open',
        account_id: accountId,
        provider: !accountId ? provider : undefined,
      });
      const findings = (resp?.data as any[]) ?? [];
      const scoped = findings.filter(f => {
        if (accountId) return f.account_id === accountId;
        if (provider) return f.provider === provider;
        return accountIds.includes(f.account_id);
      }).slice(0, limit);
      return { ...resp, data: scoped };
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    enabled: accountIds.length > 0,
  });
}

export function useDashboardAccounts() {
  return useQuery({
    queryKey: dashboardKeys.accounts(),
    queryFn: () => connectorAPI.listAccounts(),
    staleTime: 60_000,
  });
}

export function useDashboardResources() {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const provider = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
  return useQuery({
    queryKey: [...dashboardKeys.resources(), accountIds],
    queryFn: () => connectorAPI.getResourcesSummary(accountId, provider),
    staleTime: 60_000,
    enabled: accountIds.length > 0,
  });
}
