'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { Shield, AlertTriangle, Clock, ArrowRight, RefreshCw, Loader2, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import apiClient, { Incident } from '@/lib/api/apiClient';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ─── MITRE ATT&CK tactics ─────────────────────────────────────────────────────

const MITRE_TACTICS = [
  'Initial Access', 'Execution', 'Persistence', 'Privilege Escalation',
  'Defense Evasion', 'Credential Access', 'Discovery', 'Lateral Movement',
  'Collection', 'Exfiltration', 'Impact',
];

// ─── Status badge ─────────────────────────────────────────────────────────────

function IncidentStatusBadge({ status }: { status: string }) {
  const styleMap: Record<string, React.CSSProperties> = {
    open: { backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' },
    investigating: { backgroundColor: 'var(--medium-dim)', color: 'var(--medium)' },
    in_progress: { backgroundColor: 'var(--medium-dim)', color: 'var(--medium)' },
    resolved: { backgroundColor: 'var(--success-dim)', color: 'var(--success)' },
    closed: { backgroundColor: 'var(--info-dim)', color: 'var(--info)' },
  };
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
      style={styleMap[status] ?? { backgroundColor: 'var(--bg-elevated)', color: 'var(--text-tertiary)' }}
    >
      {status.replace('_', ' ')}
    </span>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function IncidentsPage() {
  const [incidents, setIncidents] = React.useState<Incident[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [statusFilter, setStatusFilter] = React.useState('');
  const [severityFilter, setSeverityFilter] = React.useState('');

  React.useEffect(() => {
    document.title = 'Incidents - CloudVisor';
  }, []);

  const fetchIncidents = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { limit: 50 };
      if (statusFilter) params.status = statusFilter;
      if (severityFilter) params.severity = severityFilter;
      const resp = await apiClient.incidents.list(params);
      setIncidents((resp?.data as Incident[]) ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load incidents');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, severityFilter]);

  React.useEffect(() => { fetchIncidents(); }, [fetchIncidents]);

  const handleStatusChange = async (incidentId: string, newStatus: string) => {
    try {
      await apiClient.incidents.update(incidentId, { status: newStatus });
      await fetchIncidents();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update incident');
    }
  };

  const criticalCount = incidents.filter(i => i.severity === 'CRITICAL').length;
  const openCount = incidents.filter(i => i.status === 'open').length;

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Incidents' }]}>
        {/* Page Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Security Incidents</h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {loading ? 'Loading…' : `${incidents.length} incidents · ${criticalCount} critical · ${openCount} open`}
            </p>
          </div>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={fetchIncidents} disabled={loading}>
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Refresh
          </Button>
        </div>

        {/* Error banner */}
        {error && (
          <div
            className="mb-4 flex items-center gap-2 rounded-lg border p-3 text-sm"
            style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}
          >
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="rounded-md border px-3 py-2 text-sm focus:outline-none"
            style={{
              borderColor: 'var(--border-default)',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
            }}
          >
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
          <select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value)}
            className="rounded-md border px-3 py-2 text-sm focus:outline-none"
            style={{
              borderColor: 'var(--border-default)',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
            }}
          >
            <option value="">All severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        {/* Incident Cards */}
        {loading ? (
          <div className="flex h-48 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
          </div>
        ) : incidents.length === 0 ? (
          <div className="cv-container flex flex-col items-center justify-center p-12 text-center">
            <Shield className="mb-3 h-12 w-12" style={{ color: 'var(--success)' }} />
            <h3 className="mb-1 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>No incidents found</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {statusFilter || severityFilter
                ? 'No incidents match the current filters.'
                : 'No security incidents have been detected yet.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {incidents.map(incident => (
              <div
                key={incident.id}
                className={cn(
                  'cv-container p-5 transition-colors',
                  `severity-border-${incident.severity.toLowerCase()}`
                )}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={incident.severity as any} />
                      <IncidentStatusBadge status={incident.status} />
                    </div>
                    <h3 className="mb-1 text-base font-medium" style={{ color: 'var(--text-primary)' }}>
                      {incident.title}
                    </h3>
                    {incident.description && (
                      <p className="mb-2 text-sm line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                        {incident.description}
                      </p>
                    )}
                    <div className="flex flex-wrap items-center gap-4 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {incident.finding_ids?.length > 0 && (
                        <span className="flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          {incident.finding_ids.length} finding{incident.finding_ids.length !== 1 ? 's' : ''}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {timeAgo(incident.created_at)}
                      </span>
                      {incident.assignee_id && (
                        <span>Assigned</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {incident.status === 'open' && (
                      <Button
                        variant="outline" size="sm"
                        className="text-xs h-7 px-2"
                        onClick={() => handleStatusChange(incident.id, 'investigating')}
                      >
                        Investigate
                      </Button>
                    )}
                    {incident.status === 'investigating' && (
                      <Button
                        variant="outline" size="sm"
                        className="text-xs h-7 px-2"
                        onClick={() => handleStatusChange(incident.id, 'resolved')}
                      >
                        Resolve
                      </Button>
                    )}
                    <ArrowRight className="h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* MITRE ATT&CK Tactics Grid */}
        <div className="mt-8 cv-container p-6">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            MITRE ATT&CK Tactics Coverage
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {MITRE_TACTICS.map(tactic => (
              <div
                key={tactic}
                className="rounded-md border p-3 text-center text-xs"
                style={{ borderColor: 'var(--border-default)', color: 'var(--text-tertiary)' }}
              >
                <Shield className="mx-auto mb-1.5 h-5 w-5" strokeWidth={1.5} />
                {tactic}
              </div>
            ))}
          </div>
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
