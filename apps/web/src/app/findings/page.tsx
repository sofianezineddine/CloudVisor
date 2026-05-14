'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle, CheckCircle2, Clock, Filter, Search,
  ChevronRight, Loader2, RefreshCw, X, Shield,
  AlertCircle, Info, TrendingDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import apiClient, { type Finding } from '@/lib/api/apiClient';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';

// ─── Severity badge ───────────────────────────────────────────────────────────

const SEVERITY_STYLES: Record<string, { bg: string; color: string; icon: React.ElementType }> = {
  CRITICAL: { bg: 'var(--critical-bg)', color: 'var(--critical)', icon: AlertTriangle },
  HIGH:     { bg: 'var(--high-bg)',     color: 'var(--high)',     icon: AlertCircle },
  MEDIUM:   { bg: 'var(--medium-bg)',   color: 'var(--medium)',   icon: AlertCircle },
  LOW:      { bg: 'var(--low-bg)',      color: 'var(--low)',      icon: Info },
  INFO:     { bg: 'var(--info-bg)',     color: 'var(--info)',     icon: Info },
};

function SeverityBadge({ severity }: { severity: string }) {
  const style = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.INFO;
  return (
    <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold"
      style={{ backgroundColor: style.bg, color: style.color }}>
      {severity}
    </span>
  );
}

const STATUS_STYLES: Record<string, { color: string; label: string }> = {
  open:          { color: 'var(--critical)', label: 'Open' },
  in_progress:   { color: 'var(--medium)',   label: 'In Progress' },
  resolved:      { color: 'var(--success)',  label: 'Resolved' },
  suppressed:    { color: 'var(--info)',     label: 'Suppressed' },
  accepted_risk: { color: '#a855f7',         label: 'Accepted Risk' },
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? { color: 'var(--text-secondary)', label: status };
  return (
    <span className="inline-flex items-center gap-1 text-xs"
      style={{ color: style.color }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: style.color }} />
      {style.label}
    </span>
  );
}

// ─── Finding detail drawer ────────────────────────────────────────────────────

function FindingDetailDrawer({ finding, onClose }: { finding: Finding; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [suppressReason, setSuppressReason] = React.useState('');
  const [showSuppress, setShowSuppress] = React.useState(false);

  const updateMutation = useMutation({
    mutationFn: (status: string) => apiClient.findings.update(finding.id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['findings'] });
      toast.success('Finding updated');
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const suppressMutation = useMutation({
    mutationFn: () => apiClient.findings.suppress(finding.id, suppressReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['findings'] });
      toast.success('Finding suppressed');
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const acceptRiskMutation = useMutation({
    mutationFn: () => apiClient.findings.acceptRisk(finding.id, 'Accepted via findings page'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['findings'] });
      toast.success('Risk accepted');
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex flex-col shadow-2xl"
      style={{ width: 480, backgroundColor: 'var(--bg-surface)', borderLeft: '1px solid var(--border-default)' }}>
      <div className="flex items-center justify-between px-5 py-4 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border-default)' }}>
        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Finding Detail</h3>
        <button onClick={onClose} style={{ color: 'var(--text-tertiary)' }}>
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <SeverityBadge severity={finding.severity} />
            <StatusBadge status={finding.status} />
          </div>
          <h4 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            {finding.title}
          </h4>
          <p className="text-xs font-mono mt-1" style={{ color: 'var(--text-tertiary)' }}>
            {finding.rule_id}
          </p>
        </div>

        {/* Resource info */}
        <div className="rounded-lg p-3 space-y-1.5"
          style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-faint)' }}>
          {[
            ['Resource', finding.resource_name || finding.resource_id],
            ['Account', finding.account_id],
            ['Region', finding.region],
            ['Provider', finding.provider?.toUpperCase()],
            ['Type', finding.resource_type],
          ].filter(([, v]) => v).map(([label, value]) => (
            <div key={label as string} className="flex items-start gap-2">
              <span className="text-xs w-16 flex-shrink-0" style={{ color: 'var(--text-tertiary)' }}>{label}</span>
              <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>{value}</span>
            </div>
          ))}
        </div>

        {finding.description && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-tertiary)' }}>Description</p>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{finding.description}</p>
          </div>
        )}

        {finding.remediation && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-tertiary)' }}>Remediation</p>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{finding.remediation}</p>
          </div>
        )}

        {finding.compliance_mapping && finding.compliance_mapping.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--text-tertiary)' }}>Compliance</p>
            <div className="flex flex-wrap gap-1.5">
              {finding.compliance_mapping.map((m: any, i: number) => (
                <span key={i} className="rounded px-2 py-0.5 text-xs"
                  style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                  {typeof m === 'string' ? m : `${m.framework} ${m.control}`}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="text-xs space-y-1" style={{ color: 'var(--text-tertiary)' }}>
          <div>First seen: {new Date(finding.first_seen_at).toLocaleString()}</div>
          <div>Last seen: {new Date(finding.last_seen_at).toLocaleString()}</div>
          {(finding as any).regression_count > 0 && (
            <div style={{ color: 'var(--warning)' }}>
              Regressed {(finding as any).regression_count} time(s)
            </div>
          )}
        </div>

        {/* Actions */}
        {finding.status === 'open' && (
          <div className="pt-2 border-t space-y-2" style={{ borderColor: 'var(--border-faint)' }}>
            <Button size="sm" className="w-full gap-1.5 text-xs"
              onClick={() => updateMutation.mutate('in_progress')}
              disabled={updateMutation.isPending}>
              {updateMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              Mark In Progress
            </Button>
            <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs"
              onClick={() => updateMutation.mutate('resolved')}
              disabled={updateMutation.isPending}>
              Mark Resolved
            </Button>
            <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs"
              onClick={() => acceptRiskMutation.mutate()}
              disabled={acceptRiskMutation.isPending}>
              Accept Risk
            </Button>
            {!showSuppress ? (
              <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs"
                onClick={() => setShowSuppress(true)}>
                Suppress
              </Button>
            ) : (
              <div className="space-y-2">
                <input
                  type="text"
                  value={suppressReason}
                  onChange={e => setSuppressReason(e.target.value)}
                  placeholder="Reason for suppression (min 20 chars)"
                  className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
                />
                <div className="flex gap-2">
                  <Button size="sm" className="flex-1 text-xs"
                    onClick={() => suppressMutation.mutate()}
                    disabled={suppressReason.length < 20 || suppressMutation.isPending}>
                    Confirm Suppress
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setShowSuppress(false)}>Cancel</Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function FindingsPage() {
  const [severityFilter, setSeverityFilter] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState('open');
  const [selectedFinding, setSelectedFinding] = React.useState<Finding | null>(null);
  const [search, setSearch] = React.useState('');

  React.useEffect(() => {
    document.title = 'Findings - CloudVisor';
  }, []);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['findings', severityFilter, statusFilter],
    queryFn: () => apiClient.findings.list({
      severity: severityFilter || undefined,
      status: statusFilter || undefined,
      limit: 200,
    }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const findings: Finding[] = (data?.data as Finding[]) ?? [];

  // Client-side search filter
  const filtered = search.trim()
    ? findings.filter(f =>
        f.title.toLowerCase().includes(search.toLowerCase()) ||
        f.rule_id.toLowerCase().includes(search.toLowerCase()) ||
        (f.resource_name ?? '').toLowerCase().includes(search.toLowerCase()) ||
        (f.resource_id ?? '').toLowerCase().includes(search.toLowerCase())
      )
    : findings;

  // Stats
  const stats = React.useMemo(() => {
    const all = findings;
    return {
      critical: all.filter(f => f.severity === 'CRITICAL' && f.status === 'open').length,
      high: all.filter(f => f.severity === 'HIGH' && f.status === 'open').length,
      open: all.filter(f => f.status === 'open').length,
      total: all.length,
    };
  }, [findings]);

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Findings' }]}>
        <div className="px-6 py-4">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>
                Findings
              </h1>
              <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching} className="gap-1.5">
                <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Security findings across all cloud accounts and modules
            </p>
          </div>

      {/* Stats row */}
      {!isLoading && (
        <div className="grid grid-cols-2 gap-3 mb-6 sm:grid-cols-4">
          {[
            { label: 'Critical', value: stats.critical, color: 'var(--critical)', bg: 'var(--critical-bg)' },
            { label: 'High', value: stats.high, color: 'var(--high)', bg: 'var(--high-bg)' },
            { label: 'Open', value: stats.open, color: 'var(--text-primary)', bg: 'var(--bg-elevated)' },
            { label: 'Total', value: stats.total, color: 'var(--text-primary)', bg: 'var(--bg-elevated)' },
          ].map(({ label, value, color, bg }) => (
            <div key={label} className="rounded-lg border p-4 text-center"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
              <div className="font-mono text-2xl font-bold" style={{ color }}>{value}</div>
              <div className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5" style={{ color: 'var(--text-tertiary)' }} />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search findings…"
            className="w-full rounded-md border pl-9 pr-3 py-2 text-sm focus:outline-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
          />
        </div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="rounded-md border px-3 py-2 text-sm focus:outline-none"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="suppressed">Suppressed</option>
          <option value="accepted_risk">Accepted Risk</option>
        </select>
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}
          className="rounded-md border px-3 py-2 text-sm focus:outline-none"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All severities</option>
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'].map(s => <option key={s}>{s}</option>)}
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
        </div>
      ) : isError ? (
        <div className="rounded-lg border p-8 text-center"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <AlertTriangle className="h-8 w-8 mx-auto mb-3" style={{ color: 'var(--warning)' }} />
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Could not load findings</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>Retry</Button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border p-12 flex flex-col items-center gap-3 text-center"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <Shield className="h-10 w-10" style={{ color: 'var(--success)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            {search || severityFilter || statusFilter ? 'No findings match your filters' : 'No findings'}
          </h3>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            {!search && !severityFilter && !statusFilter
              ? 'Your cloud environment looks clean!'
              : 'Try adjusting your filters.'}
          </p>
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <div className="px-4 py-3 border-b text-xs font-medium"
            style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
            {filtered.length} finding{filtered.length !== 1 ? 's' : ''}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}>
                  {['Severity', 'Title', 'Resource', 'Account', 'Age', 'Status', ''].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium"
                      style={{ color: 'var(--text-secondary)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((finding) => {
                  const age = Math.floor((Date.now() - new Date(finding.first_seen_at).getTime()) / 86400000);
                  return (
                    <tr key={finding.id}
                      className="border-b cursor-pointer transition-colors"
                      style={{ borderColor: 'var(--border-faint)' }}
                      onClick={() => setSelectedFinding(finding)}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                      <td className="px-4 py-3">
                        <SeverityBadge severity={finding.severity} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm font-medium truncate max-w-xs" style={{ color: 'var(--text-primary)' }}>
                          {finding.title}
                        </div>
                        <div className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
                          {finding.rule_id}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs" style={{ color: 'var(--text-secondary)' }}>
                        {finding.resource_name || finding.resource_id?.slice(-20) || '—'}
                      </td>
                      <td className="px-4 py-3 text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                        {finding.account_id?.slice(-12) || '—'}
                      </td>
                      <td className="px-4 py-3 text-xs" style={{ color: age > 7 ? 'var(--warning)' : 'var(--text-tertiary)' }}>
                        {age === 0 ? 'Today' : `${age}d`}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={finding.status} />
                      </td>
                      <td className="px-4 py-3">
                        <ChevronRight className="h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detail drawer */}
      {selectedFinding && (
        <>
          <div className="fixed inset-0 z-40 bg-black/20" onClick={() => setSelectedFinding(null)} />
          <FindingDetailDrawer finding={selectedFinding} onClose={() => setSelectedFinding(null)} />
        </>
      )}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
