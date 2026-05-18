'use client';

import * as React from 'react';
import { DetailDrawer } from '@/components/ui/detail-drawer';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import {
  useAIOpsIncident,
  useUpdateIncidentStatus,
  type AIOpsIncidentDetail as IncidentDetailType,
} from '@/hooks/use-aiops-incidents';

// ─── Types ────────────────────────────────────────────────────────────────────

interface IncidentDetailProps {
  incidentId: string | null;
  onClose: () => void;
}

// ─── Severity Mapping ─────────────────────────────────────────────────────────

const SEVERITY_MAP: Record<string, 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'> = {
  critical: 'CRITICAL',
  high: 'HIGH',
  warning: 'MEDIUM',
  info: 'INFO',
  low: 'LOW',
};

// ─── Status Transitions ───────────────────────────────────────────────────────

const STATUS_TRANSITIONS: Record<string, string[]> = {
  open: ['acknowledged', 'investigating'],
  acknowledged: ['investigating', 'resolved'],
  investigating: ['resolved'],
  resolved: ['closed'],
  closed: [],
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

function DetailField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
        {label}
      </span>
      <span className="text-sm" style={{ color: 'var(--text-primary)' }}>
        {children}
      </span>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function IncidentDetail({ incidentId, onClose }: IncidentDetailProps) {
  const { data: incident, isLoading } = useAIOpsIncident(incidentId);
  const updateStatus = useUpdateIncidentStatus();
  const [statusChanging, setStatusChanging] = React.useState(false);

  const handleStatusChange = async (newStatus: string) => {
    if (!incidentId) return;
    setStatusChanging(true);
    try {
      await updateStatus.mutateAsync({ id: incidentId, status: newStatus });
    } finally {
      setStatusChanging(false);
    }
  };

  const availableTransitions = incident ? STATUS_TRANSITIONS[incident.status] ?? [] : [];

  return (
    <DetailDrawer
      isOpen={!!incidentId}
      onClose={onClose}
      title={incident?.title ?? 'Incident Details'}
      subtitle={incident ? `${incident.status} • ${incident.alert_count} alerts` : undefined}
      width={640}
      actions={
        incident && availableTransitions.length > 0 ? (
          <div className="flex items-center gap-2">
            <span className="text-xs mr-2" style={{ color: 'var(--text-tertiary)' }}>
              Change status:
            </span>
            {availableTransitions.map((status) => (
              <Button
                key={status}
                variant={status === 'resolved' ? 'primary' : 'outline'}
                size="sm"
                disabled={statusChanging}
                onClick={() => handleStatusChange(status)}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </Button>
            ))}
          </div>
        ) : undefined
      }
    >
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-pulse space-y-4 w-full">
            <div className="h-4 rounded w-3/4" style={{ backgroundColor: 'var(--bg-elevated)' }} />
            <div className="h-4 rounded w-1/2" style={{ backgroundColor: 'var(--bg-elevated)' }} />
            <div className="h-4 rounded w-2/3" style={{ backgroundColor: 'var(--bg-elevated)' }} />
          </div>
        </div>
      )}

      {incident && (
        <div className="space-y-6">
          {/* Core fields */}
          <div className="grid grid-cols-2 gap-4">
            <DetailField label="Severity">
              <SeverityBadge severity={SEVERITY_MAP[incident.severity] ?? 'INFO'} />
            </DetailField>
            <DetailField label="Status">
              <span
                className="inline-flex items-center text-xs font-medium capitalize"
                style={{
                  color:
                    incident.status === 'open' ? 'var(--critical)' :
                    incident.status === 'acknowledged' ? 'var(--medium)' :
                    incident.status === 'investigating' ? 'var(--info)' :
                    incident.status === 'resolved' ? 'var(--success)' :
                    'var(--text-tertiary)',
                }}
              >
                {incident.status}
              </span>
            </DetailField>
            <DetailField label="Alert Count">
              {incident.alert_count}
            </DetailField>
            <DetailField label="Assignee">
              {incident.assignee || 'Unassigned'}
            </DetailField>
            <DetailField label="Created">
              {formatDateTime(incident.created_at)}
            </DetailField>
            <DetailField label="Updated">
              {formatDateTime(incident.updated_at)}
            </DetailField>
          </div>

          {/* AI Summary */}
          {incident.ai_summary && (
            <div>
              <h3
                className="text-xs font-medium uppercase tracking-wider mb-2"
                style={{ color: 'var(--text-tertiary)' }}
              >
                AI Summary
              </h3>
              <div
                className="rounded-md p-3 text-sm"
                style={{
                  backgroundColor: 'var(--bg-elevated)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-default)',
                }}
              >
                {incident.ai_summary}
              </div>
            </div>
          )}

          {/* Associated Alerts */}
          {incident.alerts && incident.alerts.length > 0 && (
            <div>
              <h3
                className="text-xs font-medium uppercase tracking-wider mb-3"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Associated Alerts ({incident.alerts.length})
              </h3>
              <div className="space-y-2">
                {incident.alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="flex items-center gap-3 rounded-md p-2"
                    style={{
                      backgroundColor: 'var(--bg-elevated)',
                      border: '1px solid var(--border-default)',
                    }}
                  >
                    <SeverityBadge severity={SEVERITY_MAP[alert.severity] ?? 'INFO'} size="sm" />
                    <span className="text-sm flex-1 truncate" style={{ color: 'var(--text-primary)' }}>
                      {alert.name}
                    </span>
                    <span className="text-xs capitalize" style={{ color: 'var(--text-tertiary)' }}>
                      {alert.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timeline */}
          {incident.timeline && incident.timeline.length > 0 && (
            <div
              className="pt-4"
              style={{ borderTop: '1px solid var(--border-default)' }}
            >
              <h3
                className="text-xs font-medium uppercase tracking-wider mb-3"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Timeline
              </h3>
              <div className="space-y-3">
                {incident.timeline.map((event, idx) => (
                  <div key={idx} className="flex gap-3">
                    <div
                      className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                      style={{ backgroundColor: 'var(--accent)' }}
                    />
                    <div className="flex-1">
                      <p className="text-sm" style={{ color: 'var(--text-primary)' }}>
                        {event.description}
                      </p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
                        {formatDateTime(event.timestamp)}
                        {event.user_id && ` • ${event.user_id}`}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </DetailDrawer>
  );
}
