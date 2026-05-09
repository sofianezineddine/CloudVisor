'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import {
  Play, Loader2, AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useCSPMScans, useTriggerScan,
} from '@/hooks/use-cspm';

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

export function ScanHistoryTab() {
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
