'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { SeverityBadge } from './severity-badge';
import { StatusBadge } from './status-badge';
import { ChevronRight } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FindingCardProps {
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  title: string;
  description?: string;
  resourceName?: string;
  resourceType?: string;
  provider?: string;
  accountId?: string;
  age?: string;
  status?: 'open' | 'in_progress' | 'resolved' | 'suppressed' | 'accepted_risk';
  riskScore?: number;
  onClick?: () => void;
  actions?: React.ReactNode;
  className?: string;
}

// ─── FindingCard Component ────────────────────────────────────────────────────

export function FindingCard({
  severity,
  title,
  description,
  resourceName,
  resourceType,
  provider,
  accountId,
  age,
  status,
  riskScore,
  onClick,
  actions,
  className,
}: FindingCardProps) {
  const isClickable = !!onClick;

  return (
    <div
      onClick={onClick}
      className={cn(
        'group relative rounded-container border bg-[var(--bg-surface)] p-4 transition-colors',
        isClickable && 'cursor-pointer hover:border-[var(--accent)]',
        className
      )}
      style={{ border: '1px solid var(--border-default)' }}
    >
      {/* Header row */}
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <SeverityBadge severity={severity} />
          {status && <StatusBadge status={status} size="sm" />}
        </div>
        {riskScore !== undefined && (
          <div className="flex items-center gap-1">
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Risk:</span>
            <span
              className="font-mono text-sm font-semibold"
              style={{
                color:
                  riskScore >= 80 ? 'var(--critical)' :
                  riskScore >= 60 ? 'var(--high)' :
                  riskScore >= 40 ? 'var(--medium)' :
                  'var(--low)',
              }}
            >
              {riskScore}
            </span>
          </div>
        )}
      </div>

      {/* Title */}
      <h3 className="mb-1 text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
        {title}
        {isClickable && (
          <ChevronRight className="ml-1 inline h-4 w-4 opacity-0 transition-opacity group-hover:opacity-100" />
        )}
      </h3>

      {/* Description */}
      {description && (
        <p className="mb-3 text-sm line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
          {description}
        </p>
      )}

      {/* Metadata row */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
        {resourceName && (
          <div className="flex items-center gap-1">
            <span className="font-medium">Resource:</span>
            <span style={{ color: 'var(--text-secondary)' }}>{resourceName}</span>
          </div>
        )}
        {resourceType && (
          <div className="flex items-center gap-1">
            <span className="font-medium">Type:</span>
            <span style={{ color: 'var(--text-secondary)' }}>
              {resourceType.split('::').pop()?.replace(/_/g, ' ')}
            </span>
          </div>
        )}
        {provider && (
          <div className="flex items-center gap-1">
            <span className="font-medium">Provider:</span>
            <span className="uppercase" style={{ color: 'var(--text-secondary)' }}>{provider}</span>
          </div>
        )}
        {accountId && (
          <div className="flex items-center gap-1">
            <span className="font-medium">Account:</span>
            <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{accountId}</span>
          </div>
        )}
        {age && (
          <div className="flex items-center gap-1">
            <span className="font-medium">Discovered:</span>
            <span style={{ color: 'var(--text-secondary)' }}>{age}</span>
          </div>
        )}
      </div>

      {/* Actions */}
      {actions && (
        <div className="mt-3 flex items-center gap-2 border-t pt-3" style={{ borderColor: 'var(--border-faint)' }}>
          {actions}
        </div>
      )}
    </div>
  );
}
