'use client';

import { useQuery } from '@tanstack/react-query';
import { keepApi } from '@/lib/api/keep';

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * Keep's /dashboard/metric-widgets response shape.
 * - apd: Alert Provider Distribution (alerts per provider in last 24h)
 * - ipd: Incidents Per Day distribution
 * - wpd: Workflow executions Per Day distribution
 * - mttr: Mean Time To Resolve
 */
export interface AIOpsMetricWidgets {
  apd?: Record<string, unknown>;
  ipd?: Record<string, unknown>;
  wpd?: Record<string, unknown>;
  mttr?: Record<string, unknown>;
}

export interface AIOpsProviderInfo {
  id: string;
  type: string;
  display_name?: string;
  installed_by?: string;
  last_alert_received?: string;
  alertsDistribution?: Array<{ hour: number; number: number }>;
}

/**
 * @deprecated Keep doesn't have a dedicated trend endpoint.
 * Use useAIOpsDashboardMetrics() which returns metric widgets including alert distribution.
 */
export interface AIOpsAlertTrendPoint {
  date: string;
  critical: number;
  warning: number;
  info: number;
  low: number;
}

/** @deprecated Use AIOpsProviderInfo */
export interface AIOpsProviderHealth {
  id: string;
  name: string;
  type: string;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string;
}

export interface AIOpsProvidersResponse {
  providers: unknown[];
  installed_providers: AIOpsProviderInfo[];
  linked_providers: AIOpsProviderInfo[];
  is_localhost: boolean;
}

// ─── Query key factory ────────────────────────────────────────────────────────

export const aiopsDashboardKeys = {
  all: () => ['aiops', 'dashboard'] as const,
  metricWidgets: () => [...aiopsDashboardKeys.all(), 'metric-widgets'] as const,
  providerHealth: () => [...aiopsDashboardKeys.all(), 'provider-health'] as const,
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

/**
 * Fetches dashboard metric widgets from Keep's /dashboard/metric-widgets endpoint.
 * Returns alert distribution, incident distribution, workflow execution distribution, and MTTR.
 */
export function useAIOpsDashboardMetrics() {
  return useQuery({
    queryKey: aiopsDashboardKeys.metricWidgets(),
    queryFn: async () => {
      const { data } = await keepApi.get<AIOpsMetricWidgets>('/dashboard/metric-widgets');
      return data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

/**
 * Fetches provider health by listing all providers and their connection status.
 * Uses Keep's GET /providers endpoint which returns installed/linked providers with alert distribution.
 */
export function useAIOpsProviderHealth() {
  return useQuery({
    queryKey: aiopsDashboardKeys.providerHealth(),
    queryFn: async () => {
      const { data } = await keepApi.get<AIOpsProvidersResponse>('/providers');
      return data.installed_providers;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
