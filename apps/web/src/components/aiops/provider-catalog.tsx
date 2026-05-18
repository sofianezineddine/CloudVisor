'use client';

import * as React from 'react';
import { Plug, PlugZap, Circle } from 'lucide-react';
import type { AIOpsProvider } from '@/hooks/use-aiops-providers';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ProviderCatalogProps {
  providers: AIOpsProvider[];
  isLoading?: boolean;
  error?: string | null;
  onCardClick: (provider: AIOpsProvider) => void;
  className?: string;
}

// ─── Status Styles ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  connected: { color: 'var(--success)', bg: 'var(--success-bg, rgba(61, 184, 122, 0.12))', label: 'Connected' },
  disconnected: { color: 'var(--critical)', bg: 'var(--critical-bg)', label: 'Disconnected' },
  not_configured: { color: 'var(--text-tertiary)', bg: 'var(--bg-elevated)', label: 'Not Configured' },
};

// ─── Provider Icon ────────────────────────────────────────────────────────────

function ProviderIcon({ type, status }: { type: string; status: string }) {
  const Icon = status === 'connected' ? PlugZap : Plug;
  const color = STATUS_CONFIG[status]?.color ?? 'var(--text-tertiary)';

  return (
    <div
      className="flex items-center justify-center w-10 h-10 rounded-lg"
      style={{ backgroundColor: 'var(--bg-elevated)' }}
    >
      <Icon className="h-5 w-5" style={{ color }} />
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ProviderCatalog({
  providers,
  isLoading,
  error,
  onCardClick,
  className,
}: ProviderCatalogProps) {
  // Loading state
  if (isLoading) {
    return (
      <div className={className}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="animate-pulse rounded-lg p-4"
              style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)' }}
            >
              <div className="h-10 w-10 rounded-lg mb-3" style={{ backgroundColor: 'var(--bg-elevated)' }} />
              <div className="h-4 rounded w-2/3 mb-2" style={{ backgroundColor: 'var(--bg-elevated)' }} />
              <div className="h-3 rounded w-1/3" style={{ backgroundColor: 'var(--bg-elevated)' }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={className}>
        <div
          className="flex items-center justify-center rounded-lg border p-12"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border-default)' }}
        >
          <p className="text-sm" style={{ color: 'var(--critical)' }}>{error}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (providers.length === 0) {
    return (
      <div className={className}>
        <div
          className="flex flex-col items-center justify-center rounded-lg border p-12"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border-default)' }}
        >
          <Plug className="h-8 w-8 mb-3" style={{ color: 'var(--text-tertiary)' }} />
          <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            No providers configured
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
            Connect monitoring tools to start receiving alerts
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {providers.map((provider) => {
          const statusConfig = STATUS_CONFIG[provider.status] ?? STATUS_CONFIG.not_configured;

          return (
            <button
              key={provider.id}
              type="button"
              onClick={() => onCardClick(provider)}
              className="text-left rounded-lg p-4 transition-colors"
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-default)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent)';
                e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-default)';
                e.currentTarget.style.backgroundColor = 'var(--bg-surface)';
              }}
            >
              <div className="flex items-start gap-3">
                <ProviderIcon type={provider.type} status={provider.status} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                    {provider.name}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                    {provider.type}
                  </p>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-1.5">
                <Circle
                  className="h-2 w-2 fill-current"
                  style={{ color: statusConfig.color }}
                />
                <span className="text-xs" style={{ color: statusConfig.color }}>
                  {statusConfig.label}
                </span>
              </div>
              {provider.last_sync && (
                <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
                  Last sync: {new Date(provider.last_sync).toLocaleString()}
                </p>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
