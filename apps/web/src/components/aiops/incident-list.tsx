'use client';

import * as React from 'react';
import { DataTable, type Column } from '@/components/ui/data-table';
import { SeverityBadge } from '@/components/ui/severity-badge';
import type { AIOpsIncident } from '@/hooks/use-aiops-incidents';

// ─── Types ────────────────────────────────────────────────────────────────────

interface IncidentListProps {
  incidents: AIOpsIncident[];
  total: number;
  page: number;
  pageSize: number;
  isLoading?: boolean;
  error?: string | null;
  onPageChange: (page: number) => void;
  onRowClick: (incident: AIOpsIncident) => void;
  className?: string;
}

// ─── Severity Mapping ─────────────────────────────────────────────────────────

const SEVERITY_MAP: Record<string, 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'> = {
  critical: 'CRITICAL',
  high: 'HIGH',
  warning: 'MEDIUM',
  info: 'INFO',
  low: 'LOW',
};

// ─── Status Styles ────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  open: { color: 'var(--critical)', bg: 'var(--critical-bg)', label: 'Open' },
  acknowledged: { color: 'var(--medium)', bg: 'var(--medium-bg)', label: 'Acknowledged' },
  investigating: { color: 'var(--info)', bg: 'var(--info-bg)', label: 'Investigating' },
  resolved: { color: 'var(--success)', bg: 'var(--success-bg, rgba(61, 184, 122, 0.12))', label: 'Resolved' },
  closed: { color: 'var(--text-tertiary)', bg: 'var(--bg-elevated)', label: 'Closed' },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 30) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

function IncidentStatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? {
    color: 'var(--text-secondary)',
    bg: 'var(--bg-elevated)',
    label: status,
  };

  return (
    <span
      className="inline-flex items-center text-xs font-medium whitespace-nowrap"
      style={{
        color: style.color,
        backgroundColor: style.bg,
        padding: '2px 8px',
        borderRadius: '99px',
      }}
    >
      {style.label}
    </span>
  );
}

// ─── Columns ──────────────────────────────────────────────────────────────────

function getColumns(): Column<AIOpsIncident>[] {
  return [
    {
      key: 'severity',
      header: 'Severity',
      width: 'w-[100px]',
      render: (row) => (
        <SeverityBadge severity={SEVERITY_MAP[row.severity] ?? 'INFO'} size="sm" />
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: 'w-[130px]',
      render: (row) => <IncidentStatusBadge status={row.status} />,
    },
    {
      key: 'title',
      header: 'Title',
      render: (row) => (
        <span
          className="text-sm font-medium truncate max-w-[300px] block"
          style={{ color: 'var(--text-primary)' }}
        >
          {row.title}
        </span>
      ),
    },
    {
      key: 'alert_count',
      header: 'Alerts',
      width: 'w-[80px]',
      hideOnMobile: true,
      render: (row) => (
        <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          {row.alert_count}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      width: 'w-[120px]',
      hideOnMobile: true,
      render: (row) => (
        <span
          className="text-sm"
          style={{ color: 'var(--text-secondary)' }}
          title={new Date(row.created_at).toLocaleString()}
        >
          {formatRelativeTime(row.created_at)}
        </span>
      ),
    },
    {
      key: 'assignee',
      header: 'Assignee',
      width: 'w-[120px]',
      hideOnTablet: true,
      render: (row) => (
        <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          {row.assignee || '—'}
        </span>
      ),
    },
  ];
}

// ─── Component ────────────────────────────────────────────────────────────────

export function IncidentList({
  incidents,
  total,
  page,
  pageSize,
  isLoading,
  error,
  onPageChange,
  onRowClick,
  className,
}: IncidentListProps) {
  const columns = React.useMemo(() => getColumns(), []);

  return (
    <div className={className}>
      <DataTable<AIOpsIncident>
        data={incidents}
        columns={columns}
        isLoading={isLoading}
        error={error}
        onRowClick={onRowClick}
        getRowId={(row) => row.id}
        pagination={{
          total,
          pageSize,
          currentPage: page,
          onPageChange,
        }}
        emptyState={
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              No incidents found
            </p>
            <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
              Correlated alert groups will appear here as incidents
            </p>
          </div>
        }
      />
    </div>
  );
}
