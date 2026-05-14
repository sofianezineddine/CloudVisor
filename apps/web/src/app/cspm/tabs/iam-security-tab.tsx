'use client';

import * as React from 'react';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { Play, Loader2, Shield, Key, AlertTriangle } from 'lucide-react';
import { GraphView } from '@/components/cspm/graph-view';
import { SkeletonLoader } from '@/components/cspm/skeleton-loader';
import { ErrorBanner } from '@/components/cspm/error-banner';
import {
  useIAMAnalysis,
  useIAMEscalationPaths,
  useIAMCrossAccountTrusts,
  useIAMServiceAccounts,
  useTriggerIAMAnalysis,
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

// ─── Component ────────────────────────────────────────────────────────────────

export function IAMSecurityTab() {
  const [identityTypeFilter, setIdentityTypeFilter] = React.useState<string | null>(null);
  const [sortField, setSortField] = React.useState<'risk_score' | 'excess_ratio'>('risk_score');
  const [sortDirection, setSortDirection] = React.useState<'desc' | 'asc'>('desc');
  const [selectedEscalationPath, setSelectedEscalationPath] = React.useState<string | null>(null);

  const triggerAnalysis = useTriggerIAMAnalysis();
  const [runSuccess, setRunSuccess] = React.useState(false);
  const [runError, setRunError] = React.useState<string | null>(null);

  const { data: iamData, isLoading: iamLoading, error: iamError } = useIAMAnalysis({
    identity_type: identityTypeFilter ?? undefined,
  });
  const { data: escalationData, isLoading: escalationLoading } = useIAMEscalationPaths({});
  const { data: trustsData, isLoading: trustsLoading } = useIAMCrossAccountTrusts({});
  const { data: serviceAccountsData, isLoading: saLoading } = useIAMServiceAccounts({});

  const identities = React.useMemo(() => {
    const items = iamData?.items ?? [];
    return [...items].sort((a, b) => {
      const aVal = a[sortField] ?? 0;
      const bVal = b[sortField] ?? 0;
      return sortDirection === 'desc' ? bVal - aVal : aVal - bVal;
    });
  }, [iamData, sortField, sortDirection]);

  const escalationPaths = escalationData ?? [];
  const trusts = trustsData ?? [];
  const serviceAccounts = serviceAccountsData?.items ?? [];

  // Dashboard metrics
  const totalIdentities = iamData?.total ?? identities.length;
  const excessPrivileges = identities.filter(i => i.excess_ratio > 0.5).length;
  const dormantAccounts = identities.filter(i => i.is_dormant).length;
  const missingMFA = identities.filter(i => !i.has_mfa).length;

  // Build graph for selected escalation path
  const selectedPath = escalationPaths.find(p => p.id === selectedEscalationPath);
  const graphNodes = React.useMemo(() => {
    if (!selectedPath) return [];
    const details = selectedPath.path_details ?? [];
    return details.map((d: any, i: number) => ({
      id: d.identity ?? `node-${i}`,
      label: d.identity ?? `Step ${i + 1}`,
      type: i === 0 ? 'entry' as const : i === details.length - 1 ? 'target' as const : 'intermediate' as const,
    }));
  }, [selectedPath]);

  const graphEdges = React.useMemo(() => {
    if (!selectedPath) return [];
    const details = selectedPath.path_details ?? [];
    return details.slice(1).map((d: any, i: number) => ({
      id: `edge-${i}`,
      source: details[i].identity ?? `node-${i}`,
      target: d.identity ?? `node-${i + 1}`,
      label: d.permission ?? d.action ?? '',
    }));
  }, [selectedPath]);

  const handleSort = (field: 'risk_score' | 'excess_ratio') => {
    if (sortField === field) {
      setSortDirection(d => d === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  return (
    <div className="space-y-6">
      {runError && <ErrorBanner message={runError} />}
      {runSuccess && (
        <div className="flex items-center gap-2 rounded border p-3 text-sm"
          style={{ borderColor: 'var(--success)', backgroundColor: 'var(--success-bg, rgba(34,197,94,0.08))', color: 'var(--success)' }}>
          ✓ IAM analysis started — results will appear below once complete.
          <button onClick={() => setRunSuccess(false)} className="ml-auto text-xs" style={{ color: 'var(--success)' }}>✕</button>
        </div>
      )}

      {/* Run IAM Analysis button */}
      <div className="flex justify-end">
        <Button
          onClick={() => {
            setRunSuccess(false);
            setRunError(null);
            triggerAnalysis.mutate(undefined, {
              onSuccess: () => setRunSuccess(true),
              onError: (e: unknown) => setRunError(e instanceof Error ? e.message : 'IAM analysis failed to start'),
            });
          }}
          disabled={triggerAnalysis.isPending}
          className="gap-2"
        >
          {triggerAnalysis.isPending
            ? <Loader2 className="h-4 w-4 animate-spin" />
            : <Play className="h-4 w-4" />}
          {triggerAnalysis.isPending ? 'Analyzing…' : 'Run IAM Analysis'}
        </Button>
      </div>

      {/* Dashboard Cards */}
      {iamLoading ? (
        <SkeletonLoader variant="cards" columns={4} />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="p-4 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="h-4 w-4" style={{ color: 'var(--text-secondary)' }} />
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Total Identities</span>
            </div>
            <div className="font-mono text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
              {totalIdentities}
            </div>
          </div>
          <div className="p-4 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <div className="flex items-center gap-2 mb-2">
              <Key className="h-4 w-4" style={{ color: 'var(--warning)' }} />
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Excess Privileges</span>
            </div>
            <div className="font-mono text-3xl font-bold" style={{ color: 'var(--warning)' }}>
              {excessPrivileges}
            </div>
          </div>
          <div className="p-4 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4" style={{ color: 'var(--high)' }} />
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Dormant Accounts</span>
            </div>
            <div className="font-mono text-3xl font-bold" style={{ color: 'var(--high)' }}>
              {dormantAccounts}
            </div>
          </div>
          <div className="p-4 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="h-4 w-4" style={{ color: 'var(--critical)' }} />
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Missing MFA</span>
            </div>
            <div className="font-mono text-3xl font-bold" style={{ color: 'var(--critical)' }}>
              {missingMFA}
            </div>
          </div>
        </div>
      )}

      {/* Identity Risk Table */}
      <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Identity Risk Table</h3>
          <select
            value={identityTypeFilter ?? ''}
            onChange={e => setIdentityTypeFilter(e.target.value || null)}
            className="rounded border px-2 py-1 text-xs"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
          >
            <option value="">All Types</option>
            <option value="user">User</option>
            <option value="role">Role</option>
            <option value="service_account">Service Account</option>
            <option value="group">Group</option>
          </select>
        </div>
        {iamLoading ? (
          <SkeletonLoader variant="table" rows={5} columns={7} />
        ) : identities.length === 0 ? (
          <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
            No identity data available
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={headerCellStyle}>Identity ARN</th>
                  <th style={headerCellStyle}>Type</th>
                  <th style={{ ...headerCellStyle, cursor: 'pointer' }} onClick={() => handleSort('excess_ratio')}>
                    Excess Ratio {sortField === 'excess_ratio' ? (sortDirection === 'desc' ? '↓' : '↑') : ''}
                  </th>
                  <th style={headerCellStyle}>Last Activity</th>
                  <th style={headerCellStyle}>MFA Status</th>
                  <th style={{ ...headerCellStyle, cursor: 'pointer' }} onClick={() => handleSort('risk_score')}>
                    Risk Score {sortField === 'risk_score' ? (sortDirection === 'desc' ? '↓' : '↑') : ''}
                  </th>
                  <th style={headerCellStyle}>Severity</th>
                </tr>
              </thead>
              <tbody>
                {identities.slice(0, 20).map(identity => (
                  <tr key={identity.id}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                    <td style={{ ...cellStyle, maxWidth: '220px' }}>
                      <div className="truncate text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                        {identity.identity_arn}
                      </div>
                    </td>
                    <td style={cellStyle}>
                      <span className="text-xs uppercase" style={{ color: 'var(--text-secondary)' }}>
                        {identity.identity_type}
                      </span>
                    </td>
                    <td style={cellStyle}>
                      <span className="font-mono text-xs" style={{ color: identity.excess_ratio > 0.7 ? 'var(--critical)' : identity.excess_ratio > 0.4 ? 'var(--warning)' : 'var(--text-primary)' }}>
                        {(identity.excess_ratio * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td style={cellStyle}>
                      <span className="text-xs" style={{ color: identity.is_dormant ? 'var(--high)' : 'var(--text-secondary)' }}>
                        {identity.last_activity_at ? new Date(identity.last_activity_at).toLocaleDateString() : 'Never'}
                      </span>
                    </td>
                    <td style={cellStyle}>
                      {identity.has_mfa ? (
                        <span className="text-xs" style={{ color: 'var(--success)' }}>✓ Enabled</span>
                      ) : (
                        <span className="text-xs font-semibold" style={{ color: 'var(--critical)' }}>✗ Missing</span>
                      )}
                    </td>
                    <td style={cellStyle}>
                      <span className="font-mono text-xs font-semibold" style={{ color: identity.risk_score >= 80 ? 'var(--critical)' : identity.risk_score >= 60 ? 'var(--high)' : 'var(--text-primary)' }}>
                        {identity.risk_score}
                      </span>
                    </td>
                    <td style={cellStyle}>
                      <SeverityBadge severity={identity.severity} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Privilege Escalation Paths */}
      <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Privilege Escalation Paths</h3>
        {escalationLoading ? (
          <SkeletonLoader variant="table" rows={3} columns={4} />
        ) : escalationPaths.length === 0 ? (
          <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
            No escalation paths detected
          </div>
        ) : (
          <>
            <div className="overflow-x-auto mb-4">
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={headerCellStyle}>Source</th>
                    <th style={headerCellStyle}>Target</th>
                    <th style={headerCellStyle}>Hops</th>
                    <th style={headerCellStyle}>Severity</th>
                    <th style={headerCellStyle}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {escalationPaths.map(path => (
                    <tr key={path.id}
                      style={{ backgroundColor: selectedEscalationPath === path.id ? 'var(--bg-elevated)' : 'transparent' }}
                      onMouseEnter={e => { if (selectedEscalationPath !== path.id) e.currentTarget.style.backgroundColor = 'var(--bg-elevated)'; }}
                      onMouseLeave={e => { if (selectedEscalationPath !== path.id) e.currentTarget.style.backgroundColor = 'transparent'; }}>
                      <td style={{ ...cellStyle, maxWidth: '180px' }}>
                        <div className="truncate text-xs">{path.source_identity}</div>
                      </td>
                      <td style={{ ...cellStyle, maxWidth: '180px' }}>
                        <div className="truncate text-xs">{path.target_identity}</div>
                      </td>
                      <td style={cellStyle}><span className="text-xs">{path.path_hops}</span></td>
                      <td style={cellStyle}><SeverityBadge severity={path.severity} size="sm" /></td>
                      <td style={cellStyle}>
                        <button
                          onClick={() => setSelectedEscalationPath(selectedEscalationPath === path.id ? null : path.id)}
                          className="text-xs underline"
                          style={{ color: 'var(--accent)' }}
                        >
                          {selectedEscalationPath === path.id ? 'Hide' : 'View'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {selectedPath && graphNodes.length > 0 && (
              <GraphView nodes={graphNodes} edges={graphEdges} direction="LR" height="300px" />
            )}
          </>
        )}
      </div>

      {/* Cross-Account Trusts */}
      <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Cross-Account Trusts</h3>
        {trustsLoading ? (
          <SkeletonLoader variant="table" rows={3} columns={5} />
        ) : trusts.length === 0 ? (
          <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
            No cross-account trusts found
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={headerCellStyle}>Source Account</th>
                  <th style={headerCellStyle}>Target Account</th>
                  <th style={headerCellStyle}>Trusted Principal</th>
                  <th style={headerCellStyle}>External ID</th>
                  <th style={headerCellStyle}>Risk Score</th>
                </tr>
              </thead>
              <tbody>
                {trusts.map(trust => {
                  const isWarning = trust.has_wildcard_principal || trust.is_overly_permissive;
                  return (
                    <tr key={trust.id}
                      style={{ backgroundColor: isWarning ? 'var(--critical-bg, rgba(239,68,68,0.05))' : 'transparent' }}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = isWarning ? 'var(--critical-bg, rgba(239,68,68,0.1))' : 'var(--bg-elevated)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = isWarning ? 'var(--critical-bg, rgba(239,68,68,0.05))' : 'transparent')}>
                      <td style={cellStyle}><span className="text-xs">{trust.source_account_id}</span></td>
                      <td style={cellStyle}><span className="text-xs">{trust.target_account_id}</span></td>
                      <td style={{ ...cellStyle, maxWidth: '200px' }}>
                        <div className="truncate text-xs" style={{ color: trust.has_wildcard_principal ? 'var(--critical)' : 'var(--text-primary)' }}>
                          {trust.trusted_principal}
                          {trust.has_wildcard_principal && ' ⚠️'}
                        </div>
                      </td>
                      <td style={cellStyle}>
                        {trust.has_external_id ? (
                          <span className="text-xs" style={{ color: 'var(--success)' }}>✓ Yes</span>
                        ) : (
                          <span className="text-xs" style={{ color: 'var(--warning)' }}>✗ No</span>
                        )}
                      </td>
                      <td style={cellStyle}>
                        <span className="font-mono text-xs font-semibold" style={{ color: trust.risk_score >= 80 ? 'var(--critical)' : trust.risk_score >= 60 ? 'var(--high)' : 'var(--text-primary)' }}>
                          {trust.risk_score}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Service Accounts */}
      <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Service Accounts</h3>
        {saLoading ? (
          <SkeletonLoader variant="table" rows={3} columns={5} />
        ) : serviceAccounts.length === 0 ? (
          <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
            No service accounts found
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={headerCellStyle}>Service Account ID</th>
                  <th style={headerCellStyle}>Permission Breadth</th>
                  <th style={headerCellStyle}>Scope Violation</th>
                  <th style={headerCellStyle}>Key Age (days)</th>
                  <th style={headerCellStyle}>Risk Score</th>
                </tr>
              </thead>
              <tbody>
                {serviceAccounts.map(sa => {
                  const isHighlight = sa.has_scope_violation || sa.key_age_days > 90;
                  return (
                    <tr key={sa.id}
                      style={{ backgroundColor: isHighlight ? 'var(--critical-bg, rgba(239,68,68,0.05))' : 'transparent' }}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = isHighlight ? 'var(--critical-bg, rgba(239,68,68,0.1))' : 'var(--bg-elevated)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = isHighlight ? 'var(--critical-bg, rgba(239,68,68,0.05))' : 'transparent')}>
                      <td style={{ ...cellStyle, maxWidth: '200px' }}>
                        <div className="truncate text-xs">{sa.service_account_id}</div>
                      </td>
                      <td style={cellStyle}><span className="text-xs">{sa.permission_breadth}</span></td>
                      <td style={cellStyle}>
                        {sa.has_scope_violation ? (
                          <span className="text-xs font-semibold" style={{ color: 'var(--critical)' }}>⚠ Violation</span>
                        ) : (
                          <span className="text-xs" style={{ color: 'var(--success)' }}>✓ OK</span>
                        )}
                      </td>
                      <td style={cellStyle}>
                        <span className="text-xs" style={{ color: sa.key_age_days > 90 ? 'var(--critical)' : sa.key_age_days > 60 ? 'var(--warning)' : 'var(--text-primary)' }}>
                          {sa.key_age_days}
                        </span>
                      </td>
                      <td style={cellStyle}>
                        <span className="font-mono text-xs font-semibold" style={{ color: sa.risk_score >= 80 ? 'var(--critical)' : sa.risk_score >= 60 ? 'var(--high)' : 'var(--text-primary)' }}>
                          {sa.risk_score}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
