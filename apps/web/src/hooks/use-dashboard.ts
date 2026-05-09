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
  topAssets:      () => [...dashboardKeys.all(), 'top-assets'] as const,
  activity:       () => [...dashboardKeys.all(), 'activity'] as const,
  modules:        () => [...dashboardKeys.all(), 'modules'] as const,
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
    // Use gateway /v1/accounts
    queryFn: async () => {
      try {
        const resp = await apiClient.accounts.list({ limit: 200 });
        const accounts = (resp?.data as any[]) ?? [];
        return { accounts, total: accounts.length };
      } catch {
        return connectorAPI.listAccounts();
      }
    },
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

/** GET /v1/risk/top-assets — top N riskiest assets by risk score */
export function useTopRiskyAssets(limit = 10) {
  const accountIds = useScopeStore(s => s.accountIds);
  return useQuery({
    queryKey: [...dashboardKeys.topAssets(), limit, accountIds],
    queryFn: async () => {
      const resp = await apiClient.risk.topAssets(limit);
      return (resp?.data as any[]) ?? [];
    },
    staleTime: 60_000,
    enabled: accountIds.length > 0,
  });
}

/** GET /v1/activity — recent activity feed */
export function useDashboardActivity(limit = 20) {
  const accountIds = useScopeStore(s => s.accountIds);
  return useQuery({
    queryKey: [...dashboardKeys.activity(), limit, accountIds],
    queryFn: async () => {
      const resp = await apiClient.activity.list(limit);
      return (resp?.data as any[]) ?? [];
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    enabled: accountIds.length > 0,
  });
}

/** GET /v1/modules/summary — per-module finding counts */
export function useModulesSummary() {
  const accountIds = useScopeStore(s => s.accountIds);
  return useQuery({
    queryKey: [...dashboardKeys.modules(), accountIds],
    queryFn: async () => {
      const resp = await apiClient.modules.summary();
      return (resp?.data as any[]) ?? [];
    },
    staleTime: 60_000,
    enabled: accountIds.length > 0,
  });
}
