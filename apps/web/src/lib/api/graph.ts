/**
 * Graph Service API Client
 *
 * All requests go through the API gateway (/v1/assets/*, /v1/risk/*)
 * which proxies to the graph service internally.
 *
 * Authentication: HttpOnly cookies via credentials: 'include'
 * Tokens are NEVER stored or accessed from JavaScript.
 */

import { getCsrfToken } from '@/lib/csrf';
import { refreshSession } from '@/lib/api/auth';

const GATEWAY_BASE_URL =
  process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8080';

/**
 * Unified fetch for graph endpoints through the API gateway.
 * Handles auth via HttpOnly cookies, CSRF tokens, and auto-refresh on 401.
 */
async function graphFetch(
  endpoint: string,
  options: RequestInit = {},
  _retry = true,
): Promise<any> {
  const url = `${GATEWAY_BASE_URL}${endpoint}`;
  const method = (options.method || 'GET').toUpperCase();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  // CSRF protection for state-changing requests
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) headers['X-CSRF-Token'] = csrf;
  }

  const response = await fetch(url, {
    credentials: 'include', // Send HttpOnly cookies automatically
    headers,
    ...options,
  });

  // Auto-refresh on 401 — server reads cv_refresh cookie, sets new cv_access
  if (response.status === 401 && _retry) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return graphFetch(endpoint, options, false);
    }
    throw new Error('Session expired. Please sign in again.');
  }

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  if (response.status === 204) return null;

  const json = await response.json();
  // Gateway wraps all responses in { data: ..., total: ..., took_ms: ... } envelope.
  // Unwrap `data` at this level for convenience, but keep `total` in the result.
  if (json && typeof json === 'object' && 'data' in json) {
    return {
      data: json.data,
      total: json.meta?.total ?? json.total,
      took_ms: json.took_ms ?? json.meta?.took_ms,
      next_cursor: json.meta?.next_cursor ?? json.next_cursor,
    };
  }
  return json;
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
// All endpoints use public gateway paths (/v1/assets/*, /v1/risk/*)
// The gateway adds org_id from JWT and proxies to internal graph service.
// Gateway wraps responses in { data: ..., total: ... } — we unwrap via graphFetch.

export const graphAPI = {
  /** List assets with optional filters */
  async listAssets(params: {
    org_id?: string; // Optional — gateway derives from JWT
    provider?: string;
    resource_type?: string;
    region?: string;
    environment?: string;
    is_public?: boolean;
    risk_score_min?: number;
    limit?: number; // kept for backwards compat — maps to page_size
    page?: number;
    page_size?: number;
    cursor?: string;
    account_ids?: string[]; // Optional — scope results to specific cloud accounts
  }): Promise<{ assets: GraphAsset[]; total: number; limit: number; next_cursor?: string }> {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && k !== 'org_id' && k !== 'account_ids' && k !== 'limit' && k !== 'cursor') {
        q.set(k, String(v));
      }
    });
    // Map legacy limit → page_size if page_size not explicitly set
    if (params.page_size !== undefined) {
      q.set('page_size', String(params.page_size));
    } else if (params.limit !== undefined) {
      q.set('page_size', String(params.limit));
    }
    if (params.account_ids && params.account_ids.length > 0) {
      q.set('account_ids', params.account_ids.join(','));
    }
    const result = await graphFetch(`/v1/assets?${q}`);
    const assets = result?.data ?? [];
    const total = result?.total ?? (Array.isArray(assets) ? assets.length : 0);
    return { assets, total, limit: params.limit || 50, next_cursor: result?.next_cursor };
  },

  /** Get a single asset */
  async getAsset(assetId: string): Promise<GraphAsset> {
    const result = await graphFetch(`/v1/assets/${assetId}`);
    return result?.data ?? result;
  },

  /** Get related assets (graph neighbors) */
  async getRelated(
    assetId: string,
    depth = 1
  ): Promise<{ asset_id: string; relationships: RelatedAsset[] }> {
    const result = await graphFetch(`/v1/assets/${assetId}/related?depth=${depth}`);
    return {
      asset_id: assetId,
      relationships: result?.data ?? result?.relationships ?? [],
    };
  },

  /** Get attack paths from/to an asset */
  async getAttackPaths(
    assetId: string,
    maxHops = 6
  ): Promise<{ paths: any[]; total: number }> {
    const result = await graphFetch(`/v1/assets/${assetId}/attack-paths?max_hops=${maxHops}`);
    return {
      paths: result?.data ?? result?.paths ?? [],
      total: result?.total ?? 0,
    };
  },

  /** Get PII attack paths (internet → sensitive DB) */
  async getPiiAttackPaths(
    orgId?: string, // Optional — gateway derives from JWT
    maxHops = 6
  ): Promise<{ paths: AttackPath[]; total: number }> {
    // Route through gateway's /v1/risk/attack-paths with PII filter
    const q = new URLSearchParams({ max_hops: String(maxHops), type: 'pii' });
    const result = await graphFetch(`/v1/risk/attack-paths?${q}`);
    const paths = result?.data ?? result?.paths ?? [];
    return {
      paths,
      total: result?.total ?? (Array.isArray(paths) ? paths.length : 0),
    };
  },

  /** Get asset summary stats */
  async getStats(orgId?: string): Promise<GraphStats> {
    const result = await graphFetch(`/v1/assets/summary`);
    const data = result?.data ?? result;
    // Map gateway response to GraphStats shape
    let nodeCount = data?.total ?? data?.node_count ?? 0;
    // Fallback: if no explicit count, sum by_provider values
    if (!nodeCount && data?.by_provider) {
      nodeCount = Object.values(data.by_provider).reduce(
        (sum: number, count: unknown) => sum + (Number(count) || 0),
        0,
      );
    }
    return {
      node_count: nodeCount,
      edge_count: data?.edge_count ?? 0,
      by_provider: data?.by_provider ?? {},
      by_type: data?.by_type ?? {},
    };
  },

  /** Get findings for an asset */
  async getFindings(assetId: string): Promise<{
    asset_id: string;
    findings: any[];
    total: number;
    open_findings_count: number;
  }> {
    const result = await graphFetch(`/v1/assets/${assetId}/findings`);
    const findings = result?.data ?? [];
    return {
      asset_id: assetId,
      findings,
      total: result?.total ?? (Array.isArray(findings) ? findings.length : 0),
      open_findings_count: (Array.isArray(findings) ? findings.filter((f: any) => f?.status === 'open').length : 0),
    };
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
    const result = await graphFetch(`/v1/assets/${assetId}/history${qs ? `?${qs}` : ''}`);
    return {
      asset_id: assetId,
      snapshots: result?.data ?? result?.snapshots ?? [],
      total: result?.total ?? 0,
    };
  },

  /** Full-text search across assets */
  async searchAssets(params: {
    q: string;
    org_id?: string; // Optional — gateway derives from JWT
    provider?: string;
    region?: string;
    limit?: number;
  }): Promise<{ total: number; hits: GraphAsset[]; limit: number; source: string }> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && k !== 'org_id') query.set(k, String(v));
    });
    const result = await graphFetch(`/v1/assets/search?${query}`);
    const hits = result?.data ?? [];
    return {
      hits,
      total: result?.total ?? (Array.isArray(hits) ? hits.length : 0),
      limit: params.limit || 50,
      source: 'gateway',
    };
  },
};

export default graphAPI;
