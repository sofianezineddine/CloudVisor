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

interface PaginatedResponse<T> {
  data: {
    items: T[];
    total: number;
    page: number;
    page_size: number;
  };
  meta?: { request_id?: string; took_ms?: number };
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
      const params: Record<string, string> = {};
      if (filters.page) params.page = String(filters.page);
      if (filters.page_size) params.page_size = String(filters.page_size);
      if (filters.severity?.length) params.severity = filters.severity.join(',');
      if (filters.status?.length) params.status = filters.status.join(',');
      if (filters.source) params.source = filters.source;
      if (filters.time_from) params.time_from = filters.time_from;
      if (filters.time_to) params.time_to = filters.time_to;
      if (filters.sort_by) params.sort_by = filters.sort_by;
      if (filters.sort_order) params.sort_order = filters.sort_order;
      if (filters.search) params.search = filters.search;

      const { data } = await keepApi.get<PaginatedResponse<AIOpsAlert>>('/alerts', { params });
      return data;
    },
    staleTime: 30_000,
  });
}

export function useAIOpsAlert(id: string | null) {
  return useQuery({
    queryKey: aiopsAlertKeys.detail(id ?? ''),
    queryFn: async () => {
      const { data } = await keepApi.get<{ data: AIOpsAlert }>(`/alerts/${id}`);
      return data.data;
    },
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useUpdateAlertStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const { data } = await keepApi.put<{ data: AIOpsAlert }>(`/alerts/${id}/status`, { status });
      return data.data;
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: aiopsAlertKeys.all() });
      queryClient.invalidateQueries({ queryKey: aiopsAlertKeys.detail(id) });
    },
  });
}
