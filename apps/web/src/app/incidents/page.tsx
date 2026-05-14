'use client';

import * as React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle, Loader2, RefreshCw, ChevronRight, X,
  Shield, Users, Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import apiClient, { type Incident } from '@/lib/api/apiClient';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  open:          { color: 'var(--critical)', bg: 'var(--critical-bg)', label: 'Open' },
  investigating: { color: 'var(--medium)',   bg: 'var(--medium-bg)',   label: 'Investigating' },
  resolved:      { color: 'var(--success)',  bg: 'var(--success-bg)',  label: 'Resolved' },
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? { color: 'var(--text-secondary)', bg: 'var(--bg-elevated)', label: status };
  return (
    <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold"
      style={{ backgroundColor: style.bg, color: style.color }}>
      {style.label}
    </span>
  );
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'var(--critical)',
  HIGH: 'var(--high)',
  MEDIUM: 'var(--medium)',
  LOW: 'var(--low)',
  INFO: 'var(--info)',
};

// ─── Incident detail drawer ───────────────────────────────────────────────────

function IncidentDetailDrawer({ incident, onClose }: { incident: Incident; onClose: () => void }) {
  const queryClient = useQueryClient();

  const updateMutation = useMutation({
    mutationFn: (status: string) => apiClient.incidents.update(incident.id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      toast.success('Incident updated');
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const validTransitions: Record<string, string[]> = {
    open: ['investigating', 'resolved'],
    investigating: ['resolved', 'open'],
    resolved: ['open'],
  };
  const nextStatuses = validTransitions[incident.status] ?? [];

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex flex-col shadow-2xl"
      style={{ width: 480, backgroundColor: 'var(--bg-surface)', borderLeft: '1px solid var(--border-default)' }}>
      <div className="flex items-center justify-between px-5 py-4 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border-default)' }}>
        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Incident Detail</h3>
        <button onClick={onClose} style={{ color: 'var(--text-tertiary)' }}>
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold" style={{ color: SEVERITY_COLORS[incident.severity] || 'var(--text-secondary)' }}>
              {incident.severity}
            </span>
            <StatusBadge status={incident.status} />
          </div>
          <h4 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            {incident.title}
          </h4>
          <p className="text-xs font-mono mt-1" style={{ color: 'var(--text-tertiary)' }}>{incident.id}</p>
        </div>

        {incident.description && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-tertiary)' }}>Description</p>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{incident.description}</p>
          </div>
        )}

        <div>
          <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--text-tertiary)' }}>
            Linked Findings ({incident.finding_ids?.length ?? 0})
          </p>
          {incident.finding_ids?.length > 0 ? (
            <div className="space-y-1">
              {incident.finding_ids.slice(0, 10).map((id: string) => (
                <div key={id} className="text-xs font-mono rounded px-2 py-1"
                  style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                  {id}
                </div>
              ))}
              {incident.finding_ids.length > 10 && (
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  +{incident.finding_ids.length - 10} more
                </p>
              )}
            </div>
          ) : (
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>No linked findings</p>
          )}
        </div>

        <div className="text-xs space-y-1" style={{ color: 'var(--text-tertiary)' }}>
          <div>Created: {new Date(incident.created_at).toLocaleString()}</div>
          <div>Updated: {new Date(incident.updated_at).toLocaleString()}</div>
          {incident.assignee_id && <div>Assignee: {incident.assignee_id}</div>}
        </div>

        {/* Status transitions */}
        {nextStatuses.length > 0 && (
          <div className="pt-2 border-t space-y-2" style={{ borderColor: 'var(--border-faint)' }}>
            {nextStatuses.map(status => (
              <Button key={status}
                variant={status === 'resolved' ? 'default' : 'outline'}
                size="sm" className="w-full gap-1.5 text-xs capitalize"
                onClick={() => updateMutation.mutate(status)}
                disabled={updateMutation.isPending}>
                {updateMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                Mark {status.replace('_', ' ')}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function IncidentsPage() {
  const [statusFilter, setStatusFilter] = React.useState('');
  const [severityFilter, setSeverityFilter] = React.useState('');
  const [selectedIncident, setSelectedIncident] = React.useState<Incident | null>(null);

  React.useEffect(() => {
    document.title = 'Incidents - CloudVisor';
  }, []);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['incidents', statusFilter, severityFilter],
    queryFn: () => apiClient.incidents.list({
      status: statusFilter || undefined,
      severity: severityFilter || undefined,
      limit: 100,
    }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const incidents: Incident[] = (data?.data as Incident[]) ?? [];

  const stats = React.useMemo(() => ({
    open: incidents.filter(i => i.status === 'open').length,
    investigating: incidents.filter(i => i.status === 'investigating').length,
    resolved: incidents.filter(i => i.status === 'resolved').length,
    critical: incidents.filter(i => i.severity === 'CRITICAL').length,
  }), [incidents]);

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Incidents' }]}>
        <div className="px-6 py-4">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Incidents</h1>
              <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching} className="gap-1.5">
                <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Security incidents — grouped findings requiring coordinated response
            </p>
          </div>

      {/* Stats */}
      {!isLoading && (
        <div className="grid grid-cols-2 gap-3 mb-6 sm:grid-cols-4">
          {[
            { label: 'Open', value: stats.open, color: 'var(--critical)' },
            { label: 'Investigating', value: stats.investigating, color: 'var(--medium)' },
            { label: 'Resolved', value: stats.resolved, color: 'var(--success)' },
            { label: 'Critical', value: stats.critical, color: 'var(--critical)' },
          ].map(({ label, value, color }) => (
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
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="rounded-md border px-3 py-2 text-sm focus:outline-none"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="investigating">Investigating</option>
          <option value="resolved">Resolved</option>
        </select>
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}
          className="rounded-md border px-3 py-2 text-sm focus:outline-none"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
          <option value="">All severities</option>
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(s => <option key={s}>{s}</option>)}
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
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Could not load incidents</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>Retry</Button>
        </div>
      ) : incidents.length === 0 ? (
        <div className="rounded-lg border p-12 flex flex-col items-center gap-3 text-center"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <Shield className="h-10 w-10" style={{ color: 'var(--success)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>No incidents</h3>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Incidents are automatically created when multiple related findings are detected.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <div className="px-4 py-3 border-b text-xs font-medium"
            style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
            {incidents.length} incident{incidents.length !== 1 ? 's' : ''}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}>
                  {['Severity', 'Title', 'Findings', 'Status', 'Created', ''].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium"
                      style={{ color: 'var(--text-secondary)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {incidents.map((incident) => (
                  <tr key={incident.id}
                    className="border-b cursor-pointer transition-colors"
                    style={{ borderColor: 'var(--border-faint)' }}
                    onClick={() => setSelectedIncident(incident)}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                    <td className="px-4 py-3">
                      <span className="text-xs font-semibold"
                        style={{ color: SEVERITY_COLORS[incident.severity] || 'var(--text-secondary)' }}>
                        {incident.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium truncate max-w-xs" style={{ color: 'var(--text-primary)' }}>
                        {incident.title}
                      </div>
                      {incident.description && (
                        <div className="text-xs truncate max-w-xs" style={{ color: 'var(--text-tertiary)' }}>
                          {incident.description}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono" style={{ color: 'var(--text-secondary)' }}>
                      {incident.finding_ids?.length ?? 0}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={incident.status} />
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {new Date(incident.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <ChevronRight className="h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detail drawer */}
      {selectedIncident && (
        <>
          <div className="fixed inset-0 z-40 bg-black/20" onClick={() => setSelectedIncident(null)} />
          <IncidentDetailDrawer incident={selectedIncident} onClose={() => setSelectedIncident(null)} />
        </>
      )}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
