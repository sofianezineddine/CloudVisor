'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { keepApi } from '@/lib/api/keep';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AIOpsWorkflow {
  id: string;
  name: string;
  status: 'enabled' | 'disabled';
  yaml_definition: string;
  trigger_config: Record<string, unknown>;
  last_execution?: string;
  execution_count: number;
  created_at: string;
  updated_at: string;
}

export interface AIOpsWorkflowExecution {
  id: string;
  workflow_id: string;
  status: 'success' | 'failure' | 'in-progress';
  duration_ms: number;
  logs: Record<string, unknown>;
  trigger_alert_id?: string;
  started_at: string;
  completed_at?: string;
}

// ─── Query key factory ────────────────────────────────────────────────────────

export const aiopsWorkflowKeys = {
  all: () => ['aiops', 'workflows'] as const,
  lists: () => [...aiopsWorkflowKeys.all(), 'list'] as const,
  list: () => [...aiopsWorkflowKeys.lists()] as const,
  detail: (id: string) => [...aiopsWorkflowKeys.all(), 'detail', id] as const,
  executions: (id: string) => [...aiopsWorkflowKeys.all(), 'executions', id] as const,
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useAIOpsWorkflows() {
  return useQuery({
    queryKey: aiopsWorkflowKeys.list(),
    queryFn: async () => {
      const { data } = await keepApi.get<AIOpsWorkflow[]>('/workflows');
      return data;
    },
    staleTime: 30_000,
  });
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { yaml_definition: string }) => {
      // Keep expects the workflow YAML as the raw request body at POST /workflows/json
      const { data } = await keepApi.post<{ workflow_id: string; status: string; revision: number }>(
        '/workflows/json',
        payload.yaml_definition,
        { headers: { 'Content-Type': 'application/yaml' } }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiopsWorkflowKeys.all() });
    },
  });
}

export function useToggleWorkflowStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }: { id: string }) => {
      const { data } = await keepApi.put<{ workflow_id: string; status: string; is_disabled: boolean }>(`/workflows/${id}/toggle`);
      return data;
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: aiopsWorkflowKeys.all() });
      queryClient.invalidateQueries({ queryKey: aiopsWorkflowKeys.detail(id) });
    },
  });
}

export function useRunWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }: { id: string }) => {
      const { data } = await keepApi.post<{ workflow_execution_id: string }>(`/workflows/${id}/run`);
      return data;
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: aiopsWorkflowKeys.executions(id) });
      queryClient.invalidateQueries({ queryKey: aiopsWorkflowKeys.all() });
    },
  });
}
