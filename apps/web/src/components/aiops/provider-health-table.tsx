'use client';

import * as React from 'react';
import type { AIOpsProviderHealth } from '@/hooks/use-aiops-dashboard';

interface ProviderHealthTableProps {
  data: AIOpsProviderHealth[] | undefined;
  isLoading: boolean;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  connected: {
    label: 'Connected',
    color: 'var(--success)',
    bg: 'var(--success-bg)',
  },
  disconnected: {
    label: 'Disconnected',
    color: 'var(--text-tertiary)',
    bg: 'var(--bg-elevated)',
  },
  error: {
    label: 'Error',
    color: 'var(--critical)',
    bg: 'var(--critical-bg)',
  },
};

/**
 * Formats a date string as a relative time (e.g., "5 minutes ago").
 */
function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diffMs = now - date;

  if (isNaN(date)) return 'Unknown';

  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return 'Just now';

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`;

  const days = Math.floor(hours / 24);
  return `${days} day${days !== 1 ? 's' : ''} ago`;
}

/**
 * Provider health table for the AIOps overview dashboard.
 * Shows each connected provider's name, type, status badge, and last sync time.
 */
export function ProviderHealthTable({ data, isLoading }: ProviderHealthTableProps) {
  if (isLoading) {
    return (
      <div className="cv-container p-4">
        <div className="mb-3">
          <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
            Provider Health
          </h3>
        </div>
        <div
          className="flex items-center justify-center"
          style={{ height: 120 }}
        >
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Loading provider data…
          </span>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="cv-container p-4">
        <div className="mb-3">
          <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
            Provider Health
          </h3>
        </div>
        <div
          className="flex items-center justify-center rounded border"
          style={{
            height: 120,
            borderColor: 'var(--border-default)',
            backgroundColor: 'var(--bg-elevated)',
          }}
        >
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            No providers configured
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="cv-container p-4">
      <div className="mb-3">
        <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
          Provider Health
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr
              style={{
                backgroundColor: 'var(--bg-elevated)',
                borderBottom: '1px solid var(--border-default)',
              }}
            >
              <th
                className="px-3 py-2 text-xs font-semibold uppercase"
                style={{ color: 'var(--text-secondary)' }}
              >
                Name
              </th>
              <th
                className="px-3 py-2 text-xs font-semibold uppercase"
                style={{ color: 'var(--text-secondary)' }}
              >
                Type
              </th>
              <th
                className="px-3 py-2 text-xs font-semibold uppercase"
                style={{ color: 'var(--text-secondary)' }}
              >
                Status
              </th>
              <th
                className="px-3 py-2 text-xs font-semibold uppercase"
                style={{ color: 'var(--text-secondary)' }}
              >
                Last Sync
              </th>
            </tr>
          </thead>
          <tbody>
            {data.map((provider) => {
              const statusCfg = STATUS_CONFIG[provider.status] ?? STATUS_CONFIG.disconnected;
              return (
                <tr
                  key={provider.id}
                  className="transition-colors"
                  style={{ borderBottom: '1px solid var(--border-faint)' }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                  }}
                >
                  <td
                    className="px-3 py-2 text-sm font-medium"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    {provider.name}
                  </td>
                  <td
                    className="px-3 py-2 text-sm"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    {provider.type}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                      style={{
                        color: statusCfg.color,
                        backgroundColor: statusCfg.bg,
                      }}
                    >
                      {statusCfg.label}
                    </span>
                  </td>
                  <td
                    className="px-3 py-2 text-sm"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    {formatRelativeTime(provider.last_sync)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
