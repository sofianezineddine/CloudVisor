'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Shield, Plus, Loader2, AlertTriangle, X, ChevronRight,
  CheckCircle2, Play, RotateCcw, History,
} from 'lucide-react';
import { toast } from 'sonner';
import policyAPI, { type PolicyRule, type DryRunResult } from '@/lib/api/policy';

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'var(--critical)',
  HIGH: 'var(--high)',
  MEDIUM: 'var(--medium)',
  LOW: 'var(--low)',
  INFO: 'var(--info)',
};

// ─── Rule Detail Panel ────────────────────────────────────────────────────────

function RuleDetailPanel({ rule, onClose }: { rule: PolicyRule; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [disableReason, setDisableReason] = React.useState('');
  const [expiresInDays, setExpiresInDays] = React.useState('');
  const [showDisable, setShowDisable] = React.useState(false);

  const disableMutation = useMutation({
    mutationFn: () => policyAPI.disableRule(
      rule.rule_id,
      disableReason || undefined,
      expiresInDays ? parseInt(expiresInDays) : undefined,
    ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      toast.success('Rule disabled for your organization');
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const enableMutation = useMutation({
    mutationFn: () => policyAPI.enableRule(rule.rule_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      toast.success('Rule re-enabled');
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex flex-col shadow-2xl"
      style={{ width: 440, backgroundColor: 'var(--bg-surface)', borderLeft: '1px solid var(--border-default)' }}>
      <div className="flex items-center justify-between px-5 py-4 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border-default)' }}>
        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Rule Detail</h3>
        <button onClick={onClose} className="rounded p-1 transition-colors" style={{ color: 'var(--text-tertiary)' }}>
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {/* Header */}
        <div>
          <p className="text-xs font-mono mb-1" style={{ color: 'var(--text-tertiary)' }}>{rule.rule_id}</p>
          <h4 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>{rule.title}</h4>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span className="text-xs font-semibold" style={{ color: SEVERITY_COLORS[rule.severity] || 'var(--text-secondary)' }}>
              {rule.severity}
            </span>
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>·</span>
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{rule.category}</span>
            {rule.provider && (
              <>
                <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>·</span>
                <span className="text-xs uppercase" style={{ color: 'var(--text-tertiary)' }}>{rule.provider}</span>
              </>
            )}
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>·</span>
            <span className="inline-flex items-center gap-1 text-xs"
              style={{ color: rule.is_enabled ? 'var(--success)' : 'var(--text-tertiary)' }}>
              <span className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: rule.is_enabled ? 'var(--success)' : 'var(--text-tertiary)' }} />
              {rule.is_enabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </div>

        {rule.description && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-tertiary)' }}>Description</p>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{rule.description}</p>
          </div>
        )}

        {rule.resource_type && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-tertiary)' }}>Resource Type</p>
            <code className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>{rule.resource_type}</code>
          </div>
        )}

        {rule.remediation && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-tertiary)' }}>Remediation</p>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{rule.remediation}</p>
          </div>
        )}

        {rule.compliance_mapping?.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--text-tertiary)' }}>Compliance</p>
            <div className="flex flex-wrap gap-1.5">
              {rule.compliance_mapping.map((m: any, i: number) => (
                <span key={i} className="rounded px-2 py-0.5 text-xs"
                  style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                  {typeof m === 'string' ? m : `${m.framework} ${m.control}`}
                </span>
              ))}
            </div>
          </div>
        )}

        {rule.tags?.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--text-tertiary)' }}>Tags</p>
            <div className="flex flex-wrap gap-1.5">
              {rule.tags.map((tag, i) => (
                <span key={i} className="rounded-full px-2 py-0.5 text-xs"
                  style={{ backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>
          <span>v{rule.version}</span>
          {rule.is_builtin && <span className="rounded px-1.5 py-0.5" style={{ backgroundColor: 'var(--bg-elevated)' }}>Built-in</span>}
          {rule.is_custom && <span className="rounded px-1.5 py-0.5" style={{ backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}>Custom</span>}
        </div>

        {/* Enable / Disable actions */}
        <div className="pt-2 border-t" style={{ borderColor: 'var(--border-faint)' }}>
          {rule.is_enabled ? (
            !showDisable ? (
              <Button variant="outline" size="sm" className="gap-1.5 text-xs w-full"
                onClick={() => setShowDisable(true)}>
                Disable this rule for my org
              </Button>
            ) : (
              <div className="space-y-2">
                <input
                  type="text"
                  value={disableReason}
                  onChange={e => setDisableReason(e.target.value)}
                  placeholder="Reason for disabling (optional)"
                  className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
                />
                <select
                  value={expiresInDays}
                  onChange={e => setExpiresInDays(e.target.value)}
                  className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
                >
                  <option value="">Never expires</option>
                  <option value="7">Expires in 7 days</option>
                  <option value="30">Expires in 30 days</option>
                  <option value="90">Expires in 90 days</option>
                </select>
                <div className="flex gap-2">
                  <Button size="sm" className="gap-1.5 text-xs flex-1"
                    onClick={() => disableMutation.mutate()}
                    disabled={disableMutation.isPending}>
                    {disableMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                    Confirm Disable
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setShowDisable(false)}>Cancel</Button>
                </div>
              </div>
            )
          ) : (
            <Button size="sm" className="gap-1.5 text-xs w-full"
              onClick={() => enableMutation.mutate()}
              disabled={enableMutation.isPending}>
              {enableMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
              Re-enable this rule
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Create Custom Rule Form ──────────────────────────────────────────────────

function CreateCustomRuleForm({ onSuccess, onCancel }: { onSuccess: () => void; onCancel: () => void }) {
  const [form, setForm] = React.useState({
    title: '',
    description: '',
    severity: 'MEDIUM',
    category: 'custom',
    remediation: '',
    rego_code: `package custom.my_rule

import future.keywords

deny[msg] {
    # Your rule logic here
    input.resource.resource_type == "aws::s3::bucket"
    input.resource.is_public == true
    msg := sprintf("S3 bucket '%v' is publicly accessible", [input.resource.name])
}`,
  });
  const [error, setError] = React.useState<string | null>(null);
  const [dryRunResult, setDryRunResult] = React.useState<DryRunResult | null>(null);
  const [dryRunLoading, setDryRunLoading] = React.useState(false);

  const createMutation = useMutation({
    mutationFn: () => policyAPI.createCustomRule(form),
    onSuccess: () => { setError(null); onSuccess(); },
    onError: (e: Error) => setError(e.message),
  });

  const handleDryRun = async () => {
    if (!form.rego_code.trim()) {
      setError('Rego code is required for dry run');
      return;
    }
    setDryRunLoading(true);
    setError(null);
    try {
      // Use a sample resource for dry run
      const sampleResource = {
        resource_type: 'aws::s3::bucket',
        name: 'test-bucket',
        is_public: true,
        provider: 'aws',
        raw: {},
      };
      const result = await policyAPI.dryRun(form.rego_code, [sampleResource]);
      setDryRunResult(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setDryRunLoading(false);
    }
  };

  return (
    <div className="cv-container p-5 space-y-4">
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Create Custom Rule</h3>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border p-3 text-sm"
          style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}>
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Title *</label>
          <input value={form.title} onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
            placeholder="e.g. S3 bucket must have versioning enabled"
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Severity</label>
          <select value={form.severity} onChange={e => setForm(p => ({ ...p, severity: e.target.value }))}
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
            {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'].map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Category</label>
          <input value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))}
            placeholder="custom"
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Description</label>
          <textarea value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
            rows={2} placeholder="What does this rule check?"
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none resize-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
        </div>
        <div className="sm:col-span-2">
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Rego Policy *</label>
            <Button variant="outline" size="sm" className="gap-1.5 text-xs h-6"
              onClick={handleDryRun} disabled={dryRunLoading || !form.rego_code.trim()}>
              {dryRunLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
              Test (Dry Run)
            </Button>
          </div>
          <textarea value={form.rego_code} onChange={e => setForm(p => ({ ...p, rego_code: e.target.value }))}
            rows={12}
            className="w-full rounded-md border px-3 py-2 text-xs font-mono focus:outline-none resize-y"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)' }} />
        </div>
      </div>

      {/* Dry run results */}
      {dryRunResult && (
        <div className="rounded-lg border p-4 space-y-2"
          style={{
            borderColor: dryRunResult.success ? 'var(--success)' : 'var(--critical)',
            backgroundColor: dryRunResult.success ? 'var(--success-bg)' : 'var(--critical-dim)',
          }}>
          <div className="flex items-center gap-2">
            {dryRunResult.success
              ? <CheckCircle2 className="h-4 w-4 flex-shrink-0" style={{ color: 'var(--success)' }} />
              : <AlertTriangle className="h-4 w-4 flex-shrink-0" style={{ color: 'var(--critical)' }} />}
            <span className="text-sm font-semibold"
              style={{ color: dryRunResult.success ? 'var(--success)' : 'var(--critical)' }}>
              {dryRunResult.success
                ? `Dry run passed — ${dryRunResult.findings?.length ?? 0} finding(s) on sample resource`
                : `Dry run failed: ${dryRunResult.error}`}
            </span>
          </div>
          {dryRunResult.success && dryRunResult.findings && dryRunResult.findings.length > 0 && (
            <div className="space-y-1 mt-2">
              {dryRunResult.findings.map((f: any, i: number) => (
                <div key={i} className="text-xs font-mono rounded px-2 py-1"
                  style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)' }}>
                  {f.message || f.description || JSON.stringify(f)}
                </div>
              ))}
            </div>
          )}
          {dryRunResult.success && dryRunResult.findings?.length === 0 && (
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              No violations found on the sample resource. The rule is syntactically valid.
            </p>
          )}
        </div>
      )}

      <div className="flex gap-3 pt-1">
        <Button onClick={() => createMutation.mutate()} disabled={!form.title || !form.rego_code || createMutation.isPending} className="gap-2">
          {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Create Rule
        </Button>
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function RulesPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = React.useState(false);
  const [selectedRule, setSelectedRule] = React.useState<PolicyRule | null>(null);
  const [categoryFilter, setCategoryFilter] = React.useState('');
  const [severityFilter, setSeverityFilter] = React.useState('');

  React.useEffect(() => { document.title = 'Security Rules - Settings - CloudVisor'; }, []);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['rules', categoryFilter, severityFilter],
    queryFn: () => policyAPI.listRules({
      category: categoryFilter || undefined,
      severity: severityFilter || undefined,
    }),
    // listRules() already normalizes to { rules, total }
    select: (d) => (d?.rules ?? []) as PolicyRule[],
  });

  const rules = data ?? [];
  const enabledCount = rules.filter(r => r.is_enabled !== false).length;
  const disabledCount = rules.length - enabledCount;

  return (
    <>
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Security Rules</h1>
            {!isLoading && rules.length > 0 && (
              <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
                {rules.length} rules · {enabledCount} enabled · {disabledCount} disabled
              </p>
            )}
          </div>
          <Button className="gap-2" onClick={() => setShowCreate(v => !v)}>
            {showCreate ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showCreate ? 'Cancel' : 'Custom Rule'}
          </Button>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Manage built-in and custom security rules. Disable rules that don't apply to your environment.
        </p>
      </div>

      {showCreate && (
        <div className="mb-4">
          <CreateCustomRuleForm
            onSuccess={() => {
              setShowCreate(false);
              queryClient.invalidateQueries({ queryKey: ['rules'] });
              toast.success('Custom rule created');
            }}
            onCancel={() => setShowCreate(false)}
          />
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}
          className="rounded-md border px-3 py-2 text-sm focus:outline-none"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All categories</option>
          <option value="cspm">CSPM</option>
          <option value="cwpp">CWPP</option>
          <option value="ciem">CIEM</option>
          <option value="kspm">KSPM</option>
          <option value="cdr">CDR</option>
          <option value="cicd">CI/CD</option>
          <option value="custom">Custom</option>
        </select>
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}
          className="rounded-md border px-3 py-2 text-sm focus:outline-none"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All severities</option>
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'].map(s => <option key={s}>{s}</option>)}
        </select>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
        </div>
      ) : isError ? (
        <div className="cv-container p-8 flex flex-col items-center gap-3 text-center">
          <AlertTriangle className="h-8 w-8" style={{ color: 'var(--warning)' }} />
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Could not load rules</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Retry</Button>
        </div>
      ) : rules.length === 0 ? (
        <div className="cv-container p-12 flex flex-col items-center gap-3 text-center">
          <Shield className="h-10 w-10" style={{ color: 'var(--text-tertiary)' }} />
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No rules found</p>
        </div>
      ) : (
        <div className="cv-container overflow-hidden">
          <table className="w-full">
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-elevated)', borderBottom: '1px solid var(--border-faint)' }}>
                {['Severity', 'Title', 'Category', 'Provider', 'Status', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium"
                    style={{ color: 'var(--text-secondary)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id || rule.rule_id}
                  className="border-b cursor-pointer transition-colors"
                  style={{ borderColor: 'var(--border-faint)' }}
                  onClick={() => setSelectedRule(rule)}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                  <td className="px-4 py-3">
                    <span className="text-xs font-semibold"
                      style={{ color: SEVERITY_COLORS[rule.severity] || 'var(--text-secondary)' }}>
                      {rule.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm font-medium truncate max-w-xs" style={{ color: 'var(--text-primary)' }}>
                      {rule.title}
                    </div>
                    <div className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
                      {rule.rule_id}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs" style={{ color: 'var(--text-secondary)' }}>{rule.category}</td>
                  <td className="px-4 py-3 text-xs uppercase" style={{ color: 'var(--text-secondary)' }}>{rule.provider || '—'}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 text-xs"
                      style={{ color: rule.is_enabled !== false ? 'var(--success)' : 'var(--text-tertiary)' }}>
                      <span className="h-1.5 w-1.5 rounded-full"
                        style={{ backgroundColor: rule.is_enabled !== false ? 'var(--success)' : 'var(--text-tertiary)' }} />
                      {rule.is_enabled !== false ? 'Enabled' : 'Disabled'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <ChevronRight className="h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedRule && (
        <>
          <div className="fixed inset-0 z-40 bg-black/20" onClick={() => setSelectedRule(null)} />
          <RuleDetailPanel rule={selectedRule} onClose={() => setSelectedRule(null)} />
        </>
      )}
    </>
  );
}
