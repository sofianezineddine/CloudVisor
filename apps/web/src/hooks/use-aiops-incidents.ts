'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { keepApi } from '@/lib/api/keep';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AIOpsIncident {
  id: string;
  title: string;
  status: 'open' | 'acknowledged' | 'investigating' | 'resolved' | 'closed';
  severity: 'critical' | 'high' | 'warning' | 'info' | 'low';
  ai_summary?: string;
  assignee?: string;
  alert_count: number;
  created_at: string;
  updated_at: string;
}

export interface AIOpsIncidentDetail extends AIOpsIncident {
  alerts: Array<{ id: string; name: string; severity: string; status: string }>;
  timeline: Array<{
    event_type: string;
    description: string;
    timestamp: string;
    user_id?: string;
  }>;
}

export interface AIOpsIncidentFilters {
  page?: number;
  page_size?: number;
  status?: string;
  severity?: string;
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

export const aiopsIncidentKeys = {
  all: () => ['aiops', 'incidents'] as const,
  lists: () => [...aiopsIncidentKeys.all(), 'list'] as const,
  list: (filters: AIOpsIncidentFilters) => [...aiopsIncidentKeys.lists(), filters] as const,
  detail: (id: string) => [...aiopsIncidentKeys.all(), 'detail', id] as const,
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useAIOpsIncidents(filters: AIOpsIncidentFilters = {}) {
  return useQuery({
    queryKey: aiopsIncidentKeys.list(filters),
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (filters.page) params.page = String(filters.page);
      if (filters.page_size) params.page_size = String(filters.page_size);
      if (filters.status) params.status = filters.status;
      if (filters.severity) params.severity = filters.severity;

      const { data } = await keepApi.get<PaginatedResponse<AIOpsIncident>>('/incidents', { params });
      return data;
    },
    staleTime: 30_000,
  });
}

export function useAIOpsIncident(id: string | null) {
  return useQuery({
    queryKey: aiopsIncidentKeys.detail(id ?? ''),
    queryFn: async () => {
      const { data } = await keepApi.get<{ data: AIOpsIncidentDetail }>(`/incidents/${id}`);
      return data.data;
    },
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useUpdateIncidentStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const { data } = await keepApi.put<{ data: AIOpsIncident }>(`/incidents/${id}/status`, { status });
      return data.data;
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: aiopsIncidentKeys.all() });
      queryClient.invalidateQueries({ queryKey: aiopsIncidentKeys.detail(id) });
    },
  });
}

export function useCreateIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { title: string; alert_ids: string[]; severity?: string }) => {
      const { data } = await keepApi.post<{ data: AIOpsIncident }>('/incidents', payload);
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiopsIncidentKeys.all() });
    },
  });
}
