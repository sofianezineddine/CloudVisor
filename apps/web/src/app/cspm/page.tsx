'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { StatusBadge } from '@/components/ui/status-badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  Play, RefreshCw, Loader2, AlertTriangle, CheckCircle2,
  ChevronDown, ChevronUp, X, Shield, ToggleLeft, ToggleRight,
} from 'lucide-react';
import {
  useCSPMStats, useCSPMPosture, useCSPMAccountPosture,
  useCSPMFindings, useCSPMFinding, useCSPMResources,
  useCSPMCompliance, useCSPMFramework, useCSPMScans, useCSPMRules,
  useUpdateFindingStatus, useTriggerScan, useToggleRule,
  useCSPMReports, useCSPMReport, useCreateReport, useCSPMRemediation,
} from '@/hooks/use-cspm';
import { cspmAPI } from '@/lib/api/cspm';
import type { CSPMFinding, CSPMRule, CSPMReport } from '@/lib/api/cspm';
import { useScopeStore } from '@/stores/scope';
import { useShallow } from 'zustand/react/shallow';
import { NoAccountsConnectedEmptyState } from '@/components/ui/no-accounts-empty-state';
import { NoScanDataEmptyState } from '@/components/ui/no-scan-empty-state';

// ─── Constants ────────────────────────────────────────────────────────────────

const CSPM_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'misconfigurations', label: 'Misconfigurations' },
  { id: 'compliance', label: 'Compliance' },
  { id: 'policies', label: 'Policies' },
  { id: 'inventory', label: 'Inventory' },
  { id: 'reports', label: 'Reports' },
  { id: 'scan-history', label: 'Scan History' },
];

const COMPLIANCE_FRAMEWORKS = ['CIS-AWS', 'SOC2', 'PCI-DSS', 'HIPAA', 'NIST-800-53', 'ISO27001', 'GDPR'];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(isoDate: string | null | undefined): string {
  if (!isoDate) return '—';
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function formatDuration(start: string | null, end: string | null): string {
  if (!start || !end) return '—';
  const ms = new Date(end).getTime() - new Date(start).getTime();
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

function riskColor(score: number): string {
  if (score >= 80) return 'var(--critical)';
  if (score >= 60) return 'var(--high)';
  if (score >= 40) return 'var(--warning)';
  if (score >= 20) return 'var(--accent)';
  return 'var(--success)';
}

function postureColor(score: number): string {
  if (score >= 80) return 'var(--success)';
  if (score >= 60) return 'var(--warning)';
  return 'var(--critical)';
}

// ─── Shared UI ────────────────────────────────────────────────────────────────

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

// ─── Overview Tab ─────────────────────────────────────────────────────────────

function OverviewTab({
  triggerScan,
  scanRunning,
}: {
  triggerScan: ReturnType<typeof useTriggerScan>;
  scanRunning: boolean;
}) {
  const { data: posture, isLoading: postureLoading, error: postureError } = useCSPMPosture();
  const { data: findingsData, isLoading: findingsLoading } = useCSPMFindings({
    status: 'open', page_size: 50,
  });
  const { data: scansData, isLoading: scansLoading } = useCSPMScans();
  const scans = Array.isArray(scansData) ? scansData : [];
  const hasScans = scans.length > 0;
  const { data: resourcesData } = useCSPMResources({ page_size: 200 });

  const findings = findingsData?.items ?? [];
  const allResources = Array.isArray(resourcesData) ? resourcesData : [];

  // Category breakdown
  const CATEGORY_RULES = [
    { name: 'IAM & Identity', patterns: ['iam', 'identity', 'user', 'role', 'mfa', 'access'] },
    { name: 'Data Protection', patterns: ['s3', 'bucket', 'storage', 'encryption', 'kms', 'secret'] },
    { name: 'Network Security', patterns: ['security_group', 'sg', 'vpc', 'ssh', 'rdp', 'port', 'network'] },
    { name: 'Logging & Audit', patterns: ['cloudtrail', 'logging', 'audit', 'flow_log', 'config'] },
    { name: 'Encryption', patterns: ['kms', 'encrypt', 'tls', 'ssl', 'certificate'] },
    { name: 'Compute', patterns: ['ec2', 'instance', 'imds', 'metadata', 'lambda', 'container'] },
  ];

  const categoryBreakdown = React.useMemo(() => {
    const map = new Map<string, { total: number; critical: number; high: number }>();
    for (const f of findings) {
      const text = `${f.title} ${f.rule_id} ${f.resource_type ?? ''}`.toLowerCase();
      let cat = 'Other';
      for (const c of CATEGORY_RULES) {
        if (c.patterns.some(p => text.includes(p))) { cat = c.name; break; }
      }
      const e = map.get(cat) ?? { total: 0, critical: 0, high: 0 };
      e.total++;
      if (f.severity === 'CRITICAL') e.critical++;
      if (f.severity === 'HIGH') e.high++;
      map.set(cat, e);
    }
    return Array.from(map.entries())
      .map(([name, c]) => ({ name, score: Math.max(0, 100 - c.critical * 15 - c.high * 5), failing: c.total, critical: c.critical }))
      .sort((a, b) => a.score - b.score);
  }, [findings]);

  const recentFindings = findings.filter(f => f.severity === 'CRITICAL' || f.severity === 'HIGH').slice(0, 8);

  const score = posture?.posture_score ?? 0;

  // Finding trend — last 14 days from real data only (no fake seeded data)
  const trendData = React.useMemo(() => {
    const days: { label: string; count: number }[] = [];
    const now = new Date();
    for (let i = 13; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().slice(0, 10);
      const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const count = findings.filter(f => f.created_at && f.created_at.slice(0, 10) === dateStr).length;
      days.push({ label, count });
    }
    return days;
  }, [findings]);

  const maxTrend = Math.max(...trendData.map(d => d.count), 1);

  // Fix 2: Top 10 riskiest resources
  const top10Resources = React.useMemo(() => {
    return [...allResources].sort((a, b) => b.risk_score - a.risk_score).slice(0, 10);
  }, [allResources]);

  return (
    <div className="space-y-6">
      {postureError && <ErrorBanner message="Failed to load posture data" />}

      {/* Run Scan button — only in Overview tab */}
      <div className="flex justify-end">
        <Button
          onClick={() => triggerScan.mutate({ accountId: undefined })}
          disabled={triggerScan.isPending || scanRunning}
          className="gap-2"
        >
          {triggerScan.isPending || scanRunning
            ? <Loader2 className="h-4 w-4 animate-spin" />
            : <Play className="h-4 w-4" />}
          {triggerScan.isPending || scanRunning ? 'Scanning…' : 'Run Scan'}
        </Button>
      </div>

      {/* No scan guard — show empty state if no scans have run for this scope */}
      {!scansLoading && !hasScans ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full"
            style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
            <Play className="h-7 w-7" style={{ color: 'var(--text-tertiary)' }} />
          </div>
          <div>
            <div className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
              No scan data for this account
            </div>
            <div className="text-xs max-w-xs" style={{ color: 'var(--text-secondary)' }}>
              Click &quot;Run Scan&quot; above to discover resources and generate security findings for this account.
            </div>
          </div>
        </div>
      ) : (
      <>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {/* Posture Score */}
        <div className="p-4" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid #d5dbdb' }}>
          {postureLoading ? <Skeleton className="h-10 w-20 mb-2" /> : (
            <div className="font-mono text-3xl font-bold" style={{ color: postureColor(score) }}>{score}%</div>
          )}
          <div className="mt-1 text-xs mb-2" style={{ color: 'var(--text-secondary)' }}>Posture Score</div>
          <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ backgroundColor: 'var(--border-default)' }}>
            <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, backgroundColor: postureColor(score) }} />
          </div>
        </div>

        {/* Total Findings */}
        <div className="p-4" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid #d5dbdb' }}>
          {postureLoading ? <Skeleton className="h-10 w-16 mb-2" /> : (
            <div className="font-mono text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
              {posture?.total_open_findings?.toLocaleString() ?? '—'}
            </div>
          )}
          <div className="mt-1 text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>Total Findings</div>
          {!postureLoading && posture && (
            <div className="text-xs font-semibold" style={{ color: 'var(--critical)' }}>
              {posture.critical} CRITICAL
            </div>
          )}
        </div>

        {/* Resources Evaluated */}
        <div className="p-4" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid #d5dbdb' }}>
          {postureLoading ? <Skeleton className="h-10 w-16 mb-2" /> : (
            <div className="font-mono text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
              {posture?.resources_evaluated?.toLocaleString() ?? '—'}
            </div>
          )}
          <div className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>Resources Evaluated</div>
        </div>

        {/* Compliance % */}
        <div className="p-4" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid #d5dbdb' }}>
          {postureLoading ? <Skeleton className="h-10 w-16 mb-2" /> : (
            <div className="font-mono text-3xl font-bold" style={{ color: postureColor(posture?.compliance_percentage ?? 0) }}>
              {posture?.compliance_percentage ?? '—'}{posture ? '%' : ''}
            </div>
          )}
          <div className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>Compliance</div>
        </div>
      </div>

      {/* Finding trend chart */}
      <div className="p-5" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid #d5dbdb' }}>
        <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Finding Trend — Last 14 Days</h3>
        {findingsLoading ? (
          <Skeleton className="h-24" />
        ) : trendData.every(d => d.count === 0) ? (
          <div className="flex h-24 items-center justify-center text-sm gap-2" style={{ color: 'var(--text-tertiary)' }}>
            <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
            No findings in the last 14 days
          </div>
        ) : (
          <div>
            <div className="flex items-end gap-1" style={{ height: '80px' }}>
              {trendData.map((d, i) => (
                <div key={i} className="flex flex-col items-center flex-1 min-w-0" style={{ height: '100%' }}>
                  <div className="w-full flex items-end" style={{ height: '64px' }}>
                    <div
                      className="w-full rounded-t"
                      title={`${d.label}: ${d.count} findings`}
                      style={{
                        height: `${Math.max(2, (d.count / maxTrend) * 64)}px`,
                        backgroundColor: d.count > 0 ? 'var(--aws-orange)' : 'var(--border-default)',
                        opacity: 0.85,
                      }}
                    />
                  </div>
                  <div className="mt-1 text-center overflow-hidden" style={{ fontSize: '9px', color: 'var(--text-tertiary)', whiteSpace: 'nowrap', maxWidth: '100%' }}>
                    {i % 2 === 0 ? d.label : ''}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Fix 2: Top 10 riskiest resources */}
      <div className="p-5" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid #d5dbdb' }}>
        <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Top 10 Riskiest Resources</h3>
        {top10Resources.length === 0 ? (
          <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>No resource data available</div>
        ) : (
          <table style={{ ...tableStyle, fontSize: '12px' }}>
            <thead>
              <tr>
                {['Resource Name', 'Type', 'Provider', 'Risk Score', 'Open Findings'].map(h => (
                  <th key={h} style={headerCellStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {top10Resources.map(r => {
                const totalFindings = r.critical_count + r.high_count + r.medium_count + r.low_count;
                return (
                  <tr key={r.id}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                    <td style={{ ...cellStyle, maxWidth: '180px' }}>
                      <div className="truncate text-xs font-medium" style={{ color: 'var(--text-primary)' }}>{r.resource_name || r.resource_id}</div>
                    </td>
                    <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.resource_type}</span></td>
                    <td style={cellStyle}><span className="text-xs uppercase" style={{ color: 'var(--text-secondary)' }}>{r.provider}</span></td>
                    <td style={cellStyle}>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold" style={{ color: riskColor(r.risk_score) }}>{r.risk_score}</span>
                        <div className="h-1.5 w-12 overflow-hidden rounded-full" style={{ backgroundColor: 'var(--border-default)' }}>
                          <div className="h-full rounded-full" style={{ width: `${r.risk_score}%`, backgroundColor: riskColor(r.risk_score) }} />
                        </div>
                      </div>
                    </td>
                    <td style={cellStyle}>
                      {totalFindings > 0 ? (
                        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                          {r.critical_count > 0 && <span>{r.critical_count} Critical</span>}
                          {r.high_count > 0 && <span>{r.high_count} High</span>}
                          {r.medium_count > 0 && <span>{r.medium_count} Medium</span>}
                        </div>
                      ) : <span className="text-xs" style={{ color: 'var(--success)' }}>Clean</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Category breakdown */}
      <div className="p-5" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid #d5dbdb' }}>
        <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Category Breakdown</h3>
        {findingsLoading ? (
          <div className="space-y-3">{[1,2,3,4].map(i => <Skeleton key={i} className="h-6" />)}</div>
        ) : categoryBreakdown.length === 0 ? (
          <div className="flex h-16 items-center justify-center text-sm gap-2" style={{ color: 'var(--text-tertiary)' }}>
            <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
            No open findings — your environment is clean!
          </div>
        ) : (
          <div className="space-y-3">
            {categoryBreakdown.map(cat => (
              <div key={cat.name}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span style={{ color: 'var(--text-primary)' }}>{cat.name}</span>
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-semibold" style={{ color: postureColor(cat.score) }}>{cat.score}%</span>
                    <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {cat.failing} failing
                      {cat.critical > 0 && <span className="ml-1" style={{ color: 'var(--critical)' }}>({cat.critical} critical)</span>}
                    </span>
                  </div>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ backgroundColor: 'var(--border-default)' }}>
                  <div className="h-full rounded-full transition-all" style={{ width: `${cat.score}%`, backgroundColor: postureColor(cat.score) }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent critical/high findings */}
      <div className="p-5" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid #d5dbdb' }}>
        <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Recent Critical & High Findings</h3>
        {findingsLoading ? (
          <div className="space-y-2">{[1,2,3,4].map(i => <Skeleton key={i} className="h-12" />)}</div>
        ) : recentFindings.length === 0 ? (
          <div className="flex h-16 items-center justify-center text-sm gap-2" style={{ color: 'var(--text-tertiary)' }}>
            <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
            No critical or high findings
          </div>
        ) : (
          <div className="space-y-1">
            {recentFindings.map(f => (
              <div key={f.id} className="flex items-center justify-between rounded p-2.5 transition-colors"
                style={{ borderBottom: '1px solid var(--border-faint)' }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                <div className="flex items-center gap-3 min-w-0">
                  <SeverityBadge severity={f.severity} size="sm" />
                  <div className="min-w-0">
                    <div className="truncate text-sm" style={{ color: 'var(--text-primary)' }}>{f.title}</div>
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {f.resource_name || f.resource_id}{f.region && ` · ${f.region}`}
                    </div>
                  </div>
                </div>
                <span className="ml-4 flex-shrink-0 text-xs" style={{ color: 'var(--text-tertiary)' }}>{timeAgo(f.first_seen_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      </>
      )}
    </div>
  );
}

// ─── Misconfigurations Tab ────────────────────────────────────────────────────

function MisconfigurationsTab() {
  const [severityFilter, setSeverityFilter] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState('');
  const [searchQuery, setSearchQuery] = React.useState('');
  const [severityTab, setSeverityTab] = React.useState('all');
  const [page, setPage] = React.useState(1);
  const [selectedFinding, setSelectedFinding] = React.useState<CSPMFinding | null>(null);

  const { data: scansData, isLoading: scansLoading } = useCSPMScans();
  const scans = Array.isArray(scansData) ? scansData : [];
  const hasScans = scans.length > 0;

  const params = {
    severity: severityTab !== 'all' ? severityTab : (severityFilter || undefined),
    status: statusFilter || undefined,
    page,
    page_size: 20,
  };

  const { data, isLoading, error } = useCSPMFindings(params);
  const updateStatus = useUpdateFindingStatus();

  const findings = (data?.items ?? []).filter(f => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return f.title?.toLowerCase().includes(q) || (f.resource_name || f.resource_id || '').toLowerCase().includes(q);
  });
  const total = data?.total ?? 0;

  const severityCounts = React.useMemo(() => {
    const c: Record<string, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    (data?.items ?? []).forEach(f => { if (c[f.severity] !== undefined) c[f.severity]++; });
    return c;
  }, [data]);

  // No scan guard
  if (!scansLoading && !hasScans) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full"
          style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <Shield className="h-7 w-7" style={{ color: 'var(--text-tertiary)' }} />
        </div>
        <div>
          <div className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
            No findings for this account
          </div>
          <div className="text-xs max-w-xs" style={{ color: 'var(--text-secondary)' }}>
            Run a scan from the Overview tab to detect misconfigurations.
          </div>
        </div>
      </div>
    );
  }

  function clearFilters() {
    setSeverityFilter('');
    setStatusFilter('');
    setSearchQuery('');
    setSeverityTab('all');
    setPage(1);
  }

  const hasFilters = severityFilter || statusFilter || searchQuery || severityTab !== 'all';

  async function handleStatusUpdate(id: string, status: string) {
    await updateStatus.mutateAsync({ id, status });
    if (selectedFinding?.id === id) setSelectedFinding(prev => prev ? { ...prev, status: status as CSPMFinding['status'] } : null);
  }

  const SEVERITY_TABS = [
    { id: 'all', label: 'All' },
    { id: 'CRITICAL', label: 'Critical' },
    { id: 'HIGH', label: 'High' },
    { id: 'MEDIUM', label: 'Medium' },
    { id: 'LOW', label: 'Low' },
  ];

  return (
    <div className="flex flex-col" style={{ minHeight: '600px', paddingBottom: selectedFinding ? '360px' : '0' }}>
      {/* Top filter bar */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input
          type="text"
          placeholder="Search by title…"
          value={searchQuery}
          onChange={e => { setSearchQuery(e.target.value); setPage(1); }}
          className="rounded border px-3 py-1.5 text-sm"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)', minWidth: '200px' }}
        />
        <select value={severityFilter} onChange={e => { setSeverityFilter(e.target.value); setSeverityTab('all'); setPage(1); }}
          className="rounded border px-2 py-1.5 text-sm"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All Severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
          className="rounded border px-2 py-1.5 text-sm"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
          <option value="suppressed">Suppressed</option>
          <option value="accepted_risk">Accepted Risk</option>
        </select>
        {hasFilters && (
          <button onClick={clearFilters} className="text-sm" style={{ color: 'var(--text-link)' }}>
            Clear filters
          </button>
        )}
        <span className="ml-auto text-xs" style={{ color: 'var(--text-tertiary)' }}>{total} findings</span>
      </div>

      {/* Severity tabs */}
      <div className="flex border-b mb-3" style={{ borderColor: 'var(--border-default)' }}>
        {SEVERITY_TABS.map(t => (
          <button key={t.id} onClick={() => { setSeverityTab(t.id); setSeverityFilter(''); setPage(1); }}
            className="px-3 py-2 text-sm transition-colors flex-shrink-0"
            style={{
              color: severityTab === t.id ? 'var(--text-primary)' : 'var(--text-link)',
              fontWeight: severityTab === t.id ? 700 : 400,
              borderBottom: severityTab === t.id ? '2px solid var(--aws-orange)' : '2px solid transparent',
              marginBottom: '-1px',
              backgroundColor: 'transparent',
            }}>
            {t.label}
            {t.id !== 'all' && <span className="ml-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>({severityCounts[t.id] ?? 0})</span>}
          </button>
        ))}
      </div>

      {error && <ErrorBanner message="Failed to load findings" />}

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="space-y-2">{[1,2,3,4,5].map(i => <Skeleton key={i} className="h-10" />)}</div>
        ) : findings.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm gap-2" style={{ color: 'var(--text-tertiary)' }}>
            <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
            No findings match the current filters
          </div>
        ) : (
          <div className="rounded-lg border overflow-hidden" style={{ borderColor: 'var(--border-default)' }}>
            <table className="w-full border-collapse">
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-elevated)', borderBottom: '1px solid var(--border-default)' }}>
                  {['Severity', 'Title', 'Resource', 'Type', 'Account', 'Region', 'Age', 'Status'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {findings.map(f => (
                  <tr key={f.id}
                    className="cursor-pointer transition-colors"
                    style={{ borderBottom: '1px solid var(--border-faint)' }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = selectedFinding?.id === f.id ? 'var(--bg-elevated)' : 'transparent')}
                    onClick={() => setSelectedFinding(selectedFinding?.id === f.id ? null : f)}>
                    <td className="px-4 py-3"><SeverityBadge severity={f.severity} size="sm" /></td>
                    <td className="px-4 py-3" style={{ maxWidth: '280px' }}>
                      <div className="truncate text-sm" style={{ color: 'var(--text-primary)' }}>{f.title}</div>
                    </td>
                    <td className="px-4 py-3" style={{ maxWidth: '160px' }}>
                      <div className="truncate text-xs" style={{ color: 'var(--text-secondary)' }}>{f.resource_name || f.resource_id}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{f.resource_type || '—'}</span>
                    </td>
                    <td className="px-4 py-3"><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{f.account_id || '—'}</span></td>
                    <td className="px-4 py-3"><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{f.region || '—'}</span></td>
                    <td className="px-4 py-3"><span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{timeAgo(f.first_seen_at)}</span></td>
                    <td className="px-4 py-3"><StatusBadge status={f.status as any} size="sm" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between border-t px-4 py-2 mt-2" style={{ borderColor: 'var(--border-default)' }}>
          <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <div className="flex gap-2">
            <Button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="h-7 px-3 text-xs">Prev</Button>
            <Button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 20)} className="h-7 px-3 text-xs">Next</Button>
          </div>
        </div>
      )}

      {/* Split panel */}
      {selectedFinding && (
        <FindingSplitPanel
          finding={selectedFinding}
          onClose={() => setSelectedFinding(null)}
          onStatusUpdate={handleStatusUpdate}
          updating={updateStatus.isPending}
        />
      )}
    </div>
  );
}

function FindingSplitPanel({ finding, onClose, onStatusUpdate, updating }: {
  finding: CSPMFinding;
  onClose: () => void;
  onStatusUpdate: (id: string, status: string) => void;
  updating: boolean;
}) {
  const { data: remediation } = useCSPMRemediation(finding.id);

  const complianceTags = Array.isArray(finding.compliance_mapping)
    ? finding.compliance_mapping.map(c => typeof c === 'string' ? c : `${c.framework}-${c.control}`)
    : [];

  // Use API remediation if available, else fall back to raw text
  const remediationSteps: string[] = React.useMemo(() => {
    if (remediation?.console_steps) {
      return [
        remediation.console_steps,
        remediation.cli_command ? `CLI: ${remediation.cli_command}` : '',
      ].filter(Boolean);
    }
    if (finding.remediation) {
      return finding.remediation.split(/\n|\.\s+/).filter(Boolean).slice(0, 5);
    }
    return ['Review the resource configuration', 'Apply the recommended security settings', 'Verify the change resolves the finding'];
  }, [remediation, finding.remediation]);

  const terraformSnippet = remediation?.terraform_snippet || null;

  const sectionLabel: React.CSSProperties = { color: 'var(--text-secondary)', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px', letterSpacing: '0.05em' };
  const divider: React.CSSProperties = { borderTop: '1px solid var(--border-faint)', margin: '12px 0' };

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-40 border-t"
      style={{
        height: '360px',
        backgroundColor: 'var(--bg-surface)',
        borderColor: 'var(--border-default)',
        boxShadow: 'var(--shadow-split)',
      }}
    >
      <div className="flex h-10 items-center justify-between border-b px-4" style={{ borderColor: 'var(--border-faint)' }}>
        <div className="flex items-center gap-2 min-w-0">
          <SeverityBadge severity={finding.severity} size="sm" />
          <span className="text-sm font-semibold truncate max-w-xs" style={{ color: 'var(--text-primary)' }}>{finding.title}</span>
          <StatusBadge status={finding.status as any} size="sm" />
          <span className="text-xs flex-shrink-0" style={{ color: 'var(--text-tertiary)' }}>{timeAgo(finding.first_seen_at)}</span>
        </div>
        <button onClick={onClose} className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded transition-colors" style={{ color: 'var(--text-tertiary)' }}
          onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
          onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="h-[calc(360px-40px)] overflow-y-auto">
        <div className="p-4 space-y-0">
          {/* 1. Impact */}
          <div>
            <div style={sectionLabel}>Impact</div>
            <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{finding.description || 'No description available.'}</p>
          </div>
          <div style={divider} />

          {/* 2. Affected Resource */}
          <div>
            <div style={sectionLabel}>Affected Resource</div>
            <div className="text-sm space-y-0.5">
              <div style={{ color: 'var(--text-primary)' }}>{finding.resource_name || finding.resource_id}</div>
              <div style={{ color: 'var(--text-tertiary)' }}>{finding.resource_type} · {finding.account_id} · {finding.region}</div>
            </div>
          </div>
          <div style={divider} />

          {/* 3. Compliance Controls */}
          {complianceTags.length > 0 && (
            <>
              <div>
                <div style={sectionLabel}>Compliance Controls</div>
                <div className="flex flex-wrap gap-1">
                  {complianceTags.map(tag => (
                    <span key={tag} className="rounded px-1.5 py-0.5 text-xs font-mono"
                      style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)', color: 'var(--text-secondary)' }}>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              <div style={divider} />
            </>
          )}

          {/* 4. Remediation Steps */}
          <div>
            <div style={sectionLabel}>Remediation Steps</div>
            <ol className="space-y-1 text-sm list-decimal list-inside" style={{ color: 'var(--text-primary)' }}>
              {remediationSteps.map((step, i) => <li key={i}>{step.trim()}</li>)}
            </ol>
            {terraformSnippet && (
              <div className="mt-3">
                <div className="mb-1 text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>Terraform fix:</div>
                <pre className="rounded p-2 text-xs overflow-auto" style={{ backgroundColor: '#1e1e1e', color: '#d4d4d4', fontFamily: 'monospace', maxHeight: '120px' }}>
                  {terraformSnippet}
                </pre>
              </div>
            )}
          </div>
          <div style={divider} />

          {/* 5. Actions */}
          <div>
            <div style={sectionLabel}>Actions</div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => onStatusUpdate(finding.id, 'resolved')} disabled={updating || finding.status === 'resolved'} className="h-7 px-3 text-xs">
                Mark Resolved
              </Button>
              <Button onClick={() => onStatusUpdate(finding.id, 'suppressed')} disabled={updating || finding.status === 'suppressed'} className="h-7 px-3 text-xs">
                Suppress
              </Button>
              <Button onClick={() => onStatusUpdate(finding.id, 'accepted_risk')} disabled={updating || finding.status === 'accepted_risk'} className="h-7 px-3 text-xs">
                Accept Risk
              </Button>
            </div>
          </div>
          <div style={divider} />

          {/* 6. Rule Detail */}
          <div>
            <div style={sectionLabel}>Rule Detail</div>
            <div className="text-sm space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)', color: 'var(--text-secondary)' }}>
                  {finding.rule_id}
                </span>
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                This rule checks for security misconfigurations that may expose your cloud resources to risk. Enabling this rule helps maintain compliance and reduces attack surface.
              </div>
            </div>
          </div>
          <div style={divider} />

          {/* 7. Timeline */}
          <div>
            <div style={sectionLabel}>Timeline</div>
            <div className="space-y-1 text-sm">
              <div className="flex items-center justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>First seen</span>
                <span style={{ color: 'var(--text-primary)' }}>{finding.first_seen_at ? new Date(finding.first_seen_at).toLocaleString() : '—'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Last seen</span>
                <span style={{ color: 'var(--text-primary)' }}>{finding.last_seen_at ? new Date(finding.last_seen_at).toLocaleString() : '—'}</span>
              </div>
              {finding.resolved_at && (
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--text-secondary)' }}>Resolved</span>
                  <span style={{ color: 'var(--success)' }}>{new Date(finding.resolved_at).toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>
          <div style={divider} />

          {/* 8. Comments */}
          <div>
            <div style={sectionLabel}>Comments</div>
            <div className="text-sm italic" style={{ color: 'var(--text-tertiary)' }}>Comments coming soon</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Compliance Tab ───────────────────────────────────────────────────────────

function downloadControlCSV(ctrl: { id?: string; control_id?: string; title: string; status: string; finding_count?: number }) {
  const ctrlId = ctrl.id ?? ctrl.control_id ?? 'unknown';
  const rows = [
    'resource_name,account,region,status,last_checked',
    `"${ctrl.title}","—","—","${ctrl.status}","${new Date().toISOString()}"`,
  ];
  const csv = rows.join('\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `${ctrlId.replace(/[^a-z0-9]/gi, '_')}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function getDomainPrefix(controlId: string | undefined): string {
  if (!controlId) return 'Other';
  // "1.1.1" → "1", "CC6.1" → "CC6", "164.312" → "164"
  const m = controlId.match(/^([A-Za-z]*\d+)/);
  return m ? m[1] : controlId.split('.')[0] || controlId;
}

function ComplianceTab() {
  const [activeFramework, setActiveFramework] = React.useState(COMPLIANCE_FRAMEWORKS[0]);
  const [expandedDomains, setExpandedDomains] = React.useState<Set<string>>(new Set());
  const { data: scansData, isLoading: scansLoading } = useCSPMScans();
  const { data: complianceData, isLoading: listLoading, error: listError } = useCSPMCompliance();
  const { data: frameworkData, isLoading: fwLoading, error: fwError } = useCSPMFramework(activeFramework);

  const scans = Array.isArray(scansData) ? scansData : [];
  const hasScans = scans.length > 0;

  const frameworks = complianceData?.frameworks ?? [];
  const summary = frameworks.find(f => f.framework === activeFramework);
  const controls = frameworkData?.controls ?? summary?.controls ?? [];

  // Group controls by domain
  const domainGroups = React.useMemo(() => {
    const map = new Map<string, typeof controls>();
    for (const ctrl of controls) {
      const ctrlId = (ctrl as any).id ?? ctrl.control_id ?? '';
      const domain = getDomainPrefix(ctrlId);
      if (!map.has(domain)) map.set(domain, []);
      map.get(domain)!.push(ctrl);
    }
    return Array.from(map.entries()).map(([domain, ctrls]) => {
      const passing = ctrls.filter(c => c.status === 'pass').length;
      const failing = ctrls.filter(c => c.status === 'fail').length;
      const pct = ctrls.length > 0 ? Math.round((passing / ctrls.length) * 100) : 0;
      return { domain, controls: ctrls, passing, failing, total: ctrls.length, pct };
    });
  }, [controls]);

  function toggleDomain(domain: string) {
    setExpandedDomains(prev => {
      const next = new Set(prev);
      if (next.has(domain)) next.delete(domain); else next.add(domain);
      return next;
    });
  }

  // Guard: no scans for this scope = no compliance data to show
  if (!scansLoading && !hasScans) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full"
          style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <Shield className="h-7 w-7" style={{ color: 'var(--text-tertiary)' }} />
        </div>
        <div>
          <div className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
            No compliance data for this account
          </div>
          <div className="text-xs max-w-xs" style={{ color: 'var(--text-secondary)' }}>
            Run a scan first to generate compliance results for this account.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {(listError || fwError) && <ErrorBanner message="Failed to load compliance data" />}

      {/* Framework selector */}
      <div className="mb-4 flex flex-wrap border-b" style={{ borderColor: 'var(--border-default)' }}>
        {COMPLIANCE_FRAMEWORKS.map(fw => {
          const fwData = frameworks.find(f => f.framework === fw);
          return (
            <button key={fw} onClick={() => { setActiveFramework(fw); setExpandedDomains(new Set()); }}
              className="px-4 py-2.5 text-sm transition-colors flex-shrink-0"
              style={{
                color: activeFramework === fw ? 'var(--text-primary)' : 'var(--text-link)',
                fontWeight: activeFramework === fw ? 700 : 400,
                borderBottom: activeFramework === fw ? '2px solid var(--aws-orange)' : '2px solid transparent',
                marginBottom: '-1px',
                backgroundColor: 'transparent',
              }}>
              {fw}
              {fwData && (
                <span className="ml-1.5 text-xs" style={{ color: postureColor(fwData.percentage) }}>
                  {fwData.percentage}%
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Summary bar */}
      {(listLoading || fwLoading) ? (
        <Skeleton className="h-16 mb-4" />
      ) : (summary || frameworkData) ? (() => {
        const d = frameworkData ?? summary!;
        return (
          <div className="mb-4 flex items-center gap-6 p-4" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid #d5dbdb' }}>
            <div>
              <div className="font-mono text-2xl font-bold" style={{ color: postureColor(d.percentage) }}>{d.percentage}%</div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{d.display_name || d.framework}</div>
            </div>
            <div className="flex-1 h-2 overflow-hidden rounded-full" style={{ backgroundColor: 'var(--border-default)' }}>
              <div className="h-full rounded-full" style={{ width: `${d.percentage}%`, backgroundColor: postureColor(d.percentage) }} />
            </div>
            <div className="flex gap-4 text-sm">
              <span style={{ color: 'var(--success)' }}>{d.passing} passing</span>
              <span style={{ color: 'var(--critical)' }}>{d.failing} failing</span>
              <span style={{ color: 'var(--text-tertiary)' }}>{d.not_applicable} N/A</span>
            </div>
          </div>
        );
      })() : null}

      {/* Controls list — grouped by domain */}
      {(listLoading || fwLoading) ? (
        <div className="space-y-2">{[1,2,3,4,5].map(i => <Skeleton key={i} className="h-10" />)}</div>
      ) : domainGroups.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
          No control data available for {activeFramework}
        </div>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              {['Control ID', 'Title', 'Status', 'Findings', 'Download'].map(h => (
                <th key={h} style={headerCellStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {domainGroups.map(group => (
              <React.Fragment key={group.domain}>
                {/* Domain row */}
                <tr
                  className="cursor-pointer"
                  onClick={() => toggleDomain(group.domain)}
                  style={{ backgroundColor: 'var(--bg-elevated)' }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--border-faint)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}>
                  <td style={{ ...cellStyle, fontWeight: 700 }} colSpan={2}>
                    <div className="flex items-center gap-2">
                      {expandedDomains.has(group.domain)
                        ? <ChevronUp className="h-3.5 w-3.5 flex-shrink-0" style={{ color: 'var(--text-secondary)' }} />
                        : <ChevronDown className="h-3.5 w-3.5 flex-shrink-0" style={{ color: 'var(--text-secondary)' }} />}
                      <span className="font-mono text-xs font-bold" style={{ color: 'var(--text-primary)' }}>Domain {group.domain}</span>
                      <div className="flex-1 h-1.5 overflow-hidden rounded-full ml-2" style={{ backgroundColor: 'var(--border-default)', maxWidth: '80px' }}>
                        <div className="h-full rounded-full" style={{ width: `${group.pct}%`, backgroundColor: postureColor(group.pct) }} />
                      </div>
                      <span className="text-xs font-semibold" style={{ color: postureColor(group.pct) }}>{group.pct}%</span>
                    </div>
                  </td>
                  <td style={cellStyle}>
                    <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{group.passing}/{group.total} passing</span>
                  </td>
                  <td style={cellStyle}>
                    {group.failing > 0 && <span className="text-xs font-semibold" style={{ color: 'var(--critical)' }}>{group.failing} failing</span>}
                  </td>
                  <td style={cellStyle} />
                </tr>
                {/* Individual controls */}
                {expandedDomains.has(group.domain) && group.controls.map(ctrl => {
                  const ctrlId = (ctrl as any).id ?? ctrl.control_id ?? '—';
                  return (
                  <tr key={ctrlId}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                    <td style={{ ...cellStyle, paddingLeft: '28px' }}><span className="font-mono text-xs">{ctrlId}</span></td>
                    <td style={{ ...cellStyle, maxWidth: '400px' }}>
                      <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{ctrl.title}</span>
                    </td>
                    <td style={cellStyle}>
                      <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold"
                        style={{
                          backgroundColor: ctrl.status === 'pass' ? 'var(--success-bg)' : ctrl.status === 'fail' ? 'var(--critical-bg)' : 'var(--bg-elevated)',
                          color: ctrl.status === 'pass' ? 'var(--success)' : ctrl.status === 'fail' ? 'var(--critical)' : 'var(--text-tertiary)',
                          border: `1px solid ${ctrl.status === 'pass' ? 'var(--low-border)' : ctrl.status === 'fail' ? 'var(--critical-border)' : 'var(--border-default)'}`,
                        }}>
                        {ctrl.status === 'pass' ? 'PASS' : ctrl.status === 'fail' ? 'FAIL' : 'N/A'}
                      </span>
                    </td>
                    <td style={cellStyle}>
                      {(ctrl.finding_count ?? 0) > 0 ? (
                        <span className="text-sm font-semibold" style={{ color: 'var(--critical)' }}>{ctrl.finding_count}</span>
                      ) : (
                        <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>0</span>
                      )}
                    </td>
                    <td style={cellStyle}>
                      <button
                        onClick={() => downloadControlCSV({ ...ctrl, id: ctrlId })}
                        className="rounded px-2 py-0.5 text-xs transition-colors"
                        style={{ color: 'var(--text-link)', border: '1px solid var(--border-default)', backgroundColor: 'transparent' }}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                        Download
                      </button>
                    </td>
                  </tr>
                  );
                })}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ─── Policies Tab ─────────────────────────────────────────────────────────────

function PoliciesTab() {
  const { data, isLoading, error } = useCSPMRules();
  const toggleRule = useToggleRule();
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
    await toggleRule.mutateAsync({ ruleId: rule.rule_id, enable: !rule.is_enabled });
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
              {/* Monaco-style editor */}
              <div className="relative rounded overflow-hidden" style={{ border: '1px solid #3c3c3c' }}>
                {/* Title bar */}
                <div className="flex items-center gap-2 px-3 py-1.5" style={{ backgroundColor: '#2d2d2d', borderBottom: '1px solid #3c3c3c' }}>
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#ff5f57' }} />
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#febc2e' }} />
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: '#28c840' }} />
                  <span className="ml-2 text-xs" style={{ color: '#858585', fontFamily: 'monospace' }}>policy.rego</span>
                </div>
                {/* Editor area with line numbers */}
                <div className="flex" style={{ backgroundColor: '#1e1e1e' }}>
                  {/* Line numbers */}
                  <div className="select-none py-3 pr-3 pl-3 text-right" style={{ backgroundColor: '#1e1e1e', borderRight: '1px solid #3c3c3c', minWidth: '40px', color: '#858585', fontFamily: 'monospace', fontSize: '13px', lineHeight: '1.5', userSelect: 'none' }}>
                    {regoCode.split('\n').map((_, i) => (
                      <div key={i}>{i + 1}</div>
                    ))}
                  </div>
                  {/* Code textarea */}
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

              {/* Test rule button + results */}
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

// ─── Inventory Tab ────────────────────────────────────────────────────────────

function InventoryTab() {
  const [typeFilter, setTypeFilter] = React.useState('');
  const [regionFilter, setRegionFilter] = React.useState('');
  const [envFilter, setEnvFilter] = React.useState('');
  const [searchQuery, setSearchQuery] = React.useState('');
  const [page, setPage] = React.useState(1);
  const [selectedResource, setSelectedResource] = React.useState<any | null>(null);

  const { data: resources, isLoading, error } = useCSPMResources({
    page: 1,
    page_size: 200,
  });

  const allItems = Array.isArray(resources) ? resources : [];

  // Unique values for filter dropdowns
  const uniqueTypes = React.useMemo(() => Array.from(new Set(allItems.map(r => r.resource_type).filter(Boolean))).sort(), [allItems]);
  const uniqueRegions = React.useMemo(() => Array.from(new Set(allItems.map(r => r.region).filter(Boolean))).sort(), [allItems]);

  // Client-side filtering
  const filteredItems = React.useMemo(() => {
    return allItems.filter(r => {
      if (typeFilter && r.resource_type !== typeFilter) return false;
      if (regionFilter && r.region !== regionFilter) return false;
      if (envFilter && r.environment !== envFilter) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const name = (r.resource_name || r.resource_id || '').toLowerCase();
        if (!name.includes(q)) return false;
      }
      return true;
    });
  }, [allItems, typeFilter, regionFilter, envFilter, searchQuery]);

  const PAGE_SIZE = 50;
  const totalPages = Math.ceil(filteredItems.length / PAGE_SIZE);
  const items = filteredItems.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div style={{ paddingBottom: selectedResource ? '280px' : '0' }}>
      {error && <ErrorBanner message="Failed to load resource inventory" />}

      {/* Search + Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Search by resource name…"
          value={searchQuery}
          onChange={e => { setSearchQuery(e.target.value); setPage(1); }}
          className="rounded border px-3 py-1.5 text-sm"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)', minWidth: '220px' }}
        />
        <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setPage(1); }}
          className="rounded border px-2 py-1.5 text-sm"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All Types</option>
          {uniqueTypes.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={regionFilter} onChange={e => { setRegionFilter(e.target.value); setPage(1); }}
          className="rounded border px-2 py-1.5 text-sm"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All Regions</option>
          {uniqueRegions.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <select value={envFilter} onChange={e => { setEnvFilter(e.target.value); setPage(1); }}
          className="rounded border px-2 py-1.5 text-sm"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All Environments</option>
          <option value="prod">prod</option>
          <option value="staging">staging</option>
          <option value="dev">dev</option>
        </select>
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{filteredItems.length} resources</span>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[1,2,3,4,5].map(i => <Skeleton key={i} className="h-10" />)}</div>
      ) : items.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
          No resources found
        </div>
      ) : (
        <>
          <table style={tableStyle}>
            <thead>
              <tr>
                {['Resource Name', 'Type', 'Provider', 'Account', 'Region', 'Environment', 'Risk Score', 'Open Findings'].map(h => (
                  <th key={h} style={headerCellStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map(r => {
                const totalFindings = r.critical_count + r.high_count + r.medium_count + r.low_count;
                return (
                  <tr key={r.id}
                    className="cursor-pointer"
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = selectedResource?.id === r.id ? 'var(--bg-elevated)' : 'transparent')}
                    onClick={() => setSelectedResource(selectedResource?.id === r.id ? null : r)}>
                    <td style={{ ...cellStyle, maxWidth: '200px' }}>
                      <div className="truncate text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{r.resource_name || r.resource_id}</div>
                    </td>
                    <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.resource_type}</span></td>
                    <td style={cellStyle}><span className="text-xs uppercase" style={{ color: 'var(--text-secondary)' }}>{r.provider}</span></td>
                    <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.account_id}</span></td>
                    <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.region}</span></td>
                    <td style={cellStyle}>
                      {r.environment && (
                        <span className="rounded px-1.5 py-0.5 text-xs"
                          style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)', color: 'var(--text-secondary)' }}>
                          {r.environment}
                        </span>
                      )}
                    </td>
                    <td style={cellStyle}>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-semibold" style={{ color: riskColor(r.risk_score) }}>{r.risk_score}</span>
                        <div className="h-1.5 w-16 overflow-hidden rounded-full" style={{ backgroundColor: 'var(--border-default)' }}>
                          <div className="h-full rounded-full" style={{ width: `${r.risk_score}%`, backgroundColor: riskColor(r.risk_score) }} />
                        </div>
                      </div>
                    </td>
                    <td style={cellStyle}>
                      {totalFindings > 0 ? (
                        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                          {r.critical_count > 0 && <span>{r.critical_count} Critical</span>}
                          {r.high_count > 0 && <span>{r.high_count} High</span>}
                          {r.medium_count > 0 && <span>{r.medium_count} Medium</span>}
                          {r.low_count > 0 && <span>{r.low_count} Low</span>}
                        </div>
                      ) : (
                        <span className="text-xs" style={{ color: 'var(--success)' }}>Clean</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t px-4 py-2" style={{ borderColor: 'var(--border-default)' }}>
              <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Page {page} of {totalPages}</span>
              <div className="flex gap-2">
                <Button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="h-7 px-3 text-xs">Prev</Button>
                <Button onClick={() => setPage(p => p + 1)} disabled={page >= totalPages} className="h-7 px-3 text-xs">Next</Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Resource detail split panel */}
      {selectedResource && (
        <div
          className="fixed bottom-0 left-0 right-0 z-40 border-t"
          style={{
            height: '280px',
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border-default)',
            boxShadow: 'var(--shadow-split)',
          }}
        >
          <div className="flex h-10 items-center justify-between border-b px-4" style={{ borderColor: 'var(--border-faint)' }}>
            <div className="flex items-center gap-3 min-w-0">
              <span className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                {selectedResource.resource_name || selectedResource.resource_id}
              </span>
              <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{selectedResource.resource_type}</span>
              <span className="text-xs uppercase font-semibold" style={{ color: 'var(--text-secondary)' }}>{selectedResource.provider}</span>
            </div>
            <button onClick={() => setSelectedResource(null)}
              className="flex h-7 w-7 items-center justify-center rounded"
              style={{ color: 'var(--text-tertiary)' }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="h-[calc(280px-40px)] overflow-y-auto p-4">
            <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm sm:grid-cols-4">
              {[
                ['Account', selectedResource.account_id],
                ['Region', selectedResource.region],
                ['Environment', selectedResource.environment || 'unknown'],
                ['Risk Score', selectedResource.risk_score],
                ['Internet Exposed', selectedResource.is_internet_exposed ? 'Yes' : 'No'],
                ['Sensitive Data', selectedResource.contains_sensitive_data ? 'Yes' : 'No'],
                ['Last Scanned', selectedResource.last_scanned_at ? timeAgo(selectedResource.last_scanned_at) : '—'],
                ['Resource ID', selectedResource.resource_id],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <div className="text-xs font-semibold mb-0.5" style={{ color: 'var(--text-secondary)' }}>{label}</div>
                  <div className="text-sm font-mono truncate" style={{ color: 'var(--text-primary)' }}>{String(value ?? '—')}</div>
                </div>
              ))}
            </div>
            {(selectedResource.critical_count + selectedResource.high_count + selectedResource.medium_count + selectedResource.low_count) > 0 && (
              <div className="mt-4">
                <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Open Findings</div>
                <div className="flex gap-3 flex-wrap text-xs" style={{ color: 'var(--text-secondary)' }}>
                  {selectedResource.critical_count > 0 && <span>{selectedResource.critical_count} Critical</span>}
                  {selectedResource.high_count > 0 && <span>{selectedResource.high_count} High</span>}
                  {selectedResource.medium_count > 0 && <span>{selectedResource.medium_count} Medium</span>}
                  {selectedResource.low_count > 0 && <span>{selectedResource.low_count} Low</span>}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Scan History Tab ─────────────────────────────────────────────────────────

function ScanHistoryTab() {
  const { data: scans, isLoading, error } = useCSPMScans();
  const triggerScan = useTriggerScan();

  const items = Array.isArray(scans) ? scans : [];

  const statusStyle = (status: string): React.CSSProperties => {
    if (status === 'completed') return { color: 'var(--success)', backgroundColor: 'var(--success-bg)', border: '1px solid var(--low-border)' };
    if (status === 'running' || status === 'in_progress') return { color: 'var(--warning)', backgroundColor: 'var(--medium-bg)', border: '1px solid var(--medium-border)' };
    if (status === 'failed') return { color: 'var(--critical)', backgroundColor: 'var(--critical-bg)', border: '1px solid var(--critical-border)' };
    return { color: 'var(--text-secondary)', backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' };
  };

  return (
    <div>
      {error && <ErrorBanner message="Failed to load scan history" />}

      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{items.length} scans</span>
        <Button onClick={() => triggerScan.mutate({})} disabled={triggerScan.isPending} className="gap-2 h-8 px-3 text-sm">
          {triggerScan.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
          Run Scan
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">{[1,2,3,4].map(i => <Skeleton key={i} className="h-10" />)}</div>
      ) : items.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
          No scans found. Run your first scan to get started.
        </div>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              {['Scan ID', 'Type', 'Status', 'Started', 'Duration', 'Resources Scanned', 'Findings Created'].map(h => (
                <th key={h} style={headerCellStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(scan => (
              <tr key={scan.id}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                <td style={cellStyle}>
                  <span className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }} title={scan.id}>
                    {scan.id.slice(0, 8)}…
                  </span>
                </td>
                <td style={cellStyle}><span className="text-xs capitalize" style={{ color: 'var(--text-secondary)' }}>{scan.scan_type.replace('_', ' ')}</span></td>
                <td style={cellStyle}>
                  <span className="rounded px-2 py-0.5 text-xs font-semibold capitalize" style={statusStyle(scan.status)}>
                    {scan.status}
                  </span>
                </td>
                <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{timeAgo(scan.started_at)}</span></td>
                <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{formatDuration(scan.started_at, scan.completed_at)}</span></td>
                <td style={cellStyle}><span className="text-sm" style={{ color: 'var(--text-primary)' }}>{scan.resources_scanned?.toLocaleString() ?? '—'}</span></td>
                <td style={cellStyle}>
                  {scan.findings_created > 0 ? (
                    <span className="text-sm font-semibold" style={{ color: 'var(--critical)' }}>{scan.findings_created}</span>
                  ) : (
                    <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{scan.findings_created ?? '—'}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ─── Reports Tab ──────────────────────────────────────────────────────────────

function ReportsTab() {
  const { data: reports, isLoading, error } = useCSPMReports();
  const createReport = useCreateReport();
  const [showModal, setShowModal] = React.useState(false);
  const [reportType, setReportType] = React.useState('findings_export');
  const [framework, setFramework] = React.useState('CIS-AWS');
  const [format, setFormat] = React.useState('csv');
  const [pollingId, setPollingId] = React.useState<string | null>(null);
  const { data: polledReport } = useCSPMReport(pollingId);

  React.useEffect(() => {
    if (polledReport && (polledReport as any).status === 'ready') setPollingId(null);
  }, [polledReport]);

  const items = Array.isArray(reports) ? reports : [];

  async function handleCreate() {
    const payload: Parameters<typeof cspmAPI.createReport>[0] = {
      report_type: reportType,
      format,
      ...(reportType === 'compliance' ? { framework } : {}),
    };
    const result = await createReport.mutateAsync(payload);
    setShowModal(false);
    setPollingId((result as any).id);
  }

  function statusStyle(status: string): React.CSSProperties {
    if (status === 'ready') return { color: 'var(--success)', backgroundColor: 'var(--success-bg)', border: '1px solid var(--low-border)' };
    if (status === 'generating') return { color: 'var(--warning)', backgroundColor: 'var(--medium-bg)', border: '1px solid var(--medium-border)' };
    if (status === 'failed') return { color: 'var(--critical)', backgroundColor: 'var(--critical-bg)', border: '1px solid var(--critical-border)' };
    return { color: 'var(--text-secondary)', backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' };
  }

  return (
    <div>
      {error && <ErrorBanner message="Failed to load reports" />}
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{items.length} reports</span>
        <Button onClick={() => setShowModal(true)} className="gap-2 h-8 px-3 text-sm">
          <Shield className="h-3.5 w-3.5" />
          Generate Report
        </Button>
      </div>
      {isLoading ? (
        <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-10" />)}</div>
      ) : items.length === 0 ? (
        <div className="flex h-40 flex-col items-center justify-center gap-3"
          style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid #d5dbdb' }}>
          <Shield className="h-8 w-8" style={{ color: 'var(--text-tertiary)' }} />
          <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>No reports yet</div>
          <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Generate your first compliance or posture report</div>
          <Button onClick={() => setShowModal(true)} className="h-8 px-3 text-sm">Generate Report</Button>
        </div>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              {['Type', 'Framework', 'Format', 'Status', 'Created', 'Size', 'Download'].map(h => (
                <th key={h} style={headerCellStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(report => (
              <tr key={report.id}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                <td style={cellStyle}><span className="text-sm capitalize" style={{ color: 'var(--text-primary)' }}>{report.report_type.replace('_', ' ')}</span></td>
                <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{report.framework || ''}</span></td>
                <td style={cellStyle}><span className="text-xs uppercase" style={{ color: 'var(--text-secondary)' }}>{report.format}</span></td>
                <td style={cellStyle}>
                  <span className="rounded px-2 py-0.5 text-xs font-semibold capitalize" style={statusStyle(report.status)}>
                    {report.status}
                  </span>
                </td>
                <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{timeAgo(report.created_at)}</span></td>
                <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{report.file_size_bytes ? `${Math.round(report.file_size_bytes / 1024)}KB` : ''}</span></td>
                <td style={cellStyle}>
                  {report.status === 'ready' ? (
                    <a href={cspmAPI.getReportDownloadUrl(report.id)} download={`report-${report.id}.csv`}
                      className="rounded px-2 py-0.5 text-xs"
                      style={{ color: 'var(--text-link)', border: '1px solid var(--border-default)', textDecoration: 'none' }}>
                      Download
                    </a>
                  ) : <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}></span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="w-full max-w-md rounded-lg" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)' }}>
            <div className="flex items-center justify-between border-b px-6 py-4" style={{ borderColor: 'var(--border-default)' }}>
              <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Generate Report</h2>
              <button onClick={() => setShowModal(false)} style={{ color: 'var(--text-tertiary)' }}><X className="h-4 w-4" /></button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Report Type</label>
                <select value={reportType} onChange={e => setReportType(e.target.value)}
                  className="w-full rounded border px-3 py-2 text-sm"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                  <option value="findings_export">Findings Export</option>
                  <option value="posture">Posture Report</option>
                  <option value="compliance">Compliance Report</option>
                </select>
              </div>
              {reportType === 'compliance' && (
                <div>
                  <label className="block text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Framework</label>
                  <select value={framework} onChange={e => setFramework(e.target.value)}
                    className="w-full rounded border px-3 py-2 text-sm"
                    style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                    {COMPLIANCE_FRAMEWORKS.map(fw => <option key={fw} value={fw}>{fw}</option>)}
                  </select>
                </div>
              )}
              <div>
                <label className="block text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Format</label>
                <select value={format} onChange={e => setFormat(e.target.value)}
                  className="w-full rounded border px-3 py-2 text-sm"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                  <option value="csv">CSV</option>
                </select>
                <p className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>PDF export coming soon</p>
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t px-6 py-4" style={{ borderColor: 'var(--border-default)' }}>
              <Button onClick={() => setShowModal(false)} className="h-8 px-3 text-sm">Cancel</Button>
              <Button onClick={handleCreate} disabled={createReport.isPending} className="h-8 px-3 text-sm gap-2">
                {createReport.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                Generate
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CSPMPage() {
  const [activeTab, setActiveTab] = React.useState('overview');
  const { data: stats, isLoading: statsLoading } = useCSPMStats();
  const { data: scansData } = useCSPMScans();
  const triggerScan = useTriggerScan();
  const [flashbarDismissed, setFlashbarDismissed] = React.useState(false);

  // Read account filter from global scope store (set via header ScopeSelector)
  const accountIds = useScopeStore(s => s.accountIds);

  React.useEffect(() => {
    document.title = 'CSPM - CloudVisor';
  }, []);

  const scans = Array.isArray(scansData) ? scansData : [];
  const latestScan = scans[0];
  const scanRunning = triggerScan.isPending || latestScan?.status === 'running' || latestScan?.status === 'in_progress';

  React.useEffect(() => {
    if (scanRunning) setFlashbarDismissed(false);
  }, [scanRunning]);

  return (
    <ProtectedRoute>
      <AppLayout
        breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'CSPM' }]}
        cspmActiveTab={activeTab}
        onCspmTabChange={setActiveTab}
      >
        {accountIds.length === 0 ? (
          <NoAccountsConnectedEmptyState />
        ) : !statsLoading && stats && stats.total_resources === 0 && scans.length === 0 ? (
          <NoScanDataEmptyState
            title="No scan data for this account"
            description="This account hasn't been scanned yet. Run a scan to discover resources and security findings."
          />
        ) : (
          <>
        {/* Scan progress Flashbar */}
        {scanRunning && !flashbarDismissed && (
          <div className="mb-4 flex items-center gap-3 px-4 py-3"
            style={{
              backgroundColor: '#e8f4fd',
              border: '1px solid #a8d5f5',
              borderLeft: '4px solid #0073bb',
            }}>
            <span style={{ color: '#0073bb', fontSize: '16px' }}>ⓘ</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold mb-1" style={{ color: '#0073bb' }}>
                Scan in progress — {latestScan?.scan_type?.replace('_', ' ') ?? 'On-demand scan'}
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 overflow-hidden rounded-full" style={{ backgroundColor: '#a8d5f5', maxWidth: '200px' }}>
                  <div className="h-full rounded-full"
                    style={{ width: '60%', backgroundColor: '#0073bb', animation: 'cspm-scan-progress 1.5s ease-in-out infinite alternate' }} />
                </div>
                <span className="text-xs" style={{ color: '#0073bb' }}>Scanning resources…</span>
              </div>
            </div>
            <button onClick={() => setFlashbarDismissed(true)} className="flex-shrink-0 text-sm" style={{ color: '#0073bb' }}>✕</button>
          </div>
        )}
        <style>{`
          @keyframes cspm-scan-progress {
            from { width: 20%; margin-left: 0%; }
            to { width: 40%; margin-left: 60%; }
          }
        `}</style>

        {/* Page header — no account switcher here, it's in the global header */}
        <div className="mb-4">
          <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Cloud Security Posture Management</h1>
          <p className="mt-0.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
            {statsLoading ? 'Loading…' : stats
              ? `${stats.total_resources.toLocaleString()} resources · last scan ${timeAgo(stats.last_scan_at)}`
              : 'Monitor and remediate cloud misconfigurations'}
          </p>
        </div>

        {activeTab === 'overview' && (
          <OverviewTab
            triggerScan={triggerScan}
            scanRunning={scanRunning}
          />
        )}
        {activeTab === 'misconfigurations' && (
          <MisconfigurationsTab />
        )}
        {activeTab === 'compliance' && <ComplianceTab />}
        {activeTab === 'policies' && <PoliciesTab />}
        {activeTab === 'inventory' && (
          <InventoryTab />
        )}
        {activeTab === 'reports' && <ReportsTab />}
        {activeTab === 'scan-history' && <ScanHistoryTab />}
          </>
        )}
      </AppLayout>
    </ProtectedRoute>
  );
}