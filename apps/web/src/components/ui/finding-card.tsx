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

  // Severity-specific styles
  const severityStyles = {
    CRITICAL: {
      border: 'border-l-[hsl(var(--critical))]',
      bg: 'bg-[hsl(var(--critical-bg))]',
    },
    HIGH: {
      border: 'border-l-[hsl(var(--high))]',
      bg: 'bg-[hsl(var(--high-bg))]',
    },
    MEDIUM: {
      border: 'border-l-[hsl(var(--medium))]',
      bg: 'bg-[hsl(var(--medium-bg))]',
    },
    LOW: {
      border: 'border-l-[hsl(var(--low))]',
      bg: 'bg-[hsl(var(--low-bg))]',
    },
    INFO: {
      border: 'border-l-[hsl(var(--info))]',
      bg: 'bg-[hsl(var(--info-bg))]',
    },
  };

  const styles = severityStyles[severity];

  return (
    <div
      onClick={onClick}
      className={cn(
        'group relative rounded-lg border-l-4 bg-[hsl(var(--bg-surface))] p-4 transition-all',
        styles.border,
        styles.bg,
        isClickable && 'cursor-pointer hover:shadow-md hover:scale-[1.01]',
        className
      )}
    >
      {/* Header row */}
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <SeverityBadge severity={severity} />
          {status && <StatusBadge status={status} size="sm" />}
        </div>
        {riskScore !== undefined && (
          <div className="flex items-center gap-1">
            <span className="text-xs text-[hsl(var(--text-tertiary))]">Risk:</span>
            <span className={cn(
              'font-mono text-sm font-semibold',
              riskScore >= 80 && 'text-[hsl(var(--critical))]',
              riskScore >= 60 && riskScore < 80 && 'text-[hsl(var(--high))]',
              riskScore >= 40 && riskScore < 60 && 'text-[hsl(var(--medium))]',
              riskScore < 40 && 'text-[hsl(var(--low))]'
            )}>
              {riskScore}
            </span>
          </div>
        )}
      </div>

      {/* Title */}
      <h3 className="mb-1 text-base font-semibold text-[hsl(var(--text-primary))] group-hover:text-[hsl(var(--accent))]">
        {title}
        {isClickable && (
          <ChevronRight className="ml-1 inline h-4 w-4 opacity-0 transition-opacity group-hover:opacity-100" />
        )}
      </h3>

      {/* Description */}
      {description && (
        <p className="mb-3 text-sm text-[hsl(var(--text-secondary))] line-clamp-2">
          {description}
        </p>
      )}

      {/* Metadata row */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[hsl(var(--text-tertiary))]">
        {resourceName && (
          <div className="flex items-center gap-1">
            <span className="font-medium">Resource:</span>
            <span className="text-[hsl(var(--text-secondary))]">{resourceName}</span>
          </div>
        )}
        {resourceType && (
          <div className="flex items-center gap-1">
            <span className="font-medium">Type:</span>
            <span className="text-[hsl(var(--text-secondary))]">
              {resourceType.split('::').pop()?.replace(/_/g, ' ')}
            </span>
          </div>
        )}
        {provider && (
          <div className="flex items-center gap-1">
            <span className="font-medium">Provider:</span>
            <span className="text-[hsl(var(--text-secondary))] uppercase">{provider}</span>
          </div>
        )}
        {accountId && (
          <div className="flex items-center gap-1">
            <span className="font-medium">Account:</span>
            <span className="font-mono text-[hsl(var(--text-secondary))]">{accountId}</span>
          </div>
        )}
        {age && (
          <div className="flex items-center gap-1">
            <span className="font-medium">Discovered:</span>
            <span className="text-[hsl(var(--text-secondary))]">{age}</span>
          </div>
        )}
      </div>

      {/* Actions */}
      {actions && (
        <div className="mt-3 flex items-center gap-2 border-t border-[hsl(var(--border-faint))] pt-3">
          {actions}
        </div>
      )}
    </div>
  );
}
