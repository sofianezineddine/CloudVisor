/**
 * CSPM API client — all requests go through the API gateway at /v1/cspm/*
 * account_ids is always passed when a scope is active.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005';

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

// ─── Core fetch ───────────────────────────────────────────────────────────────

async function gw<T>(path: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
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
      }),
    }),

  getScanResources: (scanId: string) =>
    gw<{ scan_id: string; resources: CSPMResource[]; total: number }>(
      `/v1/cspm/scans/${scanId}/resources`
    ),

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
};
