'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { keepApi } from '@/lib/api/keep';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AIOpsAlert {
  id: string;
  fingerprint: string;
  name: string;
  status: 'firing' | 'acknowledged' | 'resolved' | 'suppressed';
  severity: 'critical' | 'high' | 'warning' | 'info' | 'low';
  source: string;
  provider_type: string;
  provider_id?: string;
  service?: string;
  assignee?: string;
  labels?: Record<string, string>;
  last_received: string;
  created_at: string;
  is_duplicate: boolean;
  duplicate_reason?: string;
}

export interface AIOpsAlertFilters {
  page?: number;
  page_size?: number;
  severity?: string[];
  status?: string[];
  source?: string;
  time_from?: string;
  time_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  search?: string;
}

// ─── Query key factory ────────────────────────────────────────────────────────

export const aiopsAlertKeys = {
  all: () => ['aiops', 'alerts'] as const,
  lists: () => [...aiopsAlertKeys.all(), 'list'] as const,
  list: (filters: AIOpsAlertFilters) => [...aiopsAlertKeys.lists(), filters] as const,
  detail: (id: string) => [...aiopsAlertKeys.all(), 'detail', id] as const,
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useAIOpsAlerts(filters: AIOpsAlertFilters = {}) {
  return useQuery({
    queryKey: aiopsAlertKeys.list(filters),
    queryFn: async () => {
      // Build CEL filter expression from the filter params
      const celParts: string[] = [];
      if (filters.severity?.length) {
        const severityList = filters.severity.map(s => `"${s}"`).join(', ');
        celParts.push(`severity in [${severityList}]`);
      }
      if (filters.status?.length) {
        const statusList = filters.status.map(s => `"${s}"`).join(', ');
        celParts.push(`status in [${statusList}]`);
      }
      if (filters.source) {
        celParts.push(`source == "${filters.source}"`);
      }
      if (filters.search) {
        celParts.push(`name.contains("${filters.search}")`);
      }

      const pageSize = filters.page_size || 25;
      const page = filters.page || 1;

      const query: Record<string, unknown> = {
        cel: celParts.length > 0 ? celParts.join(' && ') : undefined,
        limit: pageSize,
        offset: (page - 1) * pageSize,
        sort_by: filters.sort_by || 'lastReceived',
        sort_dir: filters.sort_order || 'desc',
      };

      const { data } = await keepApi.post<{
        limit: number;
        offset: number;
        count: number;
        results: AIOpsAlert[];
      }>('/alerts/query', query);

      return {
        data: {
          items: data.results,
          total: data.count,
          page,
          page_size: pageSize,
        },
      };
    },
    staleTime: 30_000,
  });
}

export function useAIOpsAlert(fingerprint: string | null) {
  return useQuery({
    queryKey: aiopsAlertKeys.detail(fingerprint ?? ''),
    queryFn: async () => {
      const { data } = await keepApi.get<AIOpsAlert>(`/alerts/${fingerprint}`);
      return data;
    },
    enabled: !!fingerprint,
    staleTime: 30_000,
  });
}

export function useUpdateAlertStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ fingerprint, status }: { fingerprint: string; status: string }) => {
      const { data } = await keepApi.post<{ data: { status: string } }>('/alerts/enrich', {
        fingerprint,
        enrichments: { status },
      });
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiopsAlertKeys.all() });
    },
  });
}
