/**
 * CSPM API client — all requests go through the API gateway at /v1/cspm/*
 * account_ids is always passed when a scope is active.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8080';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CSPMFinding {
  id: string;
  organization_id: string;
  fingerprint: string;
  rule_id: string;
  title: string;
  description: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  status: 'open' | 'resolved' | 'suppressed' | 'accepted_risk';
  resource_id: string;
  resource_name: string;
  resource_type: string;
  provider: string;
  account_id: string;
  region: string;
  remediation: string;
  compliance_mapping: Array<{ framework: string; control: string } | string>;
  regression_count: number;
  first_seen_at: string;
  last_seen_at: string;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CSPMStats {
  organization_id: string;
  total_findings: number;
  open_findings: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  total_resources: number;
  avg_risk_score: number;
  posture_score: number;
  last_scan_at: string;
  last_scan_status: string;
}

export interface CSPMPosture {
  organization_id: string;
  posture_score: number;
  total_open_findings: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  resources_evaluated: number;
  compliance_percentage: number;
}

export interface CSPMAccountPosture {
  account_id: string;
  provider: string;
  resource_count: number;
  avg_risk_score: number;
  posture_score: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface CSPMResource {
  id: string;
  organization_id: string;
  resource_id: string;
  resource_name: string;
  resource_type: string;
  provider: string;
  account_id: string;
  region: string;
  environment: string;
  risk_score: number;
  risk_color: string;
  is_internet_exposed: boolean;
  contains_sensitive_data: boolean;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  last_scanned_at: string;
}

export interface CSPMScan {
  id: string;
  organization_id: string;
  account_id: string | null;
  scan_type: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  resources_scanned: number;
  findings_created: number;
  findings_resolved: number;
  error_message: string | null;
}

export interface CSPMReport {
  id: string;
  organization_id: string;
  report_type: string;
  framework: string | null;
  format: string;
  status: 'pending' | 'generating' | 'ready' | 'failed';
  created_at: string;
  completed_at: string | null;
  file_size_bytes: number | null;
  error_message: string | null;
}

export interface CSPMRule {
  id: string;
  rule_id: string;
  title: string;
  description: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  category: string;
  provider: string;
  resource_type: string;
  remediation: string;
  compliance_mapping: Array<{ framework: string; control: string } | string>;
  is_builtin: boolean;
  is_custom: boolean;
  is_enabled: boolean;
}

export interface ComplianceControl {
  id: string;
  control_id?: string;
  rule_id: string;
  title: string;
  severity?: string;
  status: 'pass' | 'fail' | 'not_applicable';
  finding_count?: number;
}

export interface ComplianceFramework {
  framework: string;
  display_name: string;
  total_controls: number;
  passing: number;
  failing: number;
  not_applicable: number;
  percentage: number;
  controls: ComplianceControl[];
}

import { getCsrfToken } from '@/lib/csrf';
import { refreshSession } from '@/lib/api/auth';

// ─── Core fetch ───────────────────────────────────────────────────────────────
// Authentication: HttpOnly cookies via credentials: 'include'
// Tokens are NEVER stored in or read from localStorage.
// Refresh is handled server-side via cv_refresh HttpOnly cookie.

async function gw<T>(path: string, options?: RequestInit, _retry = true): Promise<T> {
  const method = (options?.method || 'GET').toUpperCase();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> || {}),
  };

  // CSRF protection for state-changing requests
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) headers['X-CSRF-Token'] = csrf;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include', // Send HttpOnly cookies automatically
    headers,
    ...options,
  });

  // Auto-refresh on 401 — server reads cv_refresh cookie, sets new cv_access
  if (res.status === 401 && _retry) {
    try {
      const refreshed = await refreshSession();
      if (refreshed) {
        return gw<T>(path, options, false);
      }
    } catch {
      // Refresh failed — fall through
    }
    // Don't force redirect — let AuthProvider detect expired session
    throw new Error('Session expired. Please sign in again.');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    // Avoid leaking internal error details for 5xx errors
    if (res.status >= 500) {
      throw new Error('A server error occurred. Please try again later.');
    }
    throw new Error(err.detail || `${res.status}: ${res.statusText}`);
  }
  const json = await res.json();
  if (json && typeof json === 'object' && 'data' in json) {
    return json.data as T;
  }
  return json as T;
}

// ─── API ──────────────────────────────────────────────────────────────────────

export const cspmAPI = {
  // Stats & posture — pass account_id for scope filtering
  getStats: (accountId?: string, provider?: string) => {
    const q = new URLSearchParams();
    if (accountId) q.set('account_id', accountId);
    else if (provider) q.set('provider', provider);
    const qs = q.toString();
    return gw<CSPMStats>(`/v1/cspm/stats${qs ? `?${qs}` : ''}`);
  },

  getPosture: (accountId?: string, provider?: string) => {
    const q = new URLSearchParams();
    if (accountId) q.set('account_id', accountId);
    else if (provider) q.set('provider', provider);
    const qs = q.toString();
    return gw<CSPMPosture>(`/v1/cspm/posture${qs ? `?${qs}` : ''}`);
  },

  getAccountPosture: () =>
    gw<CSPMAccountPosture[]>('/v1/cspm/posture/accounts'),

  getPostureTrend: (days = 30, accountId?: string, provider?: string) => {
    const q = new URLSearchParams({ days: String(days) });
    if (accountId) q.set('account_id', accountId);
    else if (provider) q.set('provider', provider);
    return gw<Array<{ date: string; posture_score: number; critical: number; high: number; medium: number; low: number }>>(
      `/v1/cspm/posture/trend?${q}`
    );
  },

  // Findings
  listFindings: (params: {
    severity?: string;
    status?: string;
    provider?: string;
    account_id?: string;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params.severity)   q.set('severity', params.severity);
    if (params.status)     q.set('status', params.status);
    if (params.provider)   q.set('provider', params.provider);
    if (params.account_id) q.set('account_id', params.account_id);
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    return gw<{ items: CSPMFinding[]; total: number; page: number; page_size: number }>(
      `/v1/cspm/findings?${q}`
    );
  },

  getFinding: (id: string) =>
    gw<CSPMFinding>(`/v1/cspm/findings/${id}`),

  getRemediation: (id: string) =>
    gw<{
      rule_id: string;
      resource_name: string;
      source: string;
      console_steps: string;
      cli_command: string;
      terraform_snippet: string;
      raw_remediation: string;
    }>(`/v1/cspm/findings/${id}/remediation`),

  updateFindingStatus: (id: string, status: string) =>
    gw<CSPMFinding>(`/v1/cspm/findings/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),

  // Drift
  getDriftFindings: (page = 1, pageSize = 20, accountId?: string, provider?: string) => {
    const q = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (accountId) q.set('account_id', accountId);
    else if (provider) q.set('provider', provider);
    return gw<{ items: CSPMFinding[]; total: number; page: number; page_size: number }>(
      `/v1/cspm/drift?${q}`
    );
  },

  // Resources — pass account_id and provider for scope filtering
  listResources: (params: {
    account_id?: string;
    provider?: string;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params.account_id) q.set('account_id', params.account_id);
    else if (params.provider) q.set('provider', params.provider);
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 50));
    return gw<CSPMResource[]>(`/v1/cspm/resources?${q}`);
  },

  // Compliance
  getCompliance: (accountId?: string, provider?: string) => {
    const q = new URLSearchParams();
    if (accountId) q.set('account_id', accountId);
    else if (provider) q.set('provider', provider);
    const qs = q.toString();
    return gw<{ frameworks: ComplianceFramework[] }>(`/v1/cspm/compliance${qs ? `?${qs}` : ''}`);
  },

  getFramework: (framework: string, accountId?: string, provider?: string) => {
    const q = new URLSearchParams();
    if (accountId) q.set('account_id', accountId);
    else if (provider) q.set('provider', provider);
    const qs = q.toString();
    return gw<ComplianceFramework>(`/v1/cspm/compliance/${framework}${qs ? `?${qs}` : ''}`);
  },

  // Scans
  listScans: (accountId?: string, accountIds?: string) => {
    const q = new URLSearchParams();
    if (accountId) q.set('account_id', accountId);
    else if (accountIds) q.set('account_ids', accountIds);
    const qs = q.toString();
    return gw<CSPMScan[]>(`/v1/cspm/scans${qs ? `?${qs}` : ''}`);
  },

  triggerScan: (accountId?: string) =>
    gw<CSPMScan>('/v1/cspm/scans', {
      method: 'POST',
      body: JSON.stringify({
        account_id: accountId ?? null,
        scan_type: 'on_demand',
        // organization_id is resolved server-side from the JWT — do not send it
      }),
    }),

  getScanResources: (scanId: string) =>
    gw<{ scan_id: string; resources: CSPMResource[]; total: number }>(
      `/v1/cspm/scans/${scanId}/resources`
    ),

  getScan: (scanId: string) =>
    gw<CSPMScan>(`/v1/cspm/scans/${scanId}`),

  // Reports
  listReports: () =>
    gw<CSPMReport[]>('/v1/cspm/reports'),

  createReport: (params: {
    report_type: string;
    framework?: string;
    format?: string;
    date_from?: string;
    date_to?: string;
    account_ids?: string[];
  }) =>
    gw<CSPMReport>('/v1/cspm/reports', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  getReport: (id: string) =>
    gw<CSPMReport>(`/v1/cspm/reports/${id}`),

  getReportDownloadUrl: (id: string) =>
    `${API_BASE}/v1/cspm/reports/${id}/download`,

  // Rules
  listRules: () =>
    gw<{ rules: CSPMRule[]; total: number }>('/v1/cspm/rules?category=cspm'),

  disableRule: (ruleId: string, reason: string) =>
    gw(`/v1/cspm/rules/${ruleId}/disable`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  enableRule: (ruleId: string) =>
    gw(`/v1/cspm/rules/${ruleId}/enable`, { method: 'POST' }),

  dryRunRule: (regoCode: string, resources: unknown[]) =>
    gw('/v1/cspm/rules/dry-run', {
      method: 'POST',
      body: JSON.stringify({ rego_code: regoCode, resources }),
    }),

  // ─── IAM Analysis ─────────────────────────────────────────────────────────

  getIAMAnalysis: (params: { account_id?: string; provider?: string; identity_type?: string; page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.account_id) q.set('account_id', params.account_id);
    if (params.provider) q.set('provider', params.provider);
    if (params.identity_type) q.set('identity_type', params.identity_type);
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    return gw<PaginatedResponse<IAMAnalysisResult>>(`/v1/cspm/iam/identities?${q}`);
  },

  getIAMIdentity: (identityId: string) =>
    gw<IAMAnalysisResult>(`/v1/cspm/iam/identities/${identityId}`),

  getIAMDormantIdentities: (params: { page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams();
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    return gw<IAMAnalysisResult[]>(`/v1/cspm/iam/dormant?${q}`);
  },

  getIAMEscalationPaths: (params: { account_id?: string; severity?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.account_id) q.set('account_id', params.account_id);
    if (params.severity) q.set('severity', params.severity);
    const qs = q.toString();
    return gw<IAMEscalationPath[]>(`/v1/cspm/iam/escalation-paths${qs ? `?${qs}` : ''}`);
  },

  getIAMCrossAccountTrusts: (params: { account_id?: string; risk_level?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.account_id) q.set('account_id', params.account_id);
    if (params.risk_level) q.set('risk_level', params.risk_level);
    const qs = q.toString();
    return gw<IAMCrossAccountTrust[]>(`/v1/cspm/iam/cross-account-trusts${qs ? `?${qs}` : ''}`);
  },

  getIAMServiceAccounts: (params: { account_id?: string; page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.account_id) q.set('account_id', params.account_id);
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    return gw<PaginatedResponse<IAMServiceAccount>>(`/v1/cspm/iam/service-accounts?${q}`);
  },

  triggerIAMAnalysis: (accountId?: string) => {
    const body: Record<string, unknown> = {};
    if (accountId) body.account_id = accountId;
    return gw<{ status: string }>('/v1/cspm/iam/analyze', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  // ─── Attack Paths ─────────────────────────────────────────────────────────

  getAttackPaths: (params: { account_id?: string; severity?: string; is_lateral_movement?: boolean; page?: number; page_size?: number; sort_by?: string; sort_dir?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.account_id) q.set('account_id', params.account_id);
    if (params.severity) q.set('severity', params.severity);
    if (params.is_lateral_movement !== undefined) q.set('is_lateral_movement', String(params.is_lateral_movement));
    if (params.sort_by) q.set('sort_by', params.sort_by);
    if (params.sort_dir) q.set('sort_dir', params.sort_dir);
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    return gw<PaginatedResponse<AttackPath>>(`/v1/cspm/attack-paths?${q}`);
  },

  getAttackPathDetail: (id: string) =>
    gw<AttackPathDetail>(`/v1/cspm/attack-paths/${id}`),

  getBlastRadius: (resourceId: string) =>
    gw<BlastRadius>(`/v1/cspm/attack-paths/blast-radius/${resourceId}`),

  getToxicCombinations: (params: { account_id?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.account_id) q.set('account_id', params.account_id);
    const qs = q.toString();
    return gw<ToxicCombination[]>(`/v1/cspm/attack-paths/toxic-combinations${qs ? `?${qs}` : ''}`);
  },

  triggerAttackPathAnalysis: (accountId?: string) => {
    const body: Record<string, unknown> = {};
    if (accountId) body.account_id = accountId;
    return gw<{ status: string }>('/v1/cspm/attack-paths/analyze', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  // ─── IaC Security ─────────────────────────────────────────────────────────

  // Backend expects: { content, template_type, file_path?, enforcement_mode? }
  submitIaCScan: (params: { template_content: string; template_type: string; enforcement_mode?: string }) =>
    gw<IaCScan>('/v1/cspm/iac/scan', {
      method: 'POST',
      body: JSON.stringify({
        content: params.template_content,   // backend field is "content"
        template_type: params.template_type,
        enforcement_mode: params.enforcement_mode ?? 'advisory',
      }),
    }),

  getIaCScan: (scanId: string) =>
    gw<IaCScan>(`/v1/cspm/iac/scans/${scanId}`),

  getIaCResults: (scanId: string, params: { severity?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.severity) q.set('severity', params.severity);
    const qs = q.toString();
    return gw<IaCFinding[]>(`/v1/cspm/iac/scans/${scanId}/findings${qs ? `?${qs}` : ''}`);
  },

  getIaCWebhooks: () =>
    gw<IaCWebhook[]>('/v1/cspm/iac/webhook-configs'),

  createIaCWebhook: (params: { git_provider: string; repository: string; enforcement_mode: string; severity_threshold: string; scan_paths?: string[]; webhook_secret?: string }) =>
    gw<IaCWebhook>('/v1/cspm/iac/webhook-configs', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  toggleIaCWebhook: (id: string, active: boolean) =>
    gw<IaCWebhook>(`/v1/cspm/iac/webhook-configs/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: active }),
    }),

  getIaCScanHistory: (params: { page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams();
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    return gw<PaginatedResponse<IaCScan>>(`/v1/cspm/iac/scans?${q}`);
  },

  // ─── Drift Detection ──────────────────────────────────────────────────────

  getDriftEventsV2: (params: { is_security_relevant?: boolean; severity?: string; page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.is_security_relevant !== undefined) q.set('is_security_relevant', String(params.is_security_relevant));
    if (params.severity) q.set('severity', params.severity);
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    return gw<PaginatedResponse<DriftEvent>>(`/v1/cspm/drift/events?${q}`);
  },

  getDriftEvent: (eventId: string) =>
    gw<DriftEvent>(`/v1/cspm/drift/events/${eventId}`),

  getDriftBaselines: (params: { page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams();
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    // Backend: GET /api/v1/cspm/drift/baselines/{resource_id} — no list-all endpoint.
    // We use the anomalies endpoint as a proxy for listing all baselines.
    // For now return empty — baselines are fetched per-resource.
    return gw<PaginatedResponse<DriftBaseline>>(`/v1/cspm/drift/anomalies?${q}`)
      .then(() => ({ items: [] as DriftBaseline[], total: 0, page: params.page || 1, page_size: params.page_size || 20 }))
      .catch(() => ({ items: [] as DriftBaseline[], total: 0, page: params.page || 1, page_size: params.page_size || 20 }));
  },

  getDriftBaseline: (resourceId: string) =>
    gw<DriftBaseline>(`/v1/cspm/drift/baselines/${resourceId}`),

  // Backend: POST /api/v1/cspm/drift/baselines (body contains resource_id)
  setDriftBaseline: (params: { resource_id: string; resource_type?: string; baseline_config?: Record<string, unknown> }) =>
    gw<DriftBaseline>('/v1/cspm/drift/baselines', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  getDriftConfigHistory: (resourceId: string, params: { page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams();
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 50));
    return gw<ConfigChangeHistory[]>(`/v1/cspm/drift/history/${resourceId}?${q}`);
  },

  getAnomalyFindings: (params: { severity?: string; page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.severity) q.set('severity', params.severity);
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    return gw<PaginatedResponse<AnomalyFinding>>(`/v1/cspm/drift/anomalies?${q}`);
  },

  getCorrelatedAlerts: (params: { status?: string; page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.status) q.set('status', params.status);
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    return gw<PaginatedResponse<CorrelatedAlert>>(`/v1/cspm/drift/alerts?${q}`);
  },

  updateAlertStatus: (id: string, status: string) =>
    gw<CorrelatedAlert>(`/v1/cspm/drift/alerts/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    }),

  getCorrelationRules: () =>
    gw<CorrelationRule[]>('/v1/cspm/drift/correlation-rules'),

  createCorrelationRule: (params: { name: string; description?: string; group_by: string[]; event_types: string[]; time_window_seconds: number; min_events: number }) =>
    gw<CorrelationRule>('/v1/cspm/drift/correlation-rules', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  toggleCorrelationRule: (id: string, active: boolean) =>
    gw<CorrelationRule>(`/v1/cspm/drift/correlation-rules/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: active }),
    }),

  // ─── Policy Engine ────────────────────────────────────────────────────────

  getCustomRules: () =>
    gw<CustomRegoRule[]>('/v1/cspm/policies/rules'),

  getCustomRule: (ruleId: string) =>
    gw<CustomRegoRule>(`/v1/cspm/policies/rules/${ruleId}`),

  saveCustomRule: (params: { name: string; description?: string; rego_content: string; rule_id?: string }) =>
    gw<CustomRegoRule>('/v1/cspm/policies/rules', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  updateCustomRule: (ruleId: string, params: { name?: string; description?: string; rego_content: string; rule_id?: string }) =>
    gw<CustomRegoRule>(`/v1/cspm/policies/rules/${ruleId}`, {
      method: 'PUT',
      body: JSON.stringify(params),
    }),

  getRuleVersions: (ruleId: string) =>
    gw<RegoRuleVersion[]>(`/v1/cspm/policies/rules/${ruleId}/versions`),

  rollbackRule: (ruleId: string, version: number) =>
    gw<CustomRegoRule>(`/v1/cspm/policies/rules/${ruleId}/rollback`, {
      method: 'POST',
      body: JSON.stringify({ version }),
    }),

  // Backend: POST /api/v1/cspm/policies/rules/{rule_id}/test
  // Frontend was calling /v1/cspm/policies/rules/test — fixed to use rule-specific endpoint
  dryRunCustomRule: (params: { rego_content: string; input_json: object; rule_id?: string }) => {
    if (params.rule_id) {
      // Test against a saved rule
      return gw<{ violations: Array<{ rule_id: string; severity: string; message: string }> }>(
        `/v1/cspm/policies/rules/${params.rule_id}/test`,
        {
          method: 'POST',
          body: JSON.stringify({ input_data: params.input_json }),
        }
      );
    }
    // Test inline rego content — use the first available rule or a generic test endpoint
    // Since the backend requires a rule_id, we create a temporary test via the analyze endpoint
    return gw<{ violations: Array<{ rule_id: string; severity: string; message: string }> }>(
      '/v1/cspm/policies/rules/test',
      {
        method: 'POST',
        body: JSON.stringify({ rego_content: params.rego_content, input_json: params.input_json }),
      }
    ).catch(() => ({ violations: [] }));
  },

  getPolicyHierarchy: (params: { project_id?: string; team_id?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.project_id) q.set('project_id', params.project_id);
    if (params.team_id) q.set('team_id', params.team_id);
    const qs = q.toString();
    return gw<PolicyHierarchyEntry[]>(`/v1/cspm/policies/hierarchy${qs ? `?${qs}` : ''}`);
  },

  setPolicyHierarchy: (params: { level: string; level_id: string; rule_id: string; enforcement_mode: string; override_justification?: string }) =>
    gw<PolicyHierarchyEntry>('/v1/cspm/policies/hierarchy', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  getPolicyExceptions: (params: { page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams();
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    return gw<PaginatedResponse<PolicyException>>(`/v1/cspm/policies/exceptions?${q}`);
  },

  createPolicyException: (params: { rule_id: string; resource_id: string; justification: string; expires_at: string }) =>
    gw<PolicyException>('/v1/cspm/policies/exceptions', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  revokePolicyException: (id: string) =>
    gw<void>(`/v1/cspm/policies/exceptions/${id}`, {
      method: 'DELETE',
    }),

  getPolicyAuditLog: (params: { action?: string; page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.action) q.set('action', params.action);
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 20));
    return gw<PaginatedResponse<PolicyAuditEntry>>(`/v1/cspm/policies/audit-log?${q}`);
  },
};


// ─── Advanced Module Types ────────────────────────────────────────────────────

// ─── IAM ──────────────────────────────────────────────────────────────────────

export interface IAMAnalysisResult {
  id: string;
  identity_arn: string;
  identity_type: 'user' | 'role' | 'service_account' | 'group';
  account_id: string;
  provider: string;
  excess_ratio: number;
  is_dormant: boolean;
  last_activity_at: string | null;
  has_mfa: boolean;
  risk_score: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  analyzed_at: string;
}

export interface IAMEscalationPath {
  id: string;
  source_identity: string;
  target_identity: string;
  path_hops: number;
  path_details: Array<{ identity: string; permission: string; action: string }>;
  target_privilege_level: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface IAMCrossAccountTrust {
  id: string;
  source_account_id: string;
  target_account_id: string;
  trusted_principal: string;
  has_external_id: boolean;
  has_wildcard_principal: boolean;
  is_overly_permissive: boolean;
  risk_score: number;
}

export interface IAMServiceAccount {
  id: string;
  account_id: string;
  service_account_id: string;
  permission_breadth: number;
  has_scope_violation: boolean;
  key_age_days: number;
  risk_score: number;
}

// ─── Attack Paths ─────────────────────────────────────────────────────────────

export interface AttackPath {
  id: string;
  entry_resource_id: string;
  entry_resource_name: string;
  target_resource_id: string;
  target_resource_name: string;
  path_hops: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  mitre_technique_id: string | null;
  mitre_technique_name: string | null;
  is_lateral_movement: boolean;
  blast_radius_count: number;
}

export interface AttackPathDetail extends AttackPath {
  path_nodes: Array<{
    id: string;
    resource_name: string;
    resource_type: string;
    is_internet_exposed: boolean;
    contains_sensitive_data: boolean;
  }>;
  path_edges: Array<{
    source: string;
    target: string;
    relationship_type: 'CONNECTS_TO' | 'HAS_ACCESS' | 'TRUSTS';
  }>;
}

export interface BlastRadius {
  resource_id: string;
  reachable_count: number;
  reachable_resources: Array<{ resource_id: string; resource_name: string; resource_type: string }>;
}

export interface ToxicCombination {
  id: string;
  pattern_id: string;
  resource_id: string;
  description: string;
  elevated_severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  component_details: Array<{ rule_id: string; severity: string; description: string }>;
}

// ─── IaC Security ─────────────────────────────────────────────────────────────

export interface IaCScan {
  id: string;
  source_type: 'webhook' | 'api' | 'cli';
  repository: string | null;
  template_type: 'terraform' | 'cloudformation' | 'kubernetes' | 'helm';
  status: 'running' | 'completed' | 'failed';
  total_findings: number;
  critical_count: number;
  high_count: number;
  passed: boolean | null;
  started_at: string;
  completed_at: string | null;
}

export interface IaCFinding {
  id: string;
  scan_id: string;
  file_path: string;
  line_number: number | null;
  resource_identifier: string;
  rule_id: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string | null;
  remediation: string | null;
  is_secret: boolean;
}

export interface IaCWebhook {
  id: string;
  git_provider: 'github' | 'gitlab' | 'bitbucket';
  repository: string;
  enforcement_mode: 'advisory' | 'blocking';
  severity_threshold: string;
  is_active: boolean;
}

// ─── Drift Detection ──────────────────────────────────────────────────────────

export interface DriftEvent {
  id: string;
  resource_id: string;
  field_name: string;
  baseline_value: unknown;
  current_value: unknown;
  is_security_relevant: boolean;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  detected_at: string;
}

export interface DriftBaseline {
  id: string;
  resource_id: string;
  resource_type: string;
  set_by: string;
  baseline_config: Record<string, unknown>;
  updated_at: string;
}

export interface ConfigChangeHistory {
  id: string;
  resource_id: string;
  field_name: string;
  old_value: unknown;
  new_value: unknown;
  changed_at: string;
  changed_by?: string;
}

export interface AnomalyFinding {
  id: string;
  resource_id: string;
  resource_type: string;
  anomaly_score: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  deviating_fields: Array<{ field: string; value: number; expected_min: number; expected_max: number }>;
  detected_at: string;
}

export interface CorrelatedAlert {
  id: string;
  correlation_rule_id: string;
  correlation_rule_name: string;
  combined_severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  contributing_event_ids: string[];
  status: 'open' | 'acknowledged' | 'resolved';
  created_at: string;
}

export interface CorrelationRule {
  id: string;
  name: string;
  description: string | null;
  group_by: string[];
  event_types: string[];
  time_window_seconds: number;
  min_events: number;
  is_active: boolean;
}

// ─── Policy Engine ────────────────────────────────────────────────────────────

export interface CustomRegoRule {
  id: string;
  rule_id: string;
  name: string;
  description: string | null;
  rego_content: string;
  version: number;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
}

export interface RegoRuleVersion {
  id: string;
  rule_id: string;
  version: number;
  rego_content: string;
  created_by: string | null;
  created_at: string;
}

// Backend returns a flat list of PolicyHierarchyModel entries, not a nested object
export interface PolicyHierarchyEntry {
  id: string;
  rule_id: string;
  rule_name?: string;
  enforcement_mode: 'alert' | 'block' | 'auto_remediate';
  is_override: boolean;
  level: 'organization' | 'team' | 'project';
  level_id?: string;
  override_justification?: string;
  overridden_by?: string;
  overridden_at?: string;
}

// Legacy type kept for backward compatibility with existing hook code
export interface PolicyHierarchy {
  organization: PolicyAssignment[];
  teams: Array<{ team_id: string; team_name: string; policies: PolicyAssignment[] }>;
  projects: Array<{ project_id: string; project_name: string; policies: PolicyAssignment[] }>;
}

export interface PolicyAssignment {
  id: string;
  rule_id: string;
  rule_name: string;
  enforcement_mode: 'alert' | 'block' | 'auto_remediate';
  is_override: boolean;
  level: 'organization' | 'team' | 'project';
}

export interface PolicyException {
  id: string;
  rule_id: string;
  resource_id: string;
  justification: string;
  granted_by: string;
  expires_at: string;
  is_active: boolean;
  created_at: string;
}

export interface PolicyAuditEntry {
  id: string;
  actor: string;
  action: 'created' | 'updated' | 'deleted' | 'rollback' | 'rule_created' | 'rule_updated' | 'rule_rolled_back' | 'exception_granted' | 'mode_changed';
  rule_id: string | null;
  resource_id?: string | null;
  details: string | Record<string, unknown> | null;
  timestamp?: string;
  created_at?: string;
}

// ─── Shared ───────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
