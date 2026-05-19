'use client';

import { useQuery } from '@tanstack/react-query';
import { keepApi } from '@/lib/api/keep';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AIOpsDashboardMetrics {
  total_alerts_24h: number;
  open_incidents: number;
  active_providers: number;
  workflow_executions_24h: number;
}

export interface AIOpsAlertTrendPoint {
  date: string;
  critical: number;
  warning: number;
  info: number;
  low: number;
}

export interface AIOpsProviderHealth {
  id: string;
  name: string;
  type: string;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string;
}

// ─── Query key factory ────────────────────────────────────────────────────────

export const aiopsDashboardKeys = {
  all: () => ['aiops', 'dashboard'] as const,
  metrics: () => [...aiopsDashboardKeys.all(), 'metrics'] as const,
  trend: () => [...aiopsDashboardKeys.all(), 'trend'] as const,
  providerHealth: () => [...aiopsDashboardKeys.all(), 'provider-health'] as const,
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useAIOpsDashboardMetrics() {
  return useQuery({
    queryKey: aiopsDashboardKeys.metrics(),
    queryFn: async () => {
      const { data } = await keepApi.get<{ data: AIOpsDashboardMetrics }>('/aiops/dashboard/metrics');
      return data.data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useAIOpsDashboardTrend() {
  return useQuery({
    queryKey: aiopsDashboardKeys.trend(),
    queryFn: async () => {
      const { data } = await keepApi.get<{ data: AIOpsAlertTrendPoint[] }>('/aiops/dashboard/trend');
      return data.data;
    },
    staleTime: 60_000,
  });
}

export function useAIOpsProviderHealth() {
  return useQuery({
    queryKey: aiopsDashboardKeys.providerHealth(),
    queryFn: async () => {
      const { data } = await keepApi.get<{ data: AIOpsProviderHealth[] }>('/aiops/dashboard/provider-health');
      return data.data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
