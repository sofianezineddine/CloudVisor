'use client';

import * as React from 'react';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { Loader2, Settings, Code, Clock, AlertTriangle } from 'lucide-react';
import { RegoEditor } from '@/components/cspm/rego-editor';
import { SkeletonLoader } from '@/components/cspm/skeleton-loader';
import { ErrorBanner } from '@/components/cspm/error-banner';
import {
  useCustomRules,
  useSaveRegoRule,
  useDryRunRule,
  useRuleVersions,
  useRollbackRule,
  usePolicyHierarchy,
  usePolicyExceptions,
  useCreatePolicyException,
  useRevokePolicyException,
  usePolicyAuditLog,
} from '@/hooks/use-cspm';

// ─── Styles ───────────────────────────────────────────────────────────────────

const cellStyle: React.CSSProperties = {
  padding: '8px 12px',
  borderBottom: '1px solid var(--border-default)',
  borderRight: '1px solid var(--border-default)',
  fontSize: '13px',
  color: 'var(--text-primary)',
  verticalAlign: 'middle',
};

const headerCellStyle: React.CSSProperties = {
  ...cellStyle,
  fontWeight: 700,
  fontSize: '12px',
  color: 'var(--text-secondary)',
  backgroundColor: 'var(--bg-elevated)',
  whiteSpace: 'nowrap',
};

const tableStyle: React.CSSProperties = {
  borderCollapse: 'collapse',
  width: '100%',
  border: '1px solid var(--border-default)',
};

const sectionBtnStyle = (active: boolean): React.CSSProperties => ({
  padding: '6px 12px',
  fontSize: '12px',
  fontWeight: active ? 600 : 400,
  color: active ? 'var(--accent)' : 'var(--text-secondary)',
  borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
  background: 'none',
  cursor: 'pointer',
});


// ─── Component ────────────────────────────────────────────────────────────────

export function PolicyEngineTab() {
  const [activeSection, setActiveSection] = React.useState<'editor' | 'test' | 'versions' | 'hierarchy' | 'exceptions' | 'audit'>('editor');
  const [selectedRuleId, setSelectedRuleId] = React.useState<string | null>(null);
  const [regoContent, setRegoContent] = React.useState('package cloudvisor.policy\n\ndefault allow = false\n');
  const [ruleName, setRuleName] = React.useState('');
  const [testInput, setTestInput] = React.useState('{}');
  const [testResults, setTestResults] = React.useState<any[] | null>(null);
  const [testError, setTestError] = React.useState<string | null>(null);
  const [auditPage, setAuditPage] = React.useState(1);
  const [auditActionFilter, setAuditActionFilter] = React.useState<string | null>(null);

  // Exception form
  const [excRuleId, setExcRuleId] = React.useState('');
  const [excResourceId, setExcResourceId] = React.useState('');
  const [excJustification, setExcJustification] = React.useState('');
  const [excExpiresAt, setExcExpiresAt] = React.useState('');

  const { data: customRules, isLoading: rulesLoading, error: rulesError } = useCustomRules();
  const saveRule = useSaveRegoRule();
  const dryRun = useDryRunRule();
  const { data: versionsData, isLoading: versionsLoading } = useRuleVersions(selectedRuleId);
  const rollbackRule = useRollbackRule();
  const { data: hierarchyData, isLoading: hierarchyLoading } = usePolicyHierarchy({});
  const { data: exceptionsData, isLoading: exceptionsLoading } = usePolicyExceptions({});
  const createException = useCreatePolicyException();
  const revokeException = useRevokePolicyException();
  const { data: auditData, isLoading: auditLoading } = usePolicyAuditLog({ action: auditActionFilter ?? undefined, page: auditPage, page_size: 10 });

  const rules = customRules ?? [];
  const versions = versionsData ?? [];
  const hierarchy = hierarchyData;
  const exceptions = exceptionsData?.items ?? [];
  const auditItems = auditData?.items ?? [];
  const auditTotal = auditData?.total ?? 0;
  const auditTotalPages = Math.ceil(auditTotal / 10);

  // Load rule into editor when selected
  React.useEffect(() => {
    if (selectedRuleId) {
      const rule = rules.find((r: any) => r.id === selectedRuleId);
      if (rule) {
        setRegoContent(rule.rego_content);
        setRuleName(rule.name);
      }
    }
  }, [selectedRuleId, rules]);

  const handleSaveRule = () => {
    if (!ruleName.trim() || !regoContent.trim()) return;
    saveRule.mutate({ name: ruleName, rego_content: regoContent });
  };

  const handleRunTest = () => {
    setTestError(null);
    setTestResults(null);
    try {
      const parsed = JSON.parse(testInput);
      dryRun.mutate({ rego_content: regoContent, input_json: parsed }, {
        onSuccess: (data: any) => {
          setTestResults(data?.violations ?? []);
        },
        onError: (err: any) => {
          setTestError(err?.message ?? 'Test execution failed');
        },
      });
    } catch {
      setTestError('Invalid JSON input');
    }
  };

  const handleRollback = (version: number) => {
    if (!selectedRuleId) return;
    rollbackRule.mutate({ ruleId: selectedRuleId, version });
  };

  const handleCreateException = () => {
    if (!excRuleId.trim() || !excResourceId.trim() || !excJustification.trim() || !excExpiresAt) return;
    createException.mutate({
      rule_id: excRuleId,
      resource_id: excResourceId,
      justification: excJustification,
      expires_at: excExpiresAt,
    }, {
      onSuccess: () => {
        setExcRuleId('');
        setExcResourceId('');
        setExcJustification('');
        setExcExpiresAt('');
      },
    });
  };

  return (
    <div className="space-y-6">
      {rulesError && <ErrorBanner message="Failed to load policy engine data" />}

      {/* Section Navigation */}
      <div className="flex gap-1 flex-wrap" style={{ borderBottom: '1px solid var(--border-default)' }}>
        {(['editor', 'test', 'versions', 'hierarchy', 'exceptions', 'audit'] as const).map(section => (
          <button key={section} style={sectionBtnStyle(activeSection === section)} onClick={() => setActiveSection(section)}>
            {section === 'editor' ? 'Rego Editor' : section === 'test' ? 'Test' : section === 'versions' ? 'Versions' : section === 'hierarchy' ? 'Hierarchy' : section === 'exceptions' ? 'Exceptions' : 'Audit Log'}
          </button>
        ))}
      </div>

      {/* Rego Editor Section */}
      {activeSection === 'editor' && (
        <div className="space-y-4">
          {/* Rule selector */}
          <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <div className="flex items-center gap-3 mb-4">
              <select
                value={selectedRuleId ?? ''}
                onChange={e => setSelectedRuleId(e.target.value || null)}
                className="rounded border px-2 py-1 text-xs flex-1"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
              >
                <option value="">New Rule</option>
                {rules.map((r: any) => (
                  <option key={r.id} value={r.id}>{r.name} (v{r.version})</option>
                ))}
              </select>
              <input
                value={ruleName}
                onChange={e => setRuleName(e.target.value)}
                placeholder="Rule name"
                className="rounded border px-2 py-1 text-xs"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)', width: '200px' }}
              />
            </div>
            <RegoEditor value={regoContent} onChange={setRegoContent} height="300px" />
            <div className="mt-3 flex items-center gap-3">
              <Button onClick={handleSaveRule} disabled={saveRule.isPending || !ruleName.trim() || !regoContent.trim()} className="gap-2">
                {saveRule.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Code className="h-4 w-4" />}
                Save Rule
              </Button>
              {saveRule.error && (
                <span className="text-xs" style={{ color: 'var(--critical)' }}>Save failed</span>
              )}
              {saveRule.isSuccess && (
                <span className="text-xs" style={{ color: 'var(--success)' }}>✓ Saved</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Rule Testing Section */}
      {activeSection === 'test' && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Rule Testing</h3>
          <div className="space-y-4">
            <div>
              <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Input JSON</label>
              <textarea
                value={testInput}
                onChange={e => { setTestInput(e.target.value); setTestError(null); }}
                className="w-full rounded border p-3 font-mono text-xs"
                style={{ borderColor: testError ? 'var(--critical)' : 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)', minHeight: '120px', resize: 'vertical' }}
              />
              {testError && (
                <div className="mt-1 text-xs" style={{ color: 'var(--critical)' }}>{testError}</div>
              )}
            </div>
            <Button onClick={handleRunTest} disabled={dryRun.isPending} className="gap-2">
              {dryRun.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Settings className="h-4 w-4" />}
              Run Test
            </Button>
            {testResults !== null && (
              <div className="mt-4">
                <h4 className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
                  Violations ({testResults.length})
                </h4>
                {testResults.length === 0 ? (
                  <div className="text-xs" style={{ color: 'var(--success)' }}>✓ No violations — policy passes</div>
                ) : (
                  <div className="space-y-1">
                    {testResults.map((v: any, i: number) => (
                      <div key={i} className="rounded border p-2 text-xs" style={{ borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}>
                        {v.message || v.rule || JSON.stringify(v)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Version History Section */}
      {activeSection === 'versions' && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Version History</h3>
          {!selectedRuleId ? (
            <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              Select a rule in the Editor tab to view versions
            </div>
          ) : versionsLoading ? (
            <SkeletonLoader variant="table" rows={4} columns={4} />
          ) : versions.length === 0 ? (
            <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No version history
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={headerCellStyle}>Version</th>
                    <th style={headerCellStyle}>Created By</th>
                    <th style={headerCellStyle}>Date</th>
                    <th style={headerCellStyle}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((v: any) => (
                    <tr key={v.id}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                      <td style={cellStyle}><span className="text-xs font-mono">v{v.version}</span></td>
                      <td style={cellStyle}><span className="text-xs">{v.created_by ?? '—'}</span></td>
                      <td style={cellStyle}>
                        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                          {v.created_at ? new Date(v.created_at).toLocaleString() : '—'}
                        </span>
                      </td>
                      <td style={cellStyle}>
                        <Button variant="outline" size="sm"
                          onClick={() => handleRollback(v.version)}
                          disabled={rollbackRule.isPending}>
                          Rollback
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Policy Hierarchy Section */}
      {activeSection === 'hierarchy' && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Policy Hierarchy</h3>
          {hierarchyLoading ? (
            <SkeletonLoader variant="table" rows={5} columns={4} />
          ) : !hierarchy ? (
            <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No hierarchy data available
            </div>
          ) : (
            <div className="space-y-4">
              {/* Organization level */}
              {hierarchy.organization?.length > 0 && (
                <div>
                  <div className="text-xs font-semibold mb-2 flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
                    <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--accent)' }} />
                    Organization
                  </div>
                  <div className="pl-4 space-y-1">
                    {hierarchy.organization.map((p: any) => (
                      <div key={p.id} className="flex items-center justify-between py-1 text-xs" style={{ borderBottom: '1px solid var(--border-faint)' }}>
                        <span style={{ color: 'var(--text-primary)' }}>{p.rule_name}</span>
                        <span className="px-1.5 py-0.5 rounded text-xs" style={{
                          backgroundColor: p.enforcement_mode === 'block' ? 'var(--critical-bg, rgba(239,68,68,0.1))' : p.enforcement_mode === 'auto_remediate' ? 'rgba(34,197,94,0.1)' : 'rgba(234,179,8,0.1)',
                          color: p.enforcement_mode === 'block' ? 'var(--critical)' : p.enforcement_mode === 'auto_remediate' ? 'var(--success)' : 'var(--warning)',
                        }}>
                          {p.enforcement_mode}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {/* Team level */}
              {hierarchy.teams?.length > 0 && hierarchy.teams.map((team: any) => (
                <div key={team.team_id}>
                  <div className="text-xs font-semibold mb-2 flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
                    <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--warning)' }} />
                    Team: {team.team_name}
                  </div>
                  <div className="pl-4 space-y-1">
                    {team.policies?.map((p: any) => (
                      <div key={p.id} className="flex items-center justify-between py-1 text-xs" style={{
                        borderBottom: '1px solid var(--border-faint)',
                        opacity: p.is_override ? 1 : 0.7,
                      }}>
                        <span style={{ color: 'var(--text-primary)' }}>
                          {p.rule_name}
                          {p.is_override && <span className="ml-1 text-xs" style={{ color: 'var(--warning)' }}>(override)</span>}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-xs" style={{
                          backgroundColor: p.enforcement_mode === 'block' ? 'var(--critical-bg, rgba(239,68,68,0.1))' : 'rgba(234,179,8,0.1)',
                          color: p.enforcement_mode === 'block' ? 'var(--critical)' : 'var(--warning)',
                        }}>
                          {p.enforcement_mode}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {/* Project level */}
              {hierarchy.projects?.length > 0 && hierarchy.projects.map((proj: any) => (
                <div key={proj.project_id}>
                  <div className="text-xs font-semibold mb-2 flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
                    <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--success)' }} />
                    Project: {proj.project_name}
                  </div>
                  <div className="pl-4 space-y-1">
                    {proj.policies?.map((p: any) => (
                      <div key={p.id} className="flex items-center justify-between py-1 text-xs" style={{
                        borderBottom: '1px solid var(--border-faint)',
                        opacity: p.is_override ? 1 : 0.7,
                      }}>
                        <span style={{ color: 'var(--text-primary)' }}>
                          {p.rule_name}
                          {p.is_override && <span className="ml-1 text-xs" style={{ color: 'var(--warning)' }}>(override)</span>}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-xs" style={{
                          backgroundColor: p.enforcement_mode === 'block' ? 'var(--critical-bg, rgba(239,68,68,0.1))' : 'rgba(234,179,8,0.1)',
                          color: p.enforcement_mode === 'block' ? 'var(--critical)' : 'var(--warning)',
                        }}>
                          {p.enforcement_mode}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Exceptions Section */}
      {activeSection === 'exceptions' && (
        <div className="space-y-4">
          <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Policy Exceptions</h3>
            {exceptionsLoading ? (
              <SkeletonLoader variant="table" rows={3} columns={6} />
            ) : exceptions.length === 0 ? (
              <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
                No exceptions configured
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={headerCellStyle}>Rule ID</th>
                      <th style={headerCellStyle}>Resource</th>
                      <th style={headerCellStyle}>Justification</th>
                      <th style={headerCellStyle}>Expires</th>
                      <th style={headerCellStyle}>Status</th>
                      <th style={headerCellStyle}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exceptions.map((exc: any) => (
                      <tr key={exc.id}
                        style={{ opacity: exc.is_active ? 1 : 0.5, textDecoration: exc.is_active ? 'none' : 'line-through' }}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                        <td style={cellStyle}><span className="text-xs font-mono">{exc.rule_id}</span></td>
                        <td style={{ ...cellStyle, maxWidth: '150px' }}>
                          <div className="truncate text-xs">{exc.resource_id}</div>
                        </td>
                        <td style={{ ...cellStyle, maxWidth: '200px' }}>
                          <div className="truncate text-xs">{exc.justification}</div>
                        </td>
                        <td style={cellStyle}>
                          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                            {exc.expires_at ? new Date(exc.expires_at).toLocaleDateString() : '—'}
                          </span>
                        </td>
                        <td style={cellStyle}>
                          {exc.is_active ? (
                            <span className="text-xs" style={{ color: 'var(--success)' }}>Active</span>
                          ) : (
                            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Revoked</span>
                          )}
                        </td>
                        <td style={cellStyle}>
                          {exc.is_active && (
                            <Button variant="outline" size="sm"
                              onClick={() => revokeException.mutate(exc.id)}
                              disabled={revokeException.isPending}>
                              Revoke
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Create Exception Form */}
          <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Create Exception</h3>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Rule ID</label>
                <input value={excRuleId} onChange={e => setExcRuleId(e.target.value)}
                  placeholder="rule-id"
                  className="w-full rounded border px-2 py-1 text-xs"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
              </div>
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Resource ID</label>
                <input value={excResourceId} onChange={e => setExcResourceId(e.target.value)}
                  placeholder="arn:aws:..."
                  className="w-full rounded border px-2 py-1 text-xs"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
              </div>
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Justification</label>
                <input value={excJustification} onChange={e => setExcJustification(e.target.value)}
                  placeholder="Reason for exception"
                  className="w-full rounded border px-2 py-1 text-xs"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
              </div>
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Expires At</label>
                <input value={excExpiresAt} onChange={e => setExcExpiresAt(e.target.value)} type="date"
                  className="w-full rounded border px-2 py-1 text-xs"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
              </div>
            </div>
            <div className="mt-3">
              <Button onClick={handleCreateException} disabled={createException.isPending || !excRuleId.trim() || !excResourceId.trim()} size="sm" className="gap-2">
                {createException.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                Create Exception
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Audit Log Section */}
      {activeSection === 'audit' && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Audit Log</h3>
            <select
              value={auditActionFilter ?? ''}
              onChange={e => { setAuditActionFilter(e.target.value || null); setAuditPage(1); }}
              className="rounded border px-2 py-1 text-xs"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            >
              <option value="">All Actions</option>
              <option value="created">Created</option>
              <option value="updated">Updated</option>
              <option value="deleted">Deleted</option>
              <option value="rollback">Rollback</option>
            </select>
          </div>
          {auditLoading ? (
            <SkeletonLoader variant="table" rows={5} columns={5} />
          ) : auditItems.length === 0 ? (
            <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No audit log entries
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={headerCellStyle}>Action</th>
                      <th style={headerCellStyle}>Actor</th>
                      <th style={headerCellStyle}>Rule ID</th>
                      <th style={headerCellStyle}>Details</th>
                      <th style={headerCellStyle}>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditItems.map((entry: any) => (
                      <tr key={entry.id}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                        <td style={cellStyle}>
                          <span className="text-xs px-1.5 py-0.5 rounded" style={{
                            backgroundColor: entry.action === 'deleted' ? 'var(--critical-bg, rgba(239,68,68,0.1))' : entry.action === 'rollback' ? 'rgba(234,179,8,0.1)' : 'rgba(34,197,94,0.1)',
                            color: entry.action === 'deleted' ? 'var(--critical)' : entry.action === 'rollback' ? 'var(--warning)' : 'var(--success)',
                          }}>
                            {entry.action}
                          </span>
                        </td>
                        <td style={cellStyle}><span className="text-xs">{entry.actor}</span></td>
                        <td style={cellStyle}><span className="text-xs font-mono">{entry.rule_id}</span></td>
                        <td style={{ ...cellStyle, maxWidth: '200px' }}>
                          <div className="truncate text-xs" style={{ color: 'var(--text-secondary)' }}>{entry.details ?? '—'}</div>
                        </td>
                        <td style={cellStyle}>
                          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                            {entry.created_at ? new Date(entry.created_at).toLocaleString() : '—'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {auditTotalPages > 1 && (
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Page {auditPage} of {auditTotalPages}</span>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setAuditPage(p => Math.max(1, p - 1))} disabled={auditPage <= 1}>Previous</Button>
                    <Button variant="outline" size="sm" onClick={() => setAuditPage(p => Math.min(auditTotalPages, p + 1))} disabled={auditPage >= auditTotalPages}>Next</Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
