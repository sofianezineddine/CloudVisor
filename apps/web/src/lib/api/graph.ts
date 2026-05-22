/**
 * Graph Service API Client — Foundation Service 2
 * Connects to the graph service at port 8001.
 * Used by the asset graph view to fetch real relationship data.
 */

const GRAPH_BASE_URL =
  process.env.NEXT_PUBLIC_GRAPH_SERVICE_URL || 'http://localhost:8001';

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return null /* HttpOnly cookie */;
}

async function graphFetch(endpoint: string, options: RequestInit = {}): Promise<any> {
  const url = `${GRAPH_BASE_URL}${endpoint}`;
  const token = getAccessToken();

  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  return response.json();
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface GraphAsset {
  id: string;
  cloud_resource_id: string;
  provider: string;
  account_id: string;
  region: string;
  resource_type: string;
  name: string;
  tags: Record<string, string>;
  environment: string;
  is_public: boolean;
  is_internet_exposed?: boolean;
  has_public_access?: boolean;
  contains_pii?: boolean;
  contains_sensitive_data?: boolean;
  is_production?: boolean;
  is_admin?: boolean;
  risk_score: number;
  open_findings_count: number;
  last_seen_at: string;
  first_seen_at?: string;
  organization_id?: string;
}

export interface RelatedAsset {
  id: string;
  name: string;
  resource_type: string;
  relationship_type: string;
  risk_score: number;
}

export interface GraphStats {
  node_count: number;
  edge_count: number;
  by_provider: Record<string, number>;
  by_type: Record<string, number>;
}

export interface AttackPath {
  path: Array<{
    id: string;
    name: string;
    resource_type: string;
    risk_score: number;
    contains_pii?: boolean;
  }>;
  length: number;
}

// ─── API ──────────────────────────────────────────────────────────────────────

export const graphAPI = {
  /** List assets with optional filters */
  async listAssets(params: {
    org_id: string;
    provider?: string;
    resource_type?: string;
    region?: string;
    environment?: string;
    is_public?: boolean;
    risk_score_min?: number;
    page?: number;
    page_size?: number;
  }): Promise<{ assets: GraphAsset[]; total: number; page: number; page_size: number }> {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) q.set(k, String(v));
    });
    return graphFetch(`/internal/assets?${q}`);
  },

  /** Get a single asset */
  async getAsset(assetId: string): Promise<GraphAsset> {
    return graphFetch(`/internal/assets/${assetId}`);
  },

  /** Get related assets (graph neighbors) */
  async getRelated(
    assetId: string,
    depth = 1
  ): Promise<{ asset_id: string; relationships: RelatedAsset[] }> {
    return graphFetch(`/internal/assets/${assetId}/related?depth=${depth}`);
  },

  /** Get attack paths from/to an asset */
  async getAttackPaths(
    assetId: string,
    maxHops = 6
  ): Promise<{ paths: any[]; total: number }> {
    return graphFetch(`/internal/assets/${assetId}/attack-paths?max_hops=${maxHops}`);
  },

  /** Get PII attack paths (internet → sensitive DB) */
  async getPiiAttackPaths(
    orgId: string,
    maxHops = 6
  ): Promise<{ paths: AttackPath[]; total: number }> {
    return graphFetch(`/internal/assets/attack-paths/pii?org_id=${orgId}&max_hops=${maxHops}`);
  },

  /** Get graph stats */
  async getStats(orgId: string): Promise<GraphStats> {
    return graphFetch(`/internal/assets/stats?org_id=${orgId}`);
  },

  /** Get findings for an asset */
  async getFindings(assetId: string): Promise<{
    asset_id: string;
    findings: any[];
    total: number;
    open_findings_count: number;
  }> {
    return graphFetch(`/internal/assets/${assetId}/findings`);
  },

  /** Get historical snapshots for an asset (time-travel) */
  async getAssetHistory(
    assetId: string,
    params?: { start_time?: string; end_time?: string; limit?: number }
  ): Promise<{ asset_id: string; snapshots: any[]; total: number }> {
    const q = new URLSearchParams();
    if (params?.start_time) q.set('start_time', params.start_time);
    if (params?.end_time) q.set('end_time', params.end_time);
    if (params?.limit) q.set('limit', String(params.limit));
    const qs = q.toString();
    return graphFetch(`/internal/assets/${assetId}/history${qs ? `?${qs}` : ''}`);
  },

  /** Full-text search across assets */
  async searchAssets(params: {
    q: string;
    org_id: string;
    provider?: string;
    region?: string;
    page?: number;
    page_size?: number;
  }): Promise<{ total: number; hits: GraphAsset[]; page: number; page_size: number; source: string }> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) query.set(k, String(v));
    });
    return graphFetch(`/internal/assets/search?${query}`);
  },
};

export default graphAPI;
