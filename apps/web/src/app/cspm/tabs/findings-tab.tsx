'use client';

import * as React from 'react';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { StatusBadge } from '@/components/ui/status-badge';
import { Button } from '@/components/ui/button';
import { CvContainer } from '@/components/ui/cv-container';
import { FindingDetailDrawer } from '@/components/ui/finding-detail-drawer';
import {
  Search, Download, ChevronLeft, ChevronRight,
  MoreHorizontal, RefreshCw, Loader2, X, CheckCircle2, SlidersHorizontal, Shield,
} from 'lucide-react';
import { Finding } from '@/lib/api/apiClient';
import { useCSPMFindings, useUpdateFindingStatus } from '@/hooks/use-cspm';
import { useQueryClient } from '@tanstack/react-query';
import { useScopeStore } from '@/stores/scope';
import { cn } from '@/lib/utils';

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
      style={{ borderColor: 'var(--btn-primary-bg)', backgroundColor: 'rgba(255,153,0,0.1)', color: 'var(--btn-primary-bg)' }}
    >
      {label}
      <button onClick={onRemove} className="ml-0.5 rounded-full p-0.5 transition-colors"
        onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,153,0,0.2)')}
        onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
        <X className="h-2.5 w-2.5" />
      </button>
    </span>
  );
}

function FindingActions({ finding, onStatusChange }: { finding: Finding; onStatusChange: (id: string, status: string) => void }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);
  const updateStatus = useUpdateFindingStatus();

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

  const handleAction = async (e: React.MouseEvent, status: string) => {
    e.stopPropagation();
    setOpen(false);
    try {
      await updateStatus.mutateAsync({ id: finding.id, status });
      onStatusChange(finding.id, status);
    } catch {}
  };

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
          className="absolute right-0 top-full z-50 mt-1 w-44 rounded-[var(--radius-container)] overflow-hidden"
          style={{ border: '1px solid var(--border-default)', backgroundColor: 'var(--bg-overlay)', boxShadow: 'var(--shadow-popover)' }}
        >
          {actions.map(a => (
            <button
              key={a.status}
              onClick={(e) => handleAction(e, a.status)}
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

export function FindingsTab() {
  const queryClient = useQueryClient();
  const [selectedSeverities, setSelectedSeverities] = React.useState<Set<string>>(new Set());
  const [selectedStatuses, setSelectedStatuses] = React.useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = React.useState('');
  const [debouncedSearch, setDebouncedSearch] = React.useState('');
  const [showFilterPanel, setShowFilterPanel] = React.useState(true);
  const [selectedRows, setSelectedRows] = React.useState<Set<string>>(new Set());
  const [offset, setOffset] = React.useState(0);
  const [selectedFindingId, setSelectedFindingId] = React.useState<string | null>(null);
  const [showDetailPanel, setShowDetailPanel] = React.useState(false);
  const [activeTab, setActiveTab] = React.useState('details');
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  React.useEffect(() => { setOffset(0); }, [selectedSeverities, selectedStatuses, debouncedSearch]);

  // Close detail panel with Escape key
  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showDetailPanel) {
        setShowDetailPanel(false);
        setSelectedFindingId(null);
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [showDetailPanel]);

  const queryParams = React.useMemo(() => {
    const params: Record<string, any> = { page_size: PAGE_SIZE, page: Math.floor(offset / PAGE_SIZE) + 1 };
    if (selectedSeverities.size > 0) params.severity = Array.from(selectedSeverities).join(',');
    if (selectedStatuses.size > 0) params.status = Array.from(selectedStatuses).join(',');
    return params;
  }, [selectedSeverities, selectedStatuses, offset]);

  const { data: findingsData, isLoading: loading, isError, error: queryError, refetch } = useCSPMFindings(queryParams);
  const updateFinding = useUpdateFindingStatus();

  const findings: Finding[] = (findingsData?.items as Finding[]) ?? [];
  const total: number = (findingsData as any)?.total ?? 0;
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

  const openFindings = findings.filter(f => f.status === 'open');
  const severityCounts: Record<string, number> = {
    CRITICAL: openFindings.filter(f => f.severity === 'CRITICAL').length,
    HIGH: openFindings.filter(f => f.severity === 'HIGH').length,
    MEDIUM: openFindings.filter(f => f.severity === 'MEDIUM').length,
    LOW: openFindings.filter(f => f.severity === 'LOW').length,
    INFO: openFindings.filter(f => f.severity === 'INFO').length,
  };

  const statusCounts: Record<string, number> = {
    open: findings.filter(f => f.status === 'open').length,
    in_progress: findings.filter(f => f.status === 'in_progress').length,
    resolved: findings.filter(f => f.status === 'resolved').length,
    suppressed: findings.filter(f => f.status === 'suppressed').length,
    accepted_risk: findings.filter(f => f.status === 'accepted_risk').length,
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
      await updateFinding.mutateAsync({ id: findingId, status: newStatus });
      setSuccessMsg('Finding updated');
      setTimeout(() => setSuccessMsg(null), 3000);
      refetch();
    } catch {}
  };

  const handleBulkUpdate = async (status: string) => {
    if (selectedRows.size === 0) return;
    const count = selectedRows.size;
    try {
      for (const id of selectedRows) {
        await updateFinding.mutateAsync({ id, status });
      }
      setSelectedRows(new Set());
      setSuccessMsg(`${count} findings updated`);
      setTimeout(() => setSuccessMsg(null), 3000);
      refetch();
    } catch {}
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const actionLoading = updateFinding.isPending ? updateFinding.variables?.id : null;

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
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Findings</h2>
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

      <div className="flex flex-wrap items-center gap-3">
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
            borderRadius: 'var(--radius-button)',
            border: `1px solid ${showFilterPanel ? 'var(--btn-primary-bg)' : 'var(--border-default)'}`,
            backgroundColor: showFilterPanel ? 'var(--btn-primary-bg)' : 'var(--bg-surface)',
            color: showFilterPanel ? 'white' : 'var(--text-secondary)',
          }}
        >
          <SlidersHorizontal className="h-3.5 w-3.5" />
          Filters
          {activeFilterCount > 0 && (
            <span className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold text-white" style={{ backgroundColor: showFilterPanel ? 'rgba(255,255,255,0.2)' : 'var(--btn-primary-bg)' }}>
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      {showFilterPanel && (
        <div className="rounded-[var(--radius-container)] border p-3" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <div className="mb-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Severity</span>
              {selectedSeverities.size > 0 && <button onClick={() => setSelectedSeverities(new Set())} className="text-xs" style={{ color: 'var(--btn-primary-bg)' }}>Clear</button>}
            </div>
            <div className="flex flex-wrap gap-2">
              {SEVERITY_OPTIONS.map(sev => {
                const active = selectedSeverities.has(sev);
                return (
                  <button key={sev} onClick={() => toggleSeverity(sev)}
                    className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium transition-all"
                    style={{ borderRadius: 'var(--radius-button)', border: `1px solid ${active ? 'var(--btn-primary-bg)' : 'var(--border-default)'}`, backgroundColor: active ? 'var(--btn-primary-bg)' : 'var(--bg-surface)', color: active ? 'white' : 'var(--text-secondary)' }}>
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
              {selectedStatuses.size > 0 && <button onClick={() => setSelectedStatuses(new Set())} className="text-xs" style={{ color: 'var(--btn-primary-bg)' }}>Clear</button>}
            </div>
            <div className="flex flex-wrap gap-2">
              {STATUS_OPTIONS.map(st => {
                const active = selectedStatuses.has(st.value);
                return (
                  <button key={st.value} onClick={() => toggleStatus(st.value)}
                    className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium transition-all"
                    style={{ borderRadius: 'var(--radius-button)', border: `1px solid ${active ? 'var(--btn-primary-bg)' : 'var(--border-default)'}`, backgroundColor: active ? 'var(--btn-primary-bg)' : 'var(--bg-surface)', color: active ? 'white' : 'var(--text-secondary)' }}>
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
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Active filters:</span>
          {activeFilters.map((f, i) => <FilterChip key={i} label={f.label} onRemove={f.clear} />)}
          <button onClick={handleClearAll} className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Clear all</button>
        </div>
      )}

      {successMsg && (
        <div className="flex items-center gap-2 rounded-lg border p-3 text-sm" style={{ borderColor: 'var(--success)', backgroundColor: 'var(--success-bg)', color: 'var(--success)' }}>
          <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
          {successMsg}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border p-3 text-sm" style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}>
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
                    onClick={() => {
                      setSelectedFindingId(finding.id);
                      setShowDetailPanel(true);
                      setActiveTab('details');
                    }}
                    className={cn(
                      "cursor-pointer border-b transition-colors",
                      selectedFindingId === finding.id ? "aws-console-selected" : "hover:bg-gray-50"
                    )}
                    style={{ 
                      borderColor: selectedFindingId === finding.id ? '#3b82f6' : 'var(--border-faint)'
                    }}
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

      {/* AWS Console Style Overlay Detail Panel */}
      {showDetailPanel && selectedFindingId && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4 aws-console-overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowDetailPanel(false);
              setSelectedFindingId(null);
            }
          }}
        >
          <div 
            className="w-full max-w-6xl rounded-lg shadow-2xl overflow-hidden aws-console-overlay-content"
            style={{ 
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-default)',
              maxHeight: '80vh'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header with finding title and close button */}
            <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)' }}>
              <div>
                <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Finding: {filteredFindings.find(f => f.id === selectedFindingId)?.title}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <SeverityBadge severity={filteredFindings.find(f => f.id === selectedFindingId)?.severity || 'INFO'} />
                  <StatusBadge status={filteredFindings.find(f => f.id === selectedFindingId)?.status as any} />
                  <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
                    ID: {selectedFindingId}
                  </span>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowDetailPanel(false);
                  setSelectedFindingId(null);
                }}
                className="p-2 rounded-md transition-colors"
                style={{ color: 'var(--text-tertiary)' }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = 'var(--text-tertiary)';
                }}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Tab Navigation */}
            <div className="border-b" style={{ borderColor: 'var(--border-faint)' }}>
              <nav className="flex px-6">
                {[
                  { id: 'details', label: 'Details' },
                  { id: 'resource', label: 'Resource' },
                  { id: 'remediation', label: 'Remediation' },
                  { id: 'compliance', label: 'Compliance' },
                  { id: 'timeline', label: 'Timeline' }
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "aws-console-tab px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                      activeTab === tab.id ? "active" : "border-transparent hover:border-gray-300"
                    )}
                    style={{
                      color: activeTab === tab.id ? '#2563eb' : 'var(--text-secondary)',
                      borderBottomColor: activeTab === tab.id ? '#3b82f6' : 'transparent'
                    }}
                  >
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>

            {/* Scrollable Tab Content */}
            <div className="overflow-y-auto p-6" style={{ maxHeight: 'calc(80vh - 140px)' }}>
              <FindingDetailContent 
                finding={filteredFindings.find(f => f.id === selectedFindingId)} 
                activeTab={activeTab}
              />
            </div>
          </div>
        </div>
      )}

      {/* Keep the original drawer for compatibility but hidden */}
      <div style={{ display: 'none' }}>
        <FindingDetailDrawer
          findingId={null}
          onClose={() => {}}
          onStatusChange={() => queryClient.invalidateQueries({ queryKey: ['findings'] })}
        />
      </div>
    </div>
  );
}

// AWS Console Style Detail Content Component
function FindingDetailContent({ finding, activeTab }: { finding?: Finding; activeTab: string }) {
  if (!finding) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
      </div>
    );
  }

  const renderDetailsTab = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div>
        <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Finding Information</h4>
        <div className="space-y-3">
          <div className="flex">
            <span className="w-32 text-sm" style={{ color: 'var(--text-tertiary)' }}>Finding ID</span>
            <span className="font-mono text-sm" style={{ color: 'var(--text-primary)' }}>{finding.id}</span>
          </div>
          <div className="flex">
            <span className="w-32 text-sm" style={{ color: 'var(--text-tertiary)' }}>Severity</span>
            <SeverityBadge severity={finding.severity} />
          </div>
          <div className="flex">
            <span className="w-32 text-sm" style={{ color: 'var(--text-tertiary)' }}>Status</span>
            <StatusBadge status={finding.status as any} />
          </div>
          <div className="flex">
            <span className="w-32 text-sm" style={{ color: 'var(--text-tertiary)' }}>First seen</span>
            <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{new Date(finding.first_seen_at).toLocaleString()}</span>
          </div>
          <div className="flex">
            <span className="w-32 text-sm" style={{ color: 'var(--text-tertiary)' }}>Last seen</span>
            <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{new Date(finding.last_seen_at).toLocaleString()}</span>
          </div>
        </div>
      </div>
      <div>
        <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Description</h4>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {finding.description || 'No description available.'}
        </p>
      </div>
    </div>
  );

  const renderResourceTab = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div>
        <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Resource Details</h4>
        <div className="space-y-3">
          <div className="flex">
            <span className="w-32 text-sm" style={{ color: 'var(--text-tertiary)' }}>Resource name</span>
            <span className="font-mono text-sm" style={{ color: 'var(--text-primary)' }}>{finding.resource_name || finding.resource_id}</span>
          </div>
          <div className="flex">
            <span className="w-32 text-sm" style={{ color: 'var(--text-tertiary)' }}>Resource type</span>
            <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{finding.resource_type}</span>
          </div>
          <div className="flex">
            <span className="w-32 text-sm" style={{ color: 'var(--text-tertiary)' }}>Provider</span>
            <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{finding.provider?.toUpperCase()}</span>
          </div>
          <div className="flex">
            <span className="w-32 text-sm" style={{ color: 'var(--text-tertiary)' }}>Account ID</span>
            <span className="font-mono text-sm" style={{ color: 'var(--text-primary)' }}>{finding.account_id}</span>
          </div>
          <div className="flex">
            <span className="w-32 text-sm" style={{ color: 'var(--text-tertiary)' }}>Region</span>
            <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{finding.region}</span>
          </div>
        </div>
      </div>
      <div>
        <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Resource Tags</h4>
        {finding.tags && Object.keys(finding.tags).length > 0 ? (
          <div className="space-y-2">
            {Object.entries(finding.tags).map(([key, value]) => (
              <div key={key} className="flex">
                <span className="w-32 text-sm font-mono" style={{ color: 'var(--text-tertiary)' }}>{key}</span>
                <span className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>{value}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>No tags available</p>
        )}
      </div>
    </div>
  );

  const renderRemediationTab = () => (
    <div>
      <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Remediation Steps</h4>
      {finding.remediation ? (
        <div className="prose prose-sm max-w-none">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <pre className="whitespace-pre-wrap text-sm" style={{ color: 'var(--text-primary)' }}>
              {finding.remediation}
            </pre>
          </div>
        </div>
      ) : (
        <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>No remediation steps available.</p>
      )}
    </div>
  );

  const renderComplianceTab = () => (
    <div>
      <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Compliance Mappings</h4>
      {finding.compliance_mapping && finding.compliance_mapping.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {finding.compliance_mapping.map((mapping, index) => (
            <div key={index} className="border rounded-lg p-4" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)' }}>
              <div className="flex items-center gap-2 mb-2">
                <Shield className="h-4 w-4" style={{ color: 'var(--accent)' }} />
                <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {typeof mapping === 'string' ? mapping : (mapping as any).framework}
                </span>
              </div>
              {typeof mapping !== 'string' && (mapping as any).control && (
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  Control: {(mapping as any).control}
                </p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>No compliance mappings available.</p>
      )}
    </div>
  );

  const renderTimelineTab = () => (
    <div>
      <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Finding Timeline</h4>
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <div className="w-2 h-2 rounded-full mt-2" style={{ backgroundColor: 'var(--success)' }}></div>
          <div>
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Finding detected</p>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{new Date(finding.first_seen_at).toLocaleString()}</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="w-2 h-2 rounded-full mt-2" style={{ backgroundColor: 'var(--accent)' }}></div>
          <div>
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Last observed</p>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{new Date(finding.last_seen_at).toLocaleString()}</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="w-2 h-2 rounded-full mt-2" style={{ 
            backgroundColor: finding.status === 'resolved' ? 'var(--success)' : 
                           finding.status === 'open' ? 'var(--critical)' : 'var(--medium)'
          }}></div>
          <div>
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Current status</p>
            <p className="text-xs capitalize" style={{ color: 'var(--text-tertiary)' }}>{finding.status.replace('_', ' ')}</p>
          </div>
        </div>
      </div>
    </div>
  );

  switch (activeTab) {
    case 'details': return renderDetailsTab();
    case 'resource': return renderResourceTab();
    case 'remediation': return renderRemediationTab();
    case 'compliance': return renderComplianceTab();
    case 'timeline': return renderTimelineTab();
    default: return renderDetailsTab();
  }
}