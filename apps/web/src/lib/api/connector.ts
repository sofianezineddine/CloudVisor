/**
 * Connector Service API Client
 *
 * Routes through the API gateway (/v1/accounts) which:
 * 1. Reads auth from HttpOnly cookie
 * 2. Validates the JWT and extracts org_id
 * 3. Proxies to the connector service with proper tenant isolation
 *
 * Authentication: HttpOnly cookies via credentials: 'include'
 * Tokens are NEVER stored in or read from localStorage.
 * Refresh is handled server-side via cv_refresh HttpOnly cookie.
 */

import { getCsrfToken } from '@/lib/csrf';
import { refreshSession } from '@/lib/api/auth';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8080';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface CloudAccount {
  id: string;
  organization_id: string;
  provider: 'aws' | 'azure' | 'gcp' | 'oci';
  name: string;
  account_id: string;
  region: string;
  status: 'pending' | 'active' | 'error' | 'auth_failed' | 'partial_sync' | 'paused';
  sync_status: 'idle' | 'syncing' | 'completed' | 'error';
  last_sync_at: string | null;
  last_successful_sync_at: string | null;
  consecutive_errors: number;
  error_message: string | null;
  resource_count: number;
  polling_interval_minutes: number;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface DiscoveredResource {
  id: string;
  cloud_resource_id: string;
  provider: 'aws' | 'azure' | 'gcp' | 'oci';
  account_id: string;
  organization_id: string;
  region: string;
  resource_type: string;
  name: string;
  tags: Record<string, string>;
  is_public: boolean;
  environment: 'prod' | 'staging' | 'dev' | 'unknown';
  freshness_state: 'fresh' | 'stale' | 'deleted';
  missed_sync_count: number;
  first_seen_at: string | null;
  last_seen_at: string | null;
}

export interface ResourceListResponse {
  resources: DiscoveredResource[];
  total: number;
  offset: number;
  limit: number;
}

export interface ResourceSummary {
  total: number;
  by_provider: Record<string, number>;
  by_type: Record<string, number>;
  by_freshness: Record<string, number>;
}

export interface CloudAccountCredentials {
  // AWS
  access_key?: string;
  secret_key?: string;
  session_token?: string;
  // Azure
  tenant_id?: string;
  client_id?: string;
  client_secret?: string;
  subscription_id?: string;
  // GCP
  project_id?: string;
  service_account_json?: string;
  // OCI
  user_ocid?: string;
  fingerprint?: string;
  tenancy_ocid?: string;
  private_key?: string;
  region?: string;
}

export interface CreateAccountRequest {
  provider: string;
  name: string;
  account_id: string;
  region: string;
  credentials?: CloudAccountCredentials;
  polling_interval_minutes?: number;
}

export interface UpdateAccountRequest {
  name?: string;
  region?: string;
  polling_interval_minutes?: number;
}

export interface AccountListResponse {
  accounts: CloudAccount[];
  total: number;
}

export interface AccountHealthResponse {
  id: string;
  status: string;
  sync_status: string;
  last_sync_at: string | null;
  last_successful_sync_at: string | null;
  consecutive_errors: number;
  error_message: string | null;
  resource_count: number;
  error_rate: number;
}

export interface SyncTriggerResponse {
  account_id: string;
  correlation_id: string;
  status: string;
  message: string;
}

export interface OnboardingResponse {
  provider: string;
  instructions: string;
  template?: string;
}

export interface SyncStatusResponse {
  account_id: string;
  provider: string;
  account_status: string;
  sync_status: string;
  last_sync_at: string | null;
  last_successful_sync_at: string | null;
  resource_count: number;
  consecutive_errors: number;
  current_sync: {
    correlation_id: string;
    sync_type: string;
    status: string;
    started_at?: string;
    finished_at?: string;
    discovered?: number;
    updated?: number;
    deleted?: number;
    errors?: number;
    duration_seconds?: number;
    error_details?: string[];
  } | null;
}

export interface CredentialRotateRequest {
  credentials: CloudAccountCredentials;
}

export interface CredentialRotateResponse {
  account_id: string;
  vault_stored: boolean;
  connectivity_ok: boolean;
  warnings: string[];
}

export interface ScanHistoryEntry {
  id: string;
  account_id: string;
  sync_type: string;
  status: string;
  correlation_id: string;
  discovered: number;
  updated: number;
  deleted: number;
  errors: number;
  duration_seconds: number;
  started_at: string;
  finished_at: string | null;
  error_details: string[];
}

export interface ScanHistoryResponse {
  scans: ScanHistoryEntry[];
  total: number;
  account_id: string;
}

export interface ResourceTypeCatalogEntry {
  service_key: string;
  resource_type: string;
}

export interface ResourceTypeCatalog {
  providers: Record<string, {
    display_name: string;
    resource_types: ResourceTypeCatalogEntry[];
    total: number;
  }>;
  total_types: number;
}

// ─── API Client ──────────────────────────────────────────────────────────────
// All endpoints route through /v1/accounts on the API gateway.
// The gateway handles internal path mapping (/v1/accounts/* → /internal/accounts/*).

async function connectorFetch(
  endpoint: string,
  options: RequestInit = {},
  _retry = true,
): Promise<any> {
  // Map internal paths to public gateway paths
  // /internal/accounts/{path} → /v1/accounts/{path}
  // /internal/{resource} → /v1/accounts/{resource}
  // /health → /api/health
  let path = endpoint;
  if (path.startsWith('/internal/accounts')) {
    path = path.replace('/internal/accounts', '');
  } else if (path.startsWith('/internal/')) {
    // Map /internal/onboarding → /onboarding, /internal/resources → /resources
    path = path.replace('/internal', '');
  }

  const url = path === '/health'
    ? `${API_GATEWAY_URL}/api/health`
    : `${API_GATEWAY_URL}/v1/accounts${path}`;

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
    credentials: 'include', // Send HttpOnly cookies for auth
    headers,
    ...options,
  });

  // Auto-refresh on 401
  if (response.status === 401 && _retry) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return connectorFetch(endpoint, options, false);
    }
    throw new Error('Session expired. Please sign in again.');
  }

  if (!response.ok) {
    let errorData: any;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: 'Request failed' };
    }
    
    // Handle Pydantic validation errors (array of errors)
    let errorMessage: string;
    if (Array.isArray(errorData.detail)) {
      errorMessage = errorData.detail.map((e: any) => `${e.loc?.join('.') || 'field'}: ${e.msg}`).join(', ');
    } else if (typeof errorData.detail === 'string') {
      errorMessage = errorData.detail;
    } else if (typeof errorData.detail === 'object') {
      errorMessage = JSON.stringify(errorData.detail);
    } else {
      errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    }
    
    throw new Error(errorMessage);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  return response.json();
}

// ─── Account CRUD ────────────────────────────────────────────────────────────

export const connectorAPI = {
  /**
   * List all cloud accounts for an organization
   */
  async listAccounts(organizationId?: string): Promise<AccountListResponse> {
    const params = organizationId ? `?organization_id=${organizationId}` : '';
    return connectorFetch(`/internal/accounts${params}`);
  },

  /**
   * Get a specific cloud account by ID
   */
  async getAccount(accountId: string): Promise<CloudAccount> {
    return connectorFetch(`/internal/accounts/${accountId}`);
  },

  /**
   * Create a new cloud account (credentials stored in Vault if enabled)
   */
  async createAccount(data: CreateAccountRequest): Promise<CloudAccount> {
    return connectorFetch('/internal/accounts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update cloud account configuration
   */
  async updateAccount(
    accountId: string,
    data: UpdateAccountRequest
  ): Promise<CloudAccount> {
    return connectorFetch(`/internal/accounts/${accountId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Remove a cloud account
   */
  async deleteAccount(accountId: string): Promise<void> {
    return connectorFetch(`/internal/accounts/${accountId}`, {
      method: 'DELETE',
    });
  },

  // ─── Sync Operations ─────────────────────────────────────────────────────

  /**
   * Trigger an immediate sync for an account
   */
  async triggerSync(
    accountId: string,
    correlationId?: string
  ): Promise<SyncTriggerResponse> {
    return connectorFetch(`/internal/accounts/${accountId}/sync`, {
      method: 'POST',
      body: JSON.stringify({ correlation_id: correlationId }),
    });
  },

  /**
   * Get detailed health status for an account
   */
  async getAccountHealth(accountId: string): Promise<AccountHealthResponse> {
    return connectorFetch(`/internal/accounts/${accountId}/health`);
  },

  // ─── Onboarding ──────────────────────────────────────────────────────────

  /**
   * Get CloudFormation template for AWS onboarding
   */
  async getAwsTemplate(): Promise<OnboardingResponse> {
    return connectorFetch('/internal/onboarding/aws/template');
  },

  /**
   * Get Azure service principal setup instructions
   */
  async getAzureInstructions(): Promise<OnboardingResponse> {
    return connectorFetch('/internal/onboarding/azure/instructions');
  },

  /**
   * Get GCP service account setup instructions
   */
  async getGcpInstructions(): Promise<OnboardingResponse> {
    return connectorFetch('/internal/onboarding/gcp/instructions');
  },

  /**
   * Get OCI setup instructions
   */
  async getOciInstructions(): Promise<OnboardingResponse> {
    return connectorFetch('/internal/onboarding/oci/instructions');
  },

  // ─── Health ──────────────────────────────────────────────────────────────

  /**
   * Check connector service health
   */
  async healthCheck(): Promise<{ status: string; service: string }> {
    return connectorFetch('/health');
  },

  // ─── Resources ───────────────────────────────────────────────────────────

  /**
   * List discovered resources with optional filters
   */
  async listResources(params?: {
    account_id?: string;
    account_ids?: string[];
    provider?: string;
    resource_type?: string;
    region?: string;
    search?: string;
    is_public?: boolean;
    environment?: string;
    limit?: number;
    offset?: number;
  }): Promise<ResourceListResponse> {
    const query = new URLSearchParams();
    if (params?.account_id) query.set('account_id', params.account_id);
    if (params?.account_ids && params.account_ids.length > 0) query.set('account_ids', params.account_ids.join(','));
    if (params?.provider) query.set('provider', params.provider);
    if (params?.resource_type) query.set('resource_type', params.resource_type);
    if (params?.region) query.set('region', params.region);
    if (params?.search) query.set('search', params.search);
    if (params?.is_public !== undefined) query.set('is_public', String(params.is_public));
    if (params?.environment) query.set('environment', params.environment);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return connectorFetch(`/internal/resources${qs ? `?${qs}` : ''}`);
  },

  /**
   * Get resource counts summary grouped by provider and type
   */
  async getResourcesSummary(accountId?: string, provider?: string): Promise<ResourceSummary> {
    const query = new URLSearchParams();
    if (accountId) query.set('account_id', accountId);
    else if (provider) query.set('provider', provider);
    const qs = query.toString();
    return connectorFetch(`/internal/resources/summary${qs ? `?${qs}` : ''}`);
  },

  // ─── Sync Status ─────────────────────────────────────────────────────────

  /**
   * Get live sync progress for an account.
   * Returns the in-flight or most-recent sync's progress snapshot.
   * Used by the "Run scan" button to show live progress in a Flashbar.
   */
  async getSyncStatus(accountId: string): Promise<SyncStatusResponse> {
    return connectorFetch(`/internal/accounts/${accountId}/sync/status`);
  },

  // ─── Credential Rotation ─────────────────────────────────────────────────

  /**
   * Rotate credentials for an existing cloud account.
   * Encrypts new credentials, validates connectivity, and updates storage.
   */
  async rotateCredentials(
    accountId: string,
    credentials: CloudAccountCredentials
  ): Promise<CredentialRotateResponse> {
    return connectorFetch(`/internal/accounts/${accountId}/credentials/rotate`, {
      method: 'POST',
      body: JSON.stringify({ credentials }),
    });
  },

  // ─── Scan History ────────────────────────────────────────────────────────

  /**
   * Get paginated scan history for an account.
   * Returns past sync operations with resource counts, duration, and errors.
   */
  async getScanHistory(
    accountId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<ScanHistoryResponse> {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return connectorFetch(`/internal/accounts/${accountId}/scans${qs ? `?${qs}` : ''}`);
  },

  // ─── Resource Type Catalog ───────────────────────────────────────────────

  /**
   * Get the complete catalog of supported resource types per provider.
   * Used to populate resource-type filter dropdowns in the asset explorer.
   */
  async getResourceTypeCatalog(): Promise<ResourceTypeCatalog> {
    return connectorFetch('/internal/resources/catalog');
  },
};

export default connectorAPI;
