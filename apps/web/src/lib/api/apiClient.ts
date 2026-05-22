/**
 * API Gateway Client
 *
 * All public-facing operations should go through the API gateway at
 * localhost:8005/v1 rather than calling individual microservices directly.
 *
 * The gateway handles:
 *  - JWT validation and tenant isolation
 *  - Rate limiting
 *  - Request routing to upstream services
 *  - Unified error responses
 */

const API_GATEWAY_BASE_URL =
  process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005';

const AUTH_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8002';

/** Read the access token from localStorage (set by use-auth.tsx on login). */
function getAccessToken(): string | null {
  // No longer needed — auth is via HttpOnly cookies
  return null;
}

function getRefreshToken(): string | null {
  // No longer needed — refresh is via HttpOnly cookie
  return null;
}

/** Attempt a silent token refresh via cookie. */
async function silentRefresh(): Promise<string | null> {
  try {
    const res = await fetch(`${AUTH_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include', // Send cv_refresh cookie
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!res.ok) return null;
    return 'refreshed'; // Server set new cookies
  } catch {
    return null;
  }
}

/** Clear tokens and redirect to login. */
function forceLogout(): void {
  localStorage.removeItem('cloudvisor-user');
  if (typeof window !== 'undefined') {
    window.location.href = '/login?error=session_expired';
  }
}

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ApiEnvelope<T = unknown> {
  data: T;
  total?: number;
  took_ms?: number;
  error?: string;
  meta?: {
    request_id?: string;
    total?: number | null;
    took_ms?: number;
    next_cursor?: string | null;
  };
  errors?: Array<{ code: string; message: string }>;
}

export interface Finding {
  id: string;
  organization_id: string;
  rule_id: string;
  resource_id: string;
  resource_name: string | null;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  status: 'open' | 'in_progress' | 'resolved' | 'suppressed' | 'accepted_risk';
  title: string;
  description: string | null;
  remediation: string | null;
  provider: string | null;
  account_id: string | null;
  region: string | null;
  resource_type: string | null;
  first_seen_at: string;
  last_seen_at: string;
  resolved_at: string | null;
  compliance_mapping?: Array<{ framework: string; control: string } | string>;
  tags?: string[];
  fingerprint?: string;
  regression_count?: number;
}

export interface Incident {
  id: string;
  organization_id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  finding_ids: string[];
  assignee_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationChannel {
  id: string;
  organization_id: string;
  name: string;
  channel_type: string;
  config: Record<string, unknown>;
  severity_filter: string[];
  module_filter?: string[];
  account_filter?: string[];
  tag_filter?: Record<string, string>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Asset {
  id: string;
  cloud_resource_id: string;
  provider: string;
  account_id: string;
  region: string;
  resource_type: string;
  name: string;
  tags: Record<string, string>;
  is_public: boolean;
  environment: string;
  risk_score: number;
  open_findings_count: number;
}

export interface ComplianceResult {
  framework: string;
  control: string;
  status: string;
  resource_id: string;
  resource_type: string;
}

// ─── Core fetch helper ───────────────────────────────────────────────────────

async function apiFetch<T = unknown>(
  endpoint: string,
  options: RequestInit = {},
  _retry = true,
): Promise<T> {
  const url = `${API_GATEWAY_BASE_URL}${endpoint}`;

  // Add CSRF token for state-changing requests
  const method = (options.method || 'GET').toUpperCase();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers as Record<string, string>,
  };
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && typeof document !== 'undefined') {
    const csrfMatch = document.cookie.match(/(?:^|; )cv_csrf=([^;]*)/);
    if (csrfMatch) headers['X-CSRF-Token'] = decodeURIComponent(csrfMatch[1]);
  }

  const response = await fetch(url, {
    credentials: 'include', // Send HttpOnly cookies
    headers,
    ...options,
  });

  // ── Auto-refresh on 401 ───────────────────────────────────────────────────
  if (response.status === 401 && _retry) {
    const refreshed = await silentRefresh();
    if (refreshed) {
      // Retry once — server set new cookies
      return apiFetch<T>(endpoint, options, false);
    }
    // Don't clear tokens — let AuthProvider handle session state
    throw new Error('Session expired. Please sign in again.');
  }

  if (!response.ok) {
    let errorData: { detail?: unknown };
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: 'Request failed' };
    }

    let errorMessage: string;
    if (Array.isArray(errorData.detail)) {
      errorMessage = (errorData.detail as Array<{ loc?: string[]; msg: string }>)
        .map((e) => `${e.loc?.join('.') || 'field'}: ${e.msg}`)
        .join(', ');
    } else if (typeof errorData.detail === 'string') {
      errorMessage = errorData.detail;
    } else if (typeof errorData.detail === 'object' && errorData.detail !== null) {
      errorMessage = JSON.stringify(errorData.detail);
    } else {
      errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    }

    throw new Error(errorMessage);
  }

  if (response.status === 204) {
    return null as T;
  }

  const json = await response.json();
  // Normalize: hoist meta.total to top-level total for convenience
  if (json && typeof json === 'object' && json.meta && json.total === undefined) {
    json.total = json.meta.total ?? undefined;
  }
  return json as T;
}

// ─── Findings ────────────────────────────────────────────────────────────────

export const findingsAPI = {
  async list(params?: {
    severity?: string;
    status?: string;
    provider?: string;
    account_id?: string;
    region?: string;
    assignee_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApiEnvelope<Finding[]>> {
    const query = new URLSearchParams();
    if (params?.severity) query.set('severity', params.severity);
    if (params?.status) query.set('status', params.status);
    if (params?.provider) query.set('provider', params.provider);
    if (params?.account_id) query.set('account_id', params.account_id);
    if (params?.region) query.set('region', params.region);
    if (params?.assignee_id) query.set('assignee_id', params.assignee_id);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return apiFetch(`/v1/findings${qs ? `?${qs}` : ''}`);
  },
  async get(findingId: string): Promise<ApiEnvelope<Finding>> {
    return apiFetch(`/v1/findings/${findingId}`);
  },

  async update(
    findingId: string,
    data: { status?: string; assignee_id?: string; note?: string }
  ): Promise<ApiEnvelope<Finding>> {
    return apiFetch(`/v1/findings/${findingId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async suppress(findingId: string, reason: string): Promise<ApiEnvelope<Finding>> {
    return apiFetch(`/v1/findings/${findingId}/suppress`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  },

  async acceptRisk(findingId: string, justification: string): Promise<ApiEnvelope<Finding>> {
    return apiFetch(`/v1/findings/${findingId}/accept-risk`, {
      method: 'POST',
      body: JSON.stringify({ justification }),
    });
  },

  async bulkUpdate(
    findingIds: string[],
    status: string,
    reason?: string
  ): Promise<ApiEnvelope<{ updated: number; total: number }>> {
    return apiFetch('/v1/findings/bulk', {
      method: 'POST',
      body: JSON.stringify({ finding_ids: findingIds, status, reason }),
    });
  },

  async stats(params?: {
    account_id?: string;
    provider?: string;
  }): Promise<ApiEnvelope<Record<string, unknown>>> {
    const query = new URLSearchParams();
    if (params?.account_id) query.set('account_id', params.account_id);
    if (params?.provider) query.set('provider', params.provider);
    const qs = query.toString();
    return apiFetch(`/v1/findings/stats${qs ? `?${qs}` : ''}`);
  },
};

// ─── Incidents ───────────────────────────────────────────────────────────────

export const incidentsAPI = {
  async list(params?: {
    status?: string;
    severity?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApiEnvelope<Incident[]>> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.severity) query.set('severity', params.severity);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return apiFetch(`/v1/incidents${qs ? `?${qs}` : ''}`);
  },

  async get(incidentId: string): Promise<ApiEnvelope<Incident>> {
    return apiFetch(`/v1/incidents/${incidentId}`);
  },

  async update(
    incidentId: string,
    data: {
      status?: string;
      title?: string;
      description?: string;
      assignee_id?: string;
    }
  ): Promise<ApiEnvelope<Incident>> {
    return apiFetch(`/v1/incidents/${incidentId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
};

// ─── Notifications ───────────────────────────────────────────────────────────

export const notificationsAPI = {
  async listChannels(): Promise<ApiEnvelope<NotificationChannel[]>> {
    return apiFetch('/v1/notifications/channels');
  },

  async addChannel(data: {
    name: string;
    channel_type: string;
    config: Record<string, unknown>;
    severity_filter?: string[];
    module_filter?: string[];
    account_filter?: string[];
    tag_filter?: Record<string, string>;
    is_active?: boolean;
  }): Promise<ApiEnvelope<NotificationChannel>> {
    return apiFetch('/v1/notifications/channels', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateChannel(
    channelId: string,
    data: {
      name?: string;
      config?: Record<string, unknown>;
      severity_filter?: string[];
      module_filter?: string[];
      account_filter?: string[];
      tag_filter?: Record<string, string>;
      is_active?: boolean;
    }
  ): Promise<ApiEnvelope<NotificationChannel>> {
    return apiFetch(`/v1/notifications/channels/${channelId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async removeChannel(channelId: string): Promise<null> {
    return apiFetch(`/v1/notifications/channels/${channelId}`, {
      method: 'DELETE',
    });
  },

  async testChannel(data: {
    channel_id?: string;
    channel_type?: string;
    config?: Record<string, unknown>;
  }): Promise<ApiEnvelope<{ success: boolean; message: string }>> {
    return apiFetch('/v1/notifications/test', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// ─── Assets ──────────────────────────────────────────────────────────────────

export const assetsAPI = {
  async list(params?: {
    provider?: string;
    resource_type?: string;
    region?: string;
    account_id?: string;
    is_public?: boolean;
    environment?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApiEnvelope<Asset[]>> {
    const query = new URLSearchParams();
    if (params?.provider) query.set('provider', params.provider);
    if (params?.resource_type) query.set('resource_type', params.resource_type);
    if (params?.region) query.set('region', params.region);
    if (params?.account_id) query.set('account_id', params.account_id);
    if (params?.is_public !== undefined) query.set('is_public', String(params.is_public));
    if (params?.environment) query.set('environment', params.environment);
    if (params?.search) query.set('search', params.search);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return apiFetch(`/v1/assets${qs ? `?${qs}` : ''}`);
  },

  async get(assetId: string): Promise<ApiEnvelope<Asset>> {
    return apiFetch(`/v1/assets/${assetId}`);
  },

  async getHistory(assetId: string, params?: { start_time?: string; end_time?: string; limit?: number }): Promise<ApiEnvelope<any>> {
    const query = new URLSearchParams();
    if (params?.start_time) query.set('start_time', params.start_time);
    if (params?.end_time) query.set('end_time', params.end_time);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    const qs = query.toString();
    // Proxied through graph service via gateway assets endpoint
    return apiFetch(`/v1/assets/${assetId}/history${qs ? `?${qs}` : ''}`);
  },

  async search(q: string, params?: { provider?: string; region?: string; limit?: number }): Promise<ApiEnvelope<Asset[]>> {
    const query = new URLSearchParams({ q });
    if (params?.provider) query.set('provider', params.provider);
    if (params?.region) query.set('region', params.region);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    // Uses Elasticsearch-backed full-text search via graph service
    return apiFetch(`/v1/assets/search?${query}`);
  },
};

// ─── Compliance ───────────────────────────────────────────────────────────────

export const complianceAPI = {
  async list(params?: {
    framework?: string;
    status?: string;
    account_id?: string;
    provider?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApiEnvelope<ComplianceResult[]>> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.account_id) query.set('account_id', params.account_id);
    if (params?.provider) query.set('provider', params.provider);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    // If a specific framework is requested, use the framework detail endpoint
    if (params?.framework) {
      return apiFetch(`/v1/compliance/${encodeURIComponent(params.framework)}${qs ? `?${qs}` : ''}`);
    }
    return apiFetch(`/v1/compliance${qs ? `?${qs}` : ''}`);
  },

  async getEvidence(framework: string, controlId: string): Promise<ApiEnvelope<any>> {
    return apiFetch(`/v1/compliance/${encodeURIComponent(framework)}/evidence?control_id=${encodeURIComponent(controlId)}`);
  },
};

// ─── Copilot ──────────────────────────────────────────────────────────────────

export const copilotAPI = {
  async query(data: {
    query: string;
    stream?: boolean;
    context?: Record<string, unknown>;
    session_id?: string;
  }): Promise<ApiEnvelope<any>> {
    return apiFetch('/v1/copilot/query', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getHistory(limit = 10): Promise<ApiEnvelope<any[]>> {
    return apiFetch(`/v1/copilot/history?limit=${limit}`);
  },
};

// ─── Risk ─────────────────────────────────────────────────────────────────────

export const riskAPI = {
  async topAssets(limit = 10): Promise<ApiEnvelope<Asset[]>> {
    return apiFetch(`/v1/risk/top-assets?limit=${limit}`);
  },
  async attackPaths(maxHops = 6): Promise<ApiEnvelope<any[]>> {
    return apiFetch(`/v1/risk/attack-paths?max_hops=${maxHops}`);
  },
};

// ─── Activity feed ────────────────────────────────────────────────────────────

export const activityAPI = {
  async list(limit = 20): Promise<ApiEnvelope<any[]>> {
    return apiFetch(`/v1/activity?limit=${limit}`);
  },
};

// ─── Modules summary ──────────────────────────────────────────────────────────

export const modulesAPI = {
  async summary(): Promise<ApiEnvelope<any[]>> {
    return apiFetch('/v1/modules/summary');
  },
};

// ─── Reports ──────────────────────────────────────────────────────────────────

export const reportsAPI = {
  async list(params?: { report_type?: string; limit?: number }): Promise<ApiEnvelope<any[]>> {
    const query = new URLSearchParams();
    if (params?.report_type) query.set('report_type', params.report_type);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    const qs = query.toString();
    return apiFetch(`/v1/reports${qs ? `?${qs}` : ''}`);
  },

  async get(reportId: string): Promise<ApiEnvelope<any>> {
    return apiFetch(`/v1/reports/${reportId}`);
  },

  async generate(data: {
    report_type: string;
    framework?: string;
    format?: string;
    date_from?: string;
    date_to?: string;
    account_ids?: string[];
  }): Promise<ApiEnvelope<any>> {
    return apiFetch('/v1/reports', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// ─── Accounts ─────────────────────────────────────────────────────────────────

export const accountsAPI = {
  async list(params?: { limit?: number; offset?: number }): Promise<ApiEnvelope<any[]>> {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return apiFetch(`/v1/accounts${qs ? `?${qs}` : ''}`);
  },

  async get(accountId: string): Promise<ApiEnvelope<any>> {
    return apiFetch(`/v1/accounts/${accountId}`);
  },

  async create(data: {
    provider: string;
    name: string;
    account_id: string;
    region?: string;
    credentials?: Record<string, unknown>;
    polling_interval_minutes?: number;
  }): Promise<ApiEnvelope<any>> {
    return apiFetch('/v1/accounts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async delete(accountId: string): Promise<null> {
    return apiFetch(`/v1/accounts/${accountId}`, { method: 'DELETE' });
  },

  async triggerScan(accountId: string): Promise<ApiEnvelope<any>> {
    return apiFetch(`/v1/accounts/${accountId}/scan`, { method: 'POST', body: JSON.stringify({}) });
  },
};

// ─── Default export ───────────────────────────────────────────────────────────

const apiClient = {
  findings: findingsAPI,
  incidents: incidentsAPI,
  notifications: notificationsAPI,
  assets: assetsAPI,
  compliance: complianceAPI,
  accounts: accountsAPI,
  reports: reportsAPI,
  risk: riskAPI,
  activity: activityAPI,
  modules: modulesAPI,
  copilot: copilotAPI,
};

export default apiClient;
