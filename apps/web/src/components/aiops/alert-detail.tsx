'use client';

import * as React from 'react';
import { DetailDrawer } from '@/components/ui/detail-drawer';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { useAIOpsAlert, useUpdateAlertStatus, type AIOpsAlert } from '@/hooks/use-aiops-alerts';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AlertDetailProps {
  alertId: string | null;
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
  firing: ['acknowledged', 'resolved'],
  acknowledged: ['resolved'],
  resolved: ['firing'],
  suppressed: ['firing', 'acknowledged'],
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

export function AlertDetail({ alertId, onClose }: AlertDetailProps) {
  const { data: alert, isLoading } = useAIOpsAlert(alertId);
  const updateStatus = useUpdateAlertStatus();
  const [statusChanging, setStatusChanging] = React.useState(false);

  const handleStatusChange = async (newStatus: string) => {
    if (!alertId) return;
    setStatusChanging(true);
    try {
      await updateStatus.mutateAsync({ id: alertId, status: newStatus });
    } finally {
      setStatusChanging(false);
    }
  };

  const availableTransitions = alert ? STATUS_TRANSITIONS[alert.status] ?? [] : [];

  return (
    <DetailDrawer
      isOpen={!!alertId}
      onClose={onClose}
      title={alert?.name ?? 'Alert Details'}
      subtitle={alert ? `${alert.source} • ${alert.fingerprint}` : undefined}
      width={640}
      actions={
        alert && availableTransitions.length > 0 ? (
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

      {alert && (
        <div className="space-y-6">
          {/* Core fields */}
          <div className="grid grid-cols-2 gap-4">
            <DetailField label="Severity">
              <SeverityBadge severity={SEVERITY_MAP[alert.severity] ?? 'INFO'} />
            </DetailField>
            <DetailField label="Status">
              <span
                className="inline-flex items-center text-xs font-medium"
                style={{
                  color: alert.status === 'firing' ? 'var(--critical)' :
                    alert.status === 'acknowledged' ? 'var(--medium)' :
                      alert.status === 'resolved' ? 'var(--success)' : 'var(--info)',
                }}
              >
                {alert.status.charAt(0).toUpperCase() + alert.status.slice(1)}
              </span>
            </DetailField>
            <DetailField label="Source">
              {alert.source || alert.provider_type || '—'}
            </DetailField>
            <DetailField label="Provider Type">
              {alert.provider_type || '—'}
            </DetailField>
            <DetailField label="Service">
              {alert.service || '—'}
            </DetailField>
            <DetailField label="Assignee">
              {alert.assignee || 'Unassigned'}
            </DetailField>
            <DetailField label="Created">
              {formatDateTime(alert.created_at)}
            </DetailField>
            <DetailField label="Last Received">
              {formatDateTime(alert.last_received)}
            </DetailField>
          </div>

          {/* Fingerprint */}
          <DetailField label="Fingerprint">
            <code
              className="text-xs px-2 py-1 rounded"
              style={{
                backgroundColor: 'var(--bg-elevated)',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {alert.fingerprint}
            </code>
          </DetailField>

          {/* Duplicate info */}
          {alert.is_duplicate && (
            <div
              className="rounded-md p-3"
              style={{
                backgroundColor: 'var(--medium-bg, rgba(232, 168, 56, 0.08))',
                border: '1px solid var(--medium-border, rgba(232, 168, 56, 0.2))',
              }}
            >
              <p className="text-xs font-medium" style={{ color: 'var(--medium)' }}>
                Duplicate Alert
              </p>
              {alert.duplicate_reason && (
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                  {alert.duplicate_reason}
                </p>
              )}
            </div>
          )}

          {/* Labels */}
          {alert.labels && Object.keys(alert.labels).length > 0 && (
            <div>
              <h3
                className="text-xs font-medium uppercase tracking-wider mb-3"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Labels
              </h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(alert.labels).map(([key, value]) => (
                  <span
                    key={key}
                    className="inline-flex items-center text-xs px-2 py-1 rounded-md"
                    style={{
                      backgroundColor: 'var(--bg-elevated)',
                      color: 'var(--text-secondary)',
                      border: '1px solid var(--border-default)',
                    }}
                  >
                    <span style={{ color: 'var(--text-tertiary)' }}>{key}:</span>
                    <span className="ml-1" style={{ color: 'var(--text-primary)' }}>{value}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Enrichments section */}
          <div
            className="pt-4"
            style={{ borderTop: '1px solid var(--border-default)' }}
          >
            <h3
              className="text-xs font-medium uppercase tracking-wider mb-3"
              style={{ color: 'var(--text-tertiary)' }}
            >
              Enrichments
            </h3>
            <EnrichmentsSection alertId={alert.id} fingerprint={alert.fingerprint} />
          </div>
        </div>
      )}
    </DetailDrawer>
  );
}

// ─── Enrichments Sub-component ────────────────────────────────────────────────

function EnrichmentsSection({ alertId, fingerprint }: { alertId: string; fingerprint: string }) {
  // Enrichments are fetched as part of the alert detail or via a separate endpoint
  // For now, we display a placeholder that will be populated when enrichment data is available
  // The enrichments are stored in ALERT_ENRICHMENT table linked by fingerprint

  return (
    <div
      className="rounded-md p-4"
      style={{
        backgroundColor: 'var(--bg-elevated)',
        border: '1px solid var(--border-faint, var(--border-default))',
      }}
    >
      <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
        Enrichment data from extraction and mapping rules will appear here when available.
      </p>
    </div>
  );
}
