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

/** Read the access token from localStorage (set by use-auth.tsx on login). */
function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
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
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_GATEWAY_BASE_URL}${endpoint}`;
  const token = getAccessToken();

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...options,
  });

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
    is_active?: boolean;
  }): Promise<ApiEnvelope<NotificationChannel>> {
    return apiFetch('/v1/notifications/channels', {
      method: 'POST',
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
    if (params?.framework) query.set('framework', params.framework);
    if (params?.status) query.set('status', params.status);
    if (params?.account_id) query.set('account_id', params.account_id);
    if (params?.provider) query.set('provider', params.provider);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return apiFetch(`/v1/compliance${qs ? `?${qs}` : ''}`);
  },
};

// ─── Default export ───────────────────────────────────────────────────────────

const apiClient = {
  findings: findingsAPI,
  incidents: incidentsAPI,
  notifications: notificationsAPI,
  assets: assetsAPI,
  compliance: complianceAPI,
};

export default apiClient;
