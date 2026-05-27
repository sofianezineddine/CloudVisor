/**
 * Policy Service API Client
 *
 * All calls go through the API gateway at :8080/v1/
 * Authentication: HttpOnly cookies via credentials: 'include'
 * Tokens are NEVER stored in or read from localStorage.
 * Refresh is handled server-side via cv_refresh HttpOnly cookie.
 */

import { getCsrfToken } from '@/lib/csrf';
import { refreshSession } from '@/lib/api/auth';

const API_GATEWAY_BASE_URL =
  process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8080';

async function policyFetch(
  endpoint: string,
  options: RequestInit = {},
  _retry = true,
): Promise<any> {
  const url = `${API_GATEWAY_BASE_URL}${endpoint}`;
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
      return policyFetch(endpoint, options, false);
    }
    // Don't force redirect — let AuthProvider detect expired session
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
  created_at?: string;
  updated_at?: string;
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

export interface DryRunResult {
  success: boolean;
  findings: EvaluationFinding[];
  metadata?: Record<string, string>;
  error?: string;
}

export interface RuleVersionHistory {
  version: string;
  changed_at: string;
  changed_by: string | null;
  change_reason: string | null;
}

// ─── API ──────────────────────────────────────────────────────────────────────

export const policyAPI = {
  // ─── Compliance ────────────────────────────────────────────────────────────

  /** GET /v1/compliance — posture for all frameworks */
  async getComplianceSummary(): Promise<ComplianceSummary> {
    return policyFetch('/v1/compliance');
  },

  /** GET /v1/compliance/{framework} — posture for a specific framework */
  async getCompliancePosture(framework: string): Promise<CompliancePosture> {
    return policyFetch(`/v1/compliance/${encodeURIComponent(framework)}`);
  },

  /** GET /v1/compliance/{framework}/evidence — evidence for a control */
  async getEvidence(framework: string, controlId: string): Promise<any> {
    return policyFetch(
      `/v1/compliance/${encodeURIComponent(framework)}/evidence?control_id=${encodeURIComponent(controlId)}`
    );
  },

  // ─── Rules ─────────────────────────────────────────────────────────────────

  /** GET /v1/rules — list all rules with optional filters */
  async listRules(params?: {
    category?: string;
    provider?: string;
    severity?: string;
  }): Promise<{ rules: PolicyRule[]; total: number }> {
    const q = new URLSearchParams();
    if (params?.category) q.set('category', params.category);
    if (params?.provider) q.set('provider', params.provider);
    if (params?.severity) q.set('severity', params.severity);
    const qs = q.toString();
    const result = await policyFetch(`/v1/rules${qs ? `?${qs}` : ''}`);
    // Gateway wraps in { data: [...], total: N } envelope
    const rules = result?.data ?? result?.rules ?? [];
    const total = result?.total ?? result?.meta?.total ?? rules.length;
    return { rules, total };
  },

  /** GET /v1/rules/{id} — get a specific rule */
  async getRule(ruleId: string): Promise<PolicyRule> {
    return policyFetch(`/v1/rules/${encodeURIComponent(ruleId)}`);
  },

  /** POST /v1/rules/custom — create a custom rule */
  async createCustomRule(data: {
    title: string;
    rego_code: string;
    description?: string;
    severity?: string;
    category?: string;
    remediation?: string;
    compliance_mapping?: Array<{ framework: string; control: string }>;
    tags?: string[];
  }): Promise<PolicyRule> {
    return policyFetch('/v1/rules/custom', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /** PUT /v1/rules/custom/{id} — update a custom rule */
  async updateCustomRule(ruleId: string, data: {
    rego_code?: string;
    title?: string;
    description?: string;
    remediation?: string;
    compliance_mapping?: Array<{ framework: string; control: string }>;
  }): Promise<PolicyRule> {
    return policyFetch(`/v1/rules/custom/${encodeURIComponent(ruleId)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /** DELETE /v1/rules/custom/{id} — delete a custom rule */
  async deleteCustomRule(ruleId: string): Promise<void> {
    await policyFetch(`/v1/rules/custom/${encodeURIComponent(ruleId)}`, { method: 'DELETE' });
  },

  /** POST /v1/rules/{id}/disable — disable a rule for this org */
  async disableRule(ruleId: string, reason?: string, expiresInDays?: number): Promise<void> {
    await policyFetch(`/v1/rules/${encodeURIComponent(ruleId)}/disable`, {
      method: 'POST',
      body: JSON.stringify({
        reason: reason || null,
        expires_in_days: expiresInDays || null,
      }),
    });
  },

  /** POST /v1/rules/{id}/enable — re-enable a disabled rule */
  async enableRule(ruleId: string): Promise<void> {
    await policyFetch(`/v1/rules/${encodeURIComponent(ruleId)}/enable`, { method: 'POST' });
  },

  // ─── Evaluation ────────────────────────────────────────────────────────────

  /** POST /v1/rules/evaluate — evaluate resources against rules */
  async evaluate(resources: any[], category?: string, ruleIds?: string[]): Promise<{
    findings: EvaluationFinding[];
    evaluated_count: number;
  }> {
    return policyFetch('/v1/rules/evaluate', {
      method: 'POST',
      body: JSON.stringify({ resources, category, rule_ids: ruleIds }),
    });
  },

  /** POST /v1/rules/evaluate/dry-run — test a custom rule without creating findings */
  async dryRun(regoCode: string, resources: any[]): Promise<DryRunResult> {
    return policyFetch('/v1/rules/evaluate/dry-run', {
      method: 'POST',
      body: JSON.stringify({ rego_code: regoCode, resources }),
    });
  },

  // ─── Custom rule version history ───────────────────────────────────────────

  /** GET /v1/rules/custom/{id}/history — version history for a custom rule */
  async getRuleHistory(ruleId: string): Promise<{ rule_id: string; history: RuleVersionHistory[] }> {
    return policyFetch(`/v1/rules/custom/${encodeURIComponent(ruleId)}/history`);
  },

  /** POST /v1/rules/custom/{id}/rollback — rollback to a previous version */
  async rollbackRule(ruleId: string, targetVersion: string): Promise<PolicyRule> {
    return policyFetch(`/v1/rules/custom/${encodeURIComponent(ruleId)}/rollback`, {
      method: 'POST',
      body: JSON.stringify({ target_version: targetVersion }),
    });
  },
};

export default policyAPI;
