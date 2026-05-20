'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { keepApi } from '@/lib/api/keep';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AIOpsMaintenanceRule {
  id: number;
  name: string;
  description?: string;
  created_by: string;
  cel_query: string;
  start_time: string;
  end_time: string;
  duration_seconds?: number;
  updated_at?: string;
  suppress: boolean;
  enabled: boolean;
}

/** @deprecated Use AIOpsMaintenanceRule */
export type AIOpsMaintenanceWindow = AIOpsMaintenanceRule;

export interface CreateMaintenanceRulePayload {
  name: string;
  description?: string;
  cel_query: string;
  start_time: string;
  duration_seconds?: number;
  suppress?: boolean;
  enabled?: boolean;
}

/** @deprecated Use CreateMaintenanceRulePayload */
export type CreateMaintenanceWindowPayload = CreateMaintenanceRulePayload;

export interface UpdateMaintenanceRulePayload extends CreateMaintenanceRulePayload {
  id: number;
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
      const { data } = await keepApi.get<AIOpsMaintenanceRule[]>('/maintenance');
      return data;
    },
    staleTime: 30_000,
  });
}

export function useCreateMaintenanceWindow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateMaintenanceRulePayload) => {
      const { data } = await keepApi.post<AIOpsMaintenanceRule>('/maintenance', payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiopsMaintenanceKeys.all() });
    },
  });
}

export function useUpdateMaintenanceWindow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: UpdateMaintenanceRulePayload) => {
      const { data } = await keepApi.put<AIOpsMaintenanceRule>(`/maintenance/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiopsMaintenanceKeys.all() });
    },
  });
}

export function useDeleteMaintenanceWindow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }: { id: number }) => {
      await keepApi.delete(`/maintenance/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiopsMaintenanceKeys.all() });
    },
  });
}
