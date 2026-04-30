'use client';

import { ScanSearch, Play, Loader2 } from 'lucide-react';
import { useTriggerScan } from '@/hooks/use-cspm';
import { useScopeStore } from '@/stores/scope';

/**
 * Empty state shown on scope-aware pages when the selected account has no scan
 * data yet. Prompts the user to run their first scan.
 *
 * Usage: render this when a query returns empty data AND accountIds.length > 0
 * (i.e. an account IS selected, but it has no data yet).
 */
export function NoScanDataEmptyState({
  title = 'No data for this account',
  description,
}: {
  title?: string;
  description?: string;
}) {
  const triggerScan = useTriggerScan();
  const label = useScopeStore(s => s.label);
  const mode = useScopeStore(s => s.mode);

  const defaultDescription =
    mode === 'account'
      ? `No scan data found for ${label}. Run a scan to discover resources and security findings.`
      : `No scan data found for ${label} accounts. Run a scan to discover resources and security findings.`;

  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 text-center px-4">
      <div
        className="flex h-16 w-16 items-center justify-center rounded-full"
        style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
      >
        <ScanSearch className="h-8 w-8" style={{ color: 'var(--text-tertiary)' }} />
      </div>
      <div>
        <h2 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
          {title}
        </h2>
        <p className="text-sm max-w-sm" style={{ color: 'var(--text-secondary)' }}>
          {description ?? defaultDescription}
        </p>
      </div>
      <button
        onClick={() => triggerScan.mutate({})}
        disabled={triggerScan.isPending}
        className="inline-flex items-center gap-2 rounded px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-60"
        style={{
          backgroundColor: '#ec7211',
          color: '#ffffff',
          border: '1px solid #ec7211',
          cursor: triggerScan.isPending ? 'not-allowed' : 'pointer',
        }}
        onMouseEnter={e => {
          if (!triggerScan.isPending)
            (e.currentTarget as HTMLElement).style.backgroundColor = '#d45b07';
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLElement).style.backgroundColor = '#ec7211';
        }}
      >
        {triggerScan.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        {triggerScan.isPending ? 'Starting scan…' : 'Run scan now'}
      </button>
      {triggerScan.isSuccess && (
        <p className="text-xs" style={{ color: 'var(--success)' }}>
          Scan started — results will appear here shortly.
        </p>
      )}
      {triggerScan.isError && (
        <p className="text-xs" style={{ color: 'var(--critical)' }}>
          Failed to start scan. Please try again.
        </p>
      )}
    </div>
  );
}
