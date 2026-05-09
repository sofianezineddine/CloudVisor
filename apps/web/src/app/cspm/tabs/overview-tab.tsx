'use client';

import * as React from 'react';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  Play, Loader2, AlertTriangle, CheckCircle2,
} from 'lucide-react';
import {
  useCSPMPosture, useCSPMFindings, useCSPMResources, useCSPMScans, useTriggerScan,
} from '@/hooks/use-cspm';

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

export function OverviewTab({
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

  // Top 10 riskiest resources
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
        <div className="p-4 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          {postureLoading ? <Skeleton className="h-10 w-20 mb-2" /> : (
            <div className="font-mono text-3xl font-bold" style={{ color: postureColor(score) }}>{score}%</div>
          )}
          <div className="mt-1 text-xs mb-2" style={{ color: 'var(--text-secondary)' }}>Posture Score</div>
          <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ backgroundColor: 'var(--border-default)' }}>
            <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, backgroundColor: postureColor(score) }} />
          </div>
        </div>

        {/* Total Findings */}
        <div className="p-4 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
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
        <div className="p-4 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          {postureLoading ? <Skeleton className="h-10 w-16 mb-2" /> : (
            <div className="font-mono text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
              {posture?.resources_evaluated?.toLocaleString() ?? '—'}
            </div>
          )}
          <div className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>Resources Evaluated</div>
        </div>

        {/* Compliance % */}
        <div className="p-4 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          {postureLoading ? <Skeleton className="h-10 w-16 mb-2" /> : (
            <div className="font-mono text-3xl font-bold" style={{ color: postureColor(posture?.compliance_percentage ?? 0) }}>
              {posture?.compliance_percentage ?? '—'}{posture ? '%' : ''}
            </div>
          )}
          <div className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>Compliance</div>
        </div>
      </div>

      {/* Finding trend chart */}
      <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
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

      {/* Top 10 riskiest resources */}
      <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
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
      <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
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
      <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
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
