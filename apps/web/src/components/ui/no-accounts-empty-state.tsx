'use client';

import Link from 'next/link';
import { PlugZap } from 'lucide-react';

/**
 * Shared empty state shown on every scope-aware page when zero accounts are connected.
 * Build once, reuse everywhere — never duplicate this message.
 */
export function NoAccountsConnectedEmptyState() {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 text-center px-4">
      <div
        className="flex h-16 w-16 items-center justify-center rounded-full"
        style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
      >
        <PlugZap className="h-8 w-8" style={{ color: 'var(--text-tertiary)' }} />
      </div>
      <div>
        <h2 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
          No cloud accounts connected
        </h2>
        <p className="text-sm max-w-sm" style={{ color: 'var(--text-secondary)' }}>
          Connect a cloud account to start seeing security findings, resources, and compliance data here.
        </p>
      </div>
      <Link
        href="/settings"
        className="inline-flex items-center gap-2 rounded px-4 py-2 text-sm font-semibold transition-colors"
        style={{
          backgroundColor: '#ec7211',
          color: '#ffffff',
          border: '1px solid #ec7211',
        }}
        onMouseEnter={e => ((e.currentTarget as HTMLElement).style.backgroundColor = '#d45b07')}
        onMouseLeave={e => ((e.currentTarget as HTMLElement).style.backgroundColor = '#ec7211')}
      >
        Connect your first account
      </Link>
    </div>
  );
}
