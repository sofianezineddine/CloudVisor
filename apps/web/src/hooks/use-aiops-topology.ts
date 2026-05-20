'use client';

import { useQuery } from '@tanstack/react-query';
import { keepApi } from '@/lib/api/keep';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TopologyServiceDependency {
  id: string;
  serviceId: string;
  serviceName: string;
  protocol?: string;
}

export interface TopologyService {
  id: string;
  service: string;
  display_name: string;
  /** Alias for display_name used by UI components */
  name?: string;
  environment?: string;
  dependencies: TopologyServiceDependency[];
  application_ids?: string[];
  updated_at?: string;
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
      const { data } = await keepApi.get<TopologyService[]>('/topology');

      // Derive edges from each service's dependencies array
      const edges: TopologyEdge[] = [];
      for (const service of data) {
        for (const dep of service.dependencies ?? []) {
          edges.push({
            id: dep.id || `${service.id}-${dep.serviceId}`,
            source_service_id: service.id,
            target_service_id: dep.serviceId,
            relationship_type: dep.protocol || 'depends_on',
          });
        }
      }

      return { services: data, edges } as TopologyGraph;
    },
    staleTime: 60_000,
  });
}

export function useTopologyServiceAlerts(serviceId: string | null) {
  return useQuery({
    queryKey: aiopsTopologyKeys.serviceAlerts(serviceId ?? ''),
    queryFn: async () => {
      // Query alerts filtered by service name using Keep's alert query endpoint
      const { data } = await keepApi.post<{
        limit: number;
        offset: number;
        count: number;
        results: TopologyServiceAlert[];
      }>('/alerts/query', {
        cel: `service == "${serviceId}"`,
        limit: 50,
        offset: 0,
      });
      return data.results;
    },
    enabled: !!serviceId,
    staleTime: 30_000,
  });
}
