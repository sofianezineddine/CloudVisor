'use client';

import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, AlertCircle, Loader2, AlertTriangle, RefreshCw } from 'lucide-react';
import { authAPI } from '@/lib/api/auth';
import { Button } from '@/components/ui/button';

interface AuditEntry {
  id: number;
  event_type: string;
  user_id: string | null;
  event_data: Record<string, unknown>;
  success: boolean;
  failure_reason: string | null;
  ip_address: string | null;
  timestamp: string;
}

/** Format an event_type slug into a human-readable label. */
function formatEventType(eventType: string): string {
  return eventType
    .replace(/^auth\./, '')
    .replace(/^team\./, '')
    .replace(/^org\./, 'Organization: ')
    .replace(/^api_key\./, 'API Key: ')
    .replace(/\./g, ' ')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

/** Relative time formatter. */
function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

export default function ActivityPage() {
  const [limit] = React.useState(50);
  const [offset, setOffset] = React.useState(0);

  React.useEffect(() => {
    document.title = 'Activity Log - Settings - CloudVisor';
  }, []);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['audit-log', limit, offset],
    queryFn: () => authAPI.getAuditLog({ limit, offset }),
    staleTime: 30_000,
  });

  const entries: AuditEntry[] = data?.entries ?? [];
  const total: number = data?.total ?? 0;

  return (
    <>
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Activity Log</h1>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Track logins, security changes, and account actions
        </p>
      </div>

      {/* Activity List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
        </div>
      ) : isError ? (
        <div className="flex items-center gap-2 rounded-lg border p-4 text-sm"
          style={{ borderColor: 'var(--warning)', backgroundColor: 'var(--warning-dim)', color: 'var(--text-primary)' }}>
          <AlertTriangle className="h-4 w-4 flex-shrink-0" style={{ color: 'var(--warning)' }} />
          Failed to load activity log. You may not have permission to view this.
        </div>
      ) : entries.length === 0 ? (
        <div className="cv-container p-8 text-center">
          <CheckCircle2 className="h-8 w-8 mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No activity recorded yet</p>
        </div>
      ) : (
        <>
          <div className="cv-container overflow-hidden">
            <div className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-center justify-between px-6 py-4 transition-colors"
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <div className="flex items-center gap-4">
                    <div
                      className="flex h-8 w-8 items-center justify-center rounded-full flex-shrink-0"
                      style={{
                        backgroundColor: entry.success ? 'var(--success-dim)' : 'var(--critical-dim)',
                      }}
                    >
                      {entry.success ? (
                        <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
                      ) : (
                        <AlertCircle className="h-4 w-4" style={{ color: 'var(--critical)' }} />
                      )}
                    </div>
                    <div>
                      <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                        {formatEventType(entry.event_type)}
                      </div>
                      <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                        <span>{relativeTime(entry.timestamp)}</span>
                        {entry.ip_address && (
                          <>
                            <span>·</span>
                            <span>IP: {entry.ip_address}</span>
                          </>
                        )}
                        {entry.failure_reason && (
                          <>
                            <span>·</span>
                            <span style={{ color: 'var(--critical)' }}>{entry.failure_reason.replace(/_/g, ' ')}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <span
                    className="rounded-full px-2 py-0.5 text-xs font-medium flex-shrink-0"
                    style={
                      entry.success
                        ? { backgroundColor: 'var(--success-dim)', color: 'var(--success)' }
                        : { backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }
                    }
                  >
                    {entry.success ? 'Success' : 'Failed'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Pagination */}
          {total > limit && (
            <div className="mt-4 flex items-center justify-between text-sm"
              style={{ color: 'var(--text-secondary)' }}>
              <span>
                Showing {offset + 1}–{Math.min(offset + limit, total)} of {total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= total}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}
