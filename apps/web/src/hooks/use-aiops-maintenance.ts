'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { keepApi } from '@/lib/api/keep';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AIOpsMaintenanceWindow {
  id: string;
  name: string;
  status: 'scheduled' | 'active' | 'expired';
  start_time: string;
  end_time: string;
  filters: Record<string, unknown>;
  created_at: string;
}

export interface CreateMaintenanceWindowPayload {
  name: string;
  start_time: string;
  end_time: string;
  filters: Record<string, unknown>;
}

export interface UpdateMaintenanceWindowPayload {
  name?: string;
  start_time?: string;
  end_time?: string;
  filters?: Record<string, unknown>;
}

// ─── Query key factory ────────────────────────────────────────────────────────

export const aiopsMaintenanceKeys = {
  all: () => ['aiops', 'maintenance'] as const,
  lists: () => [...aiopsMaintenanceKeys.all(), 'list'] as const,
  list: () => [...aiopsMaintenanceKeys.lists()] as const,
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useAIOpsMaintenanceWindows() {
  return useQuery({
    queryKey: aiopsMaintenanceKeys.list(),
    queryFn: async () => {
      const { data } = await keepApi.get<{ data: AIOpsMaintenanceWindow[] }>('/aiops/maintenance');
      return data.data;
    },
    staleTime: 30_000,
  });
}

export function useCreateMaintenanceWindow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateMaintenanceWindowPayload) => {
      const { data } = await keepApi.post<{ data: AIOpsMaintenanceWindow }>('/aiops/maintenance', payload);
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiopsMaintenanceKeys.all() });
    },
  });
}

export function useUpdateMaintenanceWindow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: UpdateMaintenanceWindowPayload & { id: string }) => {
      const { data } = await keepApi.put<{ data: AIOpsMaintenanceWindow }>(`/maintenance/${id}`, payload);
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiopsMaintenanceKeys.all() });
    },
  });
}

export function useDeleteMaintenanceWindow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }: { id: string }) => {
      await keepApi.delete(`/maintenance/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiopsMaintenanceKeys.all() });
    },
  });
}
