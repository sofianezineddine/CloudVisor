'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { StatusBadge } from '@/components/ui/status-badge';
import { Button } from '@/components/ui/button';
import { CvContainer } from '@/components/ui/cv-container';
import { FindingDetailDrawer } from '@/components/ui/finding-detail-drawer';
import {
  Search, Download, ChevronLeft, ChevronRight,
  MoreHorizontal, RefreshCw, Loader2, X, CheckCircle2, SlidersHorizontal,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Finding } from '@/lib/api/apiClient';
import { useFindings, useFindingStats, useBulkUpdateFindings, useUpdateFinding } from '@/hooks/use-findings';
import { useQueryClient } from '@tanstack/react-query';
import { NoAccountsConnectedEmptyState } from '@/components/ui/no-accounts-empty-state';
import { NoScanDataEmptyState } from '@/components/ui/no-scan-empty-state';
import { useScopeStore } from '@/stores/scope';

const PAGE_SIZE = 50;
const SEVERITY_OPTIONS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as const;
const STATUS_OPTIONS = [
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'suppressed', label: 'Suppressed' },
  { value: 'accepted_risk', label: 'Accepted risk' },
] as const;

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function formatResourceType(rt: string | null): string {
  if (!rt) return '';
  const parts = rt.split('::');
  return parts[parts.length - 1].replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium"
      style={{ borderColor: 'var(--accent)', backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}
    >
      {label}
      <button onClick={onRemove} className="ml-0.5 rounded-full p-0.5 transition-colors">
        <X className="h-2.5 w-2.5" />
      </button>
    </span>
  );
}

function FindingActions({ finding, onStatusChange }: { finding: Finding; onStatusChange: (id: string, status: string) => void }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const actions = [
    { label: 'Mark in progress', status: 'in_progress', show: finding.status === 'open' },
    { label: 'Resolve', status: 'resolved', show: ['open', 'in_progress'].includes(finding.status) },
    { label: 'Suppress', status: 'suppressed', show: finding.status === 'open' },
    { label: 'Accept risk', status: 'accepted_risk', show: finding.status === 'open' },
    { label: 'Reopen', status: 'open', show: ['resolved', 'suppressed', 'accepted_risk'].includes(finding.status) },
  ].filter(a => a.show);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(o => !o); }}
        className="rounded p-1 transition-colors"
        style={{ color: 'var(--text-tertiary)' }}
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>
      {open && (
        <div
          className="absolute right-0 top-full z-50 mt-1 w-44 rounded-lg overflow-hidden"
          style={{ border: '1px solid var(--border-default)', backgroundColor: 'var(--bg-overlay)', boxShadow: 'var(--shadow-popover)' }}
        >
          {actions.map(a => (
            <button
              key={a.status}
              onClick={(e) => { e.stopPropagation(); onStatusChange(finding.id, a.status); setOpen(false); }}
              className="w-full px-3 py-2 text-left text-sm transition-colors"
              style={{ color: 'var(--text-primary)' }}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function FindingsPage() {
  const queryClient = useQueryClient();
  const accountIds = useScopeStore(s => s.accountIds);

  // Set browser tab title
  React.useEffect(() => {
    document.title = 'Findings - CloudVisor';
  }, []);
  const [selectedSeverities, setSelectedSeverities] = React.useState<Set<string>>(new Set());
  const [selectedStatuses, setSelectedStatuses] = React.useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = React.useState('');
  const [debouncedSearch, setDebouncedSearch] = React.useState('');
  const [showFilterPanel, setShowFilterPanel] = React.useState(true);
  const [selectedRows, setSelectedRows] = React.useState<Set<string>>(new Set());
  const [offset, setOffset] = React.useState(0);
  const [selectedFindingId, setSelectedFindingId] = React.useState<string | null>(null);
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  React.useEffect(() => { setOffset(0); }, [selectedSeverities, selectedStatuses, debouncedSearch]);

  const queryParams = React.useMemo(() => {
    const params: Record<string, any> = { limit: PAGE_SIZE, offset };
    if (selectedSeverities.size > 0) params.severity = Array.from(selectedSeverities).join(',');
    if (selectedStatuses.size > 0) params.status = Array.from(selectedStatuses).join(',');
    return params;
  }, [selectedSeverities, selectedStatuses, offset]);

  const { data: findingsData, isLoading: loading, isError, error: queryError, refetch } = useFindings(queryParams);
  const { data: statsData } = useFindingStats();
  const updateFinding = useUpdateFinding();
  const bulkUpdate = useBulkUpdateFindings();

  const findings: Finding[] = (findingsData?.data as Finding[]) ?? [];
  const total: number = (findingsData as any)?.total ?? (findingsData as any)?.meta?.total ?? 0;
  const stats: Record<string, any> = (statsData?.data as any) ?? {};
  const error = isError ? (queryError instanceof Error ? queryError.message : 'Failed to load findings') : null;

  const filteredFindings = React.useMemo(() => {
    if (!debouncedSearch) return findings;
    const q = debouncedSearch.toLowerCase();
    return findings.filter(f =>
      f.title.toLowerCase().includes(q) ||
      (f.resource_name ?? '').toLowerCase().includes(q) ||
      (f.resource_type ?? '').toLowerCase().includes(q)
    );
  }, [findings, debouncedSearch]);

  const severityCounts: Record<string, number> = {
    CRITICAL: stats?.by_severity?.CRITICAL ?? 0,
    HIGH: stats?.by_severity?.HIGH ?? 0,
    MEDIUM: stats?.by_severity?.MEDIUM ?? 0,
    LOW: stats?.by_severity?.LOW ?? 0,
    INFO: stats?.by_severity?.INFO ?? 0,
  };

  const statusCounts: Record<string, number> = {
    open: stats?.by_status?.open ?? 0,
    in_progress: stats?.by_status?.in_progress ?? 0,
    resolved: stats?.by_status?.resolved ?? 0,
    suppressed: stats?.by_status?.suppressed ?? 0,
    accepted_risk: stats?.by_status?.accepted_risk ?? 0,
  };

  const activeFilterCount = selectedSeverities.size + selectedStatuses.size;

  const toggleSeverity = (sev: string) => {
    setSelectedSeverities(prev => { const next = new Set(prev); if (next.has(sev)) next.delete(sev); else next.add(sev); return next; });
  };
  const toggleStatus = (status: string) => {
    setSelectedStatuses(prev => { const next = new Set(prev); if (next.has(status)) next.delete(status); else next.add(status); return next; });
  };
  const handleClearAll = () => { setSelectedSeverities(new Set()); setSelectedStatuses(new Set()); };

  const toggleRow = (id: string) => {
    setSelectedRows(prev => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  };
  const toggleAll = () => {
    if (selectedRows.size === filteredFindings.length) setSelectedRows(new Set());
    else setSelectedRows(new Set(filteredFindings.map(f => f.id)));
  };

  const handleStatusChange = async (findingId: string, newStatus: string) => {
    try {
      await updateFinding.mutateAsync({ id: findingId, data: { status: newStatus } });
      setSuccessMsg('Finding updated');
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch {}
  };

  const handleBulkUpdate = async (status: string) => {
    if (selectedRows.size === 0) return;
    const count = selectedRows.size;
    try {
      await bulkUpdate.mutateAsync({ ids: Array.from(selectedRows), status });
      setSelectedRows(new Set());
      setSuccessMsg(`${count} findings updated`);
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch {}
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const actionLoading = updateFinding.isPending ? updateFinding.variables?.id : bulkUpdate.isPending ? 'bulk' : null;

  const activeFilters: { label: string; clear: () => void }[] = [];
  Array.from(selectedSeverities).forEach(sev => activeFilters.push({ label: `Severity: ${sev}`, clear: () => toggleSeverity(sev) }));
  Array.from(selectedStatuses).forEach(status => {
    const statusLabel = STATUS_OPTIONS.find(s => s.value === status)?.label ?? status;
    activeFilters.push({ label: `Status: ${statusLabel}`, clear: () => toggleStatus(status) });
  });

  const bulkActionsEl = selectedRows.size > 0 ? (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium" style={{ color: 'var(--accent)' }}>{selectedRows.size} selected</span>
      <Button variant="normal" size="sm" onClick={() => handleBulkUpdate('suppressed')} disabled={actionLoading === 'bulk'}>Suppress</Button>
      <Button variant="normal" size="sm" onClick={() => handleBulkUpdate('resolved')} disabled={actionLoading === 'bulk'}>Resolve</Button>
      <Button variant="normal" size="sm" onClick={() => handleBulkUpdate('accepted_risk')} disabled={actionLoading === 'bulk'}>Accept risk</Button>
      {actionLoading === 'bulk' && <Loader2 className="h-4 w-4 animate-spin" style={{ color: 'var(--accent)' }} />}
      <button onClick={() => setSelectedRows(new Set())} style={{ color: 'var(--text-tertiary)' }}>
        <X className="h-4 w-4" />
      </button>
    </div>
  ) : undefined;

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Findings' }]}>
        {accountIds.length === 0 ? (
          <NoAccountsConnectedEmptyState />
        ) : !loading && total === 0 && activeFilterCount === 0 && !debouncedSearch ? (
          <NoScanDataEmptyState
            title="No findings for this account"
            description="No security findings found for the selected account. Run a scan to check for misconfigurations."
          />
        ) : (
          <>
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Findings</h1>
            <p className="mt-0.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
              {loading ? 'Loading...' : `${total.toLocaleString()} total · ${severityCounts.CRITICAL} critical`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="normal" size="sm" className="gap-1.5" onClick={() => refetch()} disabled={loading}>
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Refresh
            </Button>
            <Button variant="normal" size="sm" className="gap-1.5">
              <Download className="h-3.5 w-3.5" />
              Export
            </Button>
          </div>
        </div>

        <div className="mb-3 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[180px] max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: 'var(--text-tertiary)' }} />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search findings..."
              className="w-full pl-9 pr-3 py-2 text-sm focus:outline-none"
              style={{ borderRadius: 'var(--radius-input)', border: '1px solid var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            />
          </div>
          <button
            onClick={() => setShowFilterPanel(v => !v)}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors"
            style={{
              borderRadius: 'var(--radius-input)',
              border: `1px solid ${showFilterPanel ? 'var(--accent)' : 'var(--border-default)'}`,
              backgroundColor: showFilterPanel ? 'var(--accent-dim)' : 'var(--bg-surface)',
              color: showFilterPanel ? 'var(--accent)' : 'var(--text-secondary)',
            }}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Filters
            {activeFilterCount > 0 && (
              <span className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold text-white" style={{ backgroundColor: 'var(--accent)' }}>
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {showFilterPanel && (
          <div className="mb-3 rounded-lg border p-3" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
            <div className="mb-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Severity</span>
                {selectedSeverities.size > 0 && <button onClick={() => setSelectedSeverities(new Set())} className="text-xs" style={{ color: 'var(--accent)' }}>Clear</button>}
              </div>
              <div className="flex flex-wrap gap-2">
                {SEVERITY_OPTIONS.map(sev => {
                  const active = selectedSeverities.has(sev);
                  return (
                    <button key={sev} onClick={() => toggleSeverity(sev)}
                      className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium transition-all"
                      style={{ borderRadius: 'var(--radius-input)', border: `1px solid ${active ? 'var(--accent)' : 'var(--border-default)'}`, backgroundColor: active ? 'var(--accent)' : 'var(--bg-surface)', color: active ? 'white' : 'var(--text-secondary)' }}>
                      {sev}
                      <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold" style={{ backgroundColor: active ? 'rgba(255,255,255,0.2)' : 'var(--bg-elevated)', color: active ? 'white' : 'var(--text-tertiary)' }}>
                        {severityCounts[sev]}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Status</span>
                {selectedStatuses.size > 0 && <button onClick={() => setSelectedStatuses(new Set())} className="text-xs" style={{ color: 'var(--accent)' }}>Clear</button>}
              </div>
              <div className="flex flex-wrap gap-2">
                {STATUS_OPTIONS.map(st => {
                  const active = selectedStatuses.has(st.value);
                  return (
                    <button key={st.value} onClick={() => toggleStatus(st.value)}
                      className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium transition-all"
                      style={{ borderRadius: 'var(--radius-input)', border: `1px solid ${active ? 'var(--accent)' : 'var(--border-default)'}`, backgroundColor: active ? 'var(--accent)' : 'var(--bg-surface)', color: active ? 'white' : 'var(--text-secondary)' }}>
                      {st.label}
                      <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold" style={{ backgroundColor: active ? 'rgba(255,255,255,0.2)' : 'var(--bg-elevated)', color: active ? 'white' : 'var(--text-tertiary)' }}>
                        {statusCounts[st.value]}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {activeFilters.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Active filters:</span>
            {activeFilters.map((f, i) => <FilterChip key={i} label={f.label} onRemove={f.clear} />)}
            <button onClick={handleClearAll} className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Clear all</button>
          </div>
        )}

        {successMsg && (
          <div className="mb-3 flex items-center gap-2 rounded-lg border p-3 text-sm" style={{ borderColor: 'var(--success)', backgroundColor: 'var(--success-bg)', color: 'var(--success)' }}>
            <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
            {successMsg}
          </div>
        )}

        {error && (
          <div className="mb-3 flex items-center gap-2 rounded-lg border p-3 text-sm" style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}>
            {error}
          </div>
        )}

        <CvContainer header={{ title: 'Findings', counter: total > 0 ? `(${total.toLocaleString()})` : undefined, actions: bulkActionsEl }}>
          <div className="overflow-x-auto -mx-5 -mb-5">
            <table className="w-full">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}>
                  <th className="w-10 px-4 py-3">
                    <input type="checkbox" checked={selectedRows.size === filteredFindings.length && filteredFindings.length > 0} onChange={toggleAll} className="h-3.5 w-3.5 rounded" />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Severity</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Title</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Resource</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider hidden lg:table-cell" style={{ color: 'var(--text-secondary)' }}>Provider</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider hidden md:table-cell" style={{ color: 'var(--text-secondary)' }}>Age</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Status</th>
                  <th className="w-10 px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center">
                      <Loader2 className="mx-auto h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
                    </td>
                  </tr>
                ) : filteredFindings.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
                      {debouncedSearch ? `No findings matching "${debouncedSearch}"` : activeFilterCount > 0 ? 'No findings match the selected filters' : 'No findings found  your environment looks clean!'}
                    </td>
                  </tr>
                ) : (
                  filteredFindings.map(finding => (
                    <tr
                      key={finding.id}
                      onClick={() => setSelectedFindingId(finding.id)}
                      className="cursor-pointer border-b transition-colors"
                      style={{ borderColor: 'var(--border-faint)', backgroundColor: selectedRows.has(finding.id) ? 'var(--accent-dim)' : 'transparent' }}
                    >
                      <td className="px-4 py-3">
                        <input type="checkbox" checked={selectedRows.has(finding.id)} onChange={() => toggleRow(finding.id)} onClick={e => e.stopPropagation()} className="h-3.5 w-3.5 rounded" />
                      </td>
                      <td className="px-4 py-3">
                        <div className={`severity-border-${finding.severity.toLowerCase()} pl-3`}>
                          <SeverityBadge severity={finding.severity} />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="max-w-xs truncate text-sm" style={{ color: 'var(--text-primary)' }}>{finding.title}</div>
                        {finding.description && <div className="max-w-xs truncate text-xs" style={{ color: 'var(--text-tertiary)' }}>{finding.description}</div>}
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>{finding.resource_name || finding.resource_id}</div>
                        {finding.resource_type && <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{formatResourceType(finding.resource_type)}</div>}
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{finding.provider?.toUpperCase() ?? ''}</div>
                        {finding.account_id && <div className="font-mono text-xs" style={{ color: 'var(--text-tertiary)' }}>{finding.account_id}</div>}
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{timeAgo(finding.first_seen_at)}</span>
                      </td>
                      <td className="px-4 py-3">
                        {actionLoading === finding.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" style={{ color: 'var(--accent)' }} />
                        ) : (
                          <StatusBadge status={finding.status as any} size="sm" />
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <FindingActions finding={finding} onStatusChange={handleStatusChange} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between border-t pt-3 mt-3" style={{ borderColor: 'var(--border-faint)' }}>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              Showing {filteredFindings.length} of {total.toLocaleString()} findings
            </p>
            <div className="flex items-center gap-2">
              <Button variant="normal" size="sm" disabled={currentPage === 1 || loading} onClick={() => setOffset(o => Math.max(0, o - PAGE_SIZE))} className="h-7 px-2.5 text-xs">
                <ChevronLeft className="h-3 w-3" />
              </Button>
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Page {currentPage} of {Math.max(1, totalPages)}</span>
              <Button variant="normal" size="sm" disabled={currentPage >= totalPages || loading} onClick={() => setOffset(o => o + PAGE_SIZE)} className="h-7 px-2.5 text-xs">
                <ChevronRight className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </CvContainer>
          </>
        )}
      </AppLayout>
      <FindingDetailDrawer
        findingId={selectedFindingId}
        onClose={() => setSelectedFindingId(null)}
        onStatusChange={() => queryClient.invalidateQueries({ queryKey: ['findings'] })}
      />
    </ProtectedRoute>
  );
}
