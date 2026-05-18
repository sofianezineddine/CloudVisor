'use client';

import { useQuery } from '@tanstack/react-query';
import { keepApi } from '@/lib/api/keep';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TopologyService {
  id: string;
  name: string;
  display_name: string;
  metadata?: Record<string, unknown>;
  updated_at: string;
}

export interface TopologyEdge {
  id: string;
  source_service_id: string;
  target_service_id: string;
  relationship_type: string;
}

export interface TopologyGraph {
  services: TopologyService[];
  edges: TopologyEdge[];
}

export interface TopologyServiceAlert {
  id: string;
  name: string;
  severity: string;
  status: string;
  created_at: string;
}

// ─── Query key factory ────────────────────────────────────────────────────────

export const aiopsTopologyKeys = {
  all: () => ['aiops', 'topology'] as const,
  graph: () => [...aiopsTopologyKeys.all(), 'graph'] as const,
  serviceAlerts: (serviceId: string) => [...aiopsTopologyKeys.all(), 'service-alerts', serviceId] as const,
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useAIOpsTopology() {
  return useQuery({
    queryKey: aiopsTopologyKeys.graph(),
    queryFn: async () => {
      const { data } = await keepApi.get<{ data: TopologyGraph }>('/topology');
      return data.data;
    },
    staleTime: 60_000,
  });
}

export function useTopologyServiceAlerts(serviceId: string | null) {
  return useQuery({
    queryKey: aiopsTopologyKeys.serviceAlerts(serviceId ?? ''),
    queryFn: async () => {
      const { data } = await keepApi.get<{ data: TopologyServiceAlert[] }>(`/topology/${serviceId}/alerts`);
      return data.data;
    },
    enabled: !!serviceId,
    staleTime: 30_000,
  });
}
