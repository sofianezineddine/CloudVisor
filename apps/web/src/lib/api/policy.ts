/**
 * Policy Service API Client — Foundation Service 4
 * Connects to the policy service at port 8003.
 */

const POLICY_BASE_URL =
  process.env.NEXT_PUBLIC_POLICY_SERVICE_URL || 'http://localhost:8003';

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

function getOrgId(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const token = localStorage.getItem('access_token');
    if (!token) return null;
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.org_id || null;
  } catch {
    return null;
  }
}

async function policyFetch(endpoint: string, options: RequestInit = {}): Promise<any> {
  const url = `${POLICY_BASE_URL}${endpoint}`;
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

export interface ComplianceControl {
  id: string;
  rule_id: string;
  title: string;
  severity: string;
  status: 'pass' | 'fail' | 'not_applicable';
}

export interface CompliancePosture {
  framework: string;
  display_name: string;
  total_controls: number;
  passing: number;
  failing: number;
  not_applicable: number;
  percentage: number;
  controls: ComplianceControl[];
}

export interface ComplianceSummary {
  frameworks: CompliancePosture[];
}

export interface PolicyRule {
  id: string;
  rule_id: string;
  title: string;
  description?: string;
  severity: string;
  category: string;
  provider?: string;
  resource_type?: string;
  remediation?: string;
  version: string;
  compliance_mapping: Array<{ framework: string; control: string }>;
  tags: string[];
  is_builtin: boolean;
  is_custom: boolean;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface EvaluationFinding {
  rule_id: string;
  title: string;
  description: string;
  severity: string;
  category: string;
  provider?: string;
  resource_type?: string;
  resource_id: string;
  resource_name: string;
  remediation?: string;
  compliance_mapping: Array<{ framework: string; control: string }>;
}

// ─── API ──────────────────────────────────────────────────────────────────────

export const policyAPI = {
  /** Get compliance posture for all frameworks */
  async getComplianceSummary(orgId?: string): Promise<ComplianceSummary> {
    const id = orgId || getOrgId() || 'default';
    return policyFetch(`/policy/compliance?x_org_id=${id}`);
  },

  /** Get compliance posture for a specific framework */
  async getCompliancePosture(framework: string, orgId?: string): Promise<CompliancePosture> {
    const id = orgId || getOrgId() || 'default';
    return policyFetch(`/policy/compliance/${encodeURIComponent(framework)}?x_org_id=${id}`);
  },

  /** Get evidence for a compliance control */
  async getEvidence(framework: string, controlId: string, orgId?: string): Promise<any> {
    const id = orgId || getOrgId() || 'default';
    return policyFetch(
      `/policy/compliance/${encodeURIComponent(framework)}/evidence?control_id=${encodeURIComponent(controlId)}&x_org_id=${id}`
    );
  },

  /** List all rules */
  async listRules(params?: {
    orgId?: string;
    category?: string;
    provider?: string;
    severity?: string;
  }): Promise<{ rules: PolicyRule[]; total: number }> {
    const id = params?.orgId || getOrgId() || 'default';
    const q = new URLSearchParams({ x_org_id: id });
    if (params?.category) q.set('category', params.category);
    if (params?.provider) q.set('provider', params.provider);
    if (params?.severity) q.set('severity', params.severity);
    return policyFetch(`/policy/rules?${q}`);
  },

  /** Evaluate resources against rules */
  async evaluate(resources: any[], orgId?: string, category?: string): Promise<{
    findings: EvaluationFinding[];
    evaluated_count: number;
  }> {
    const id = orgId || getOrgId() || 'default';
    return policyFetch(`/policy/evaluate?x_org_id=${id}`, {
      method: 'POST',
      body: JSON.stringify({ resources, category }),
    });
  },

  /** Disable a rule for an org */
  async disableRule(ruleId: string, reason: string, expiresInDays?: number, orgId?: string): Promise<void> {
    const id = orgId || getOrgId() || 'default';
    await policyFetch(`/policy/rules/${ruleId}/disable?x_org_id=${id}`, {
      method: 'POST',
      body: JSON.stringify({ reason, expires_in_days: expiresInDays }),
    });
  },

  /** Re-enable a rule */
  async enableRule(ruleId: string, orgId?: string): Promise<void> {
    const id = orgId || getOrgId() || 'default';
    await policyFetch(`/policy/rules/${ruleId}/enable?x_org_id=${id}`, { method: 'POST' });
  },
};

export default policyAPI;
