'use client';

import * as React from 'react';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  Shield, ToggleLeft, ToggleRight, X, Loader2, Play, AlertTriangle,
} from 'lucide-react';
import {
  useCSPMRules, useToggleRule,
} from '@/hooks/use-cspm';
import { cspmAPI } from '@/lib/api/cspm';
import type { CSPMRule } from '@/lib/api/cspm';

function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded', className)} style={{ backgroundColor: 'var(--bg-elevated)' }} />;
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-4 flex items-center gap-2 rounded border p-3 text-sm"
      style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-bg)', color: 'var(--critical)' }}>
      <AlertTriangle className="h-4 w-4 flex-shrink-0" />
      {message}
    </div>
  );
}

// AWS Console table cell style
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

export function PoliciesTab() {
  const { data, isLoading, error } = useCSPMRules();
  const toggleRule = useToggleRule();
  const [toggleError, setToggleError] = React.useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = React.useState('');
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const REGO_TEMPLATE = `# METADATA
# title: "Your rule title here"
# description: "What this rule checks"
# severity: HIGH
# category: cspm
# provider: aws
# resource_type: aws::s3::bucket
# compliance:
#   - framework: SOC2
#     control: "CC6.1"
# remediation: "Step 1: ... Step 2: ..."

package custom.acme_corp.s3_tagging

import future.keywords

deny[finding] {
    input.resource_type == "aws::s3::bucket"
    not input.tags["CostCenter"]
    finding := {
        "rule_id": "s3-missing-costcenter-tag",
        "title": "S3 bucket is missing required CostCenter tag",
        "severity": "MEDIUM",
    }
}`;
  const [regoCode, setRegoCode] = React.useState(REGO_TEMPLATE);
  const [dryRunResult, setDryRunResult] = React.useState<unknown>(null);
  const [dryRunLoading, setDryRunLoading] = React.useState(false);
  const [dryRunError, setDryRunError] = React.useState<string | null>(null);

  const rules = data?.rules ?? [];
  const filtered = rules.filter(r =>
    (!severityFilter || r.severity === severityFilter)
  );

  const severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

  async function handleToggle(rule: CSPMRule) {
    setToggleError(null);
    try {
      await toggleRule.mutateAsync({ ruleId: rule.rule_id, enable: !rule.is_enabled });
    } catch (e: unknown) {
      setToggleError(e instanceof Error ? e.message : 'Failed to update rule');
    }
  }

  async function handleTestRule() {
    setDryRunLoading(true);
    setDryRunError(null);
    setDryRunResult(null);
    try {
      const result = await cspmAPI.dryRunRule(regoCode, []);
      setDryRunResult(result);
    } catch (e: unknown) {
      setDryRunError(e instanceof Error ? e.message : 'Dry run failed');
    } finally {
      setDryRunLoading(false);
    }
  }

  return (
    <div>
      {error && <ErrorBanner message="Failed to load policy rules" />}

      {/* Toolbar */}
      <div className="mb-4 flex items-center gap-3">
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}
          className="rounded border px-2 py-1.5 text-sm"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All Severities</option>
          {severities.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <div className="ml-auto">
          <Button onClick={() => setShowCreateModal(true)} className="gap-2 h-8 px-3 text-sm">
            <Shield className="h-3.5 w-3.5" />
            Create Custom Policy
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[1,2,3,4,5].map(i => <Skeleton key={i} className="h-10" />)}</div>
      ) : filtered.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
          No rules found
        </div>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              {['Rule ID', 'Title', 'Severity', 'Category', 'Provider', 'Enabled'].map(h => (
                <th key={h} style={headerCellStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(rule => (
              <tr key={rule.id}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                <td style={cellStyle}><span className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>{rule.rule_id}</span></td>
                <td style={{ ...cellStyle, maxWidth: '300px' }}>
                  <div className="truncate text-sm" style={{ color: 'var(--text-primary)' }}>{rule.title}</div>
                  {rule.is_custom && (
                    <span className="text-xs" style={{ color: 'var(--accent)' }}>Custom</span>
                  )}
                </td>
                <td style={cellStyle}><SeverityBadge severity={rule.severity} size="sm" /></td>
                <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{rule.category}</span></td>
                <td style={cellStyle}><span className="text-xs uppercase" style={{ color: 'var(--text-secondary)' }}>{rule.provider}</span></td>
                <td style={cellStyle}>
                  <button onClick={() => handleToggle(rule)} disabled={toggleRule.isPending}
                    className="flex items-center gap-1.5 text-sm transition-colors"
                    style={{ color: rule.is_enabled ? 'var(--success)' : 'var(--text-tertiary)' }}>
                    {rule.is_enabled
                      ? <ToggleRight className="h-5 w-5" />
                      : <ToggleLeft className="h-5 w-5" />}
                    {rule.is_enabled ? 'Enabled' : 'Disabled'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Create custom policy modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="w-full max-w-3xl rounded-lg" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
            <div className="flex items-center justify-between border-b px-6 py-4" style={{ borderColor: 'var(--border-default)' }}>
              <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Create Custom Policy</h2>
              <button onClick={() => { setShowCreateModal(false); setDryRunResult(null); setDryRunError(null); }} style={{ color: 'var(--text-tertiary)' }}><X className="h-4 w-4" /></button>
            </div>
            <div className="flex-1 overflow-auto p-6">
              <div className="mb-2 text-sm" style={{ color: 'var(--text-secondary)' }}>Write your policy in Rego:</div>
              <div className="relative rounded overflow-hidden" style={{ border: '1px solid #3c3c3c' }}>
                <div className="flex items-center gap-2 px-3 py-1.5" style={{ backgroundColor: '#2d2d2d', borderBottom: '1px solid #3c3c3c' }}>
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#ff5f57' }} />
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#febc2e' }} />
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#28c840' }} />
                  <span className="ml-2 text-xs" style={{ color: '#858585', fontFamily: 'monospace' }}>policy.rego</span>
                </div>
                <div className="flex" style={{ backgroundColor: '#1e1e1e' }}>
                  <div className="select-none py-3 pr-3 pl-3 text-right" style={{ backgroundColor: '#1e1e1e', borderRight: '1px solid #3c3c3c', minWidth: '40px', color: '#858585', fontFamily: 'monospace', fontSize: '13px', lineHeight: '1.5', userSelect: 'none' }}>
                    {regoCode.split('\n').map((_, i) => (
                      <div key={i}>{i + 1}</div>
                    ))}
                  </div>
                  <textarea
                    value={regoCode}
                    onChange={e => setRegoCode(e.target.value)}
                    spellCheck={false}
                    className="flex-1 resize-none outline-none p-3"
                    style={{
                      backgroundColor: '#1e1e1e',
                      color: '#d4d4d4',
                      fontFamily: '"Cascadia Code", "Fira Code", "Consolas", "Courier New", monospace',
                      fontSize: '13px',
                      lineHeight: '1.5',
                      border: 'none',
                      minHeight: '320px',
                      tabSize: 4,
                    }}
                  />
                </div>
              </div>

              <div className="mt-3 flex items-center gap-3">
                <Button onClick={handleTestRule} disabled={dryRunLoading} className="h-8 px-3 text-sm gap-2">
                  {dryRunLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                  Test rule
                </Button>
                {dryRunError && <span className="text-xs" style={{ color: 'var(--critical)' }}>{dryRunError}</span>}
              </div>

              {dryRunResult !== null && (
                <div className="mt-3 rounded p-3 text-xs font-mono overflow-auto" style={{ backgroundColor: '#1e1e1e', border: '1px solid #3c3c3c', color: '#d4d4d4', maxHeight: '160px' }}>
                  <div className="mb-1 text-xs font-semibold" style={{ color: '#858585', fontFamily: 'sans-serif' }}>Dry run result:</div>
                  {JSON.stringify(dryRunResult, null, 2)}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 border-t px-6 py-4" style={{ borderColor: 'var(--border-default)' }}>
              <Button onClick={() => { setShowCreateModal(false); setDryRunResult(null); setDryRunError(null); }} className="h-8 px-3 text-sm">Cancel</Button>
              <Button onClick={() => { setShowCreateModal(false); setDryRunResult(null); setDryRunError(null); }} className="h-8 px-3 text-sm">Save Policy</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
