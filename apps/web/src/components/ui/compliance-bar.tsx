'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ComplianceBarProps {
  framework: string;
  percentage: number;
  total: number;
  passing: number;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showSubtext?: boolean;
  animated?: boolean;
}

// ─── ComplianceBar Component ──────────────────────────────────────────────────

export function ComplianceBar({
  framework,
  percentage,
  total,
  passing,
  className,
  size = 'md',
  showSubtext = true,
  animated = true,
}: ComplianceBarProps) {
  const [displayPercentage, setDisplayPercentage] = React.useState(animated ? 0 : percentage);

  // Animate percentage on mount
  React.useEffect(() => {
    if (!animated) return;

    const duration = 600;
    const steps = 30;
    const increment = percentage / steps;
    const stepDuration = duration / steps;

    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= percentage) {
        setDisplayPercentage(percentage);
        clearInterval(timer);
      } else {
        setDisplayPercentage(Math.floor(current));
      }
    }, stepDuration);

    return () => clearInterval(timer);
  }, [percentage, animated]);

  // Color based on percentage
  const getColor = () => {
    if (percentage >= 80) return 'success';
    if (percentage >= 60) return 'warning';
    return 'danger';
  };

  const color = getColor();

  const colorClasses = {
    success: 'bg-[hsl(var(--success))] text-[hsl(var(--success))]',
    warning: 'bg-[hsl(var(--warning))] text-[hsl(var(--warning))]',
    danger: 'bg-[hsl(var(--critical))] text-[hsl(var(--critical))]',
  };

  const sizeClasses = {
    sm: 'h-1',
    md: 'h-1.5',
    lg: 'h-2',
  };

  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  return (
    <div className={cn('space-y-1.5', className)}>
      {/* Label row */}
      <div className="flex items-center justify-between">
        <span className={cn(
          'font-medium text-[hsl(var(--text-primary))]',
          textSizeClasses[size]
        )}>
          {framework}
        </span>
        <span className={cn(
          'font-mono font-semibold',
          textSizeClasses[size],
          colorClasses[color]
        )}>
          {displayPercentage}%
        </span>
      </div>

      {/* Progress bar */}
      <div className={cn(
        'w-full rounded-full bg-[hsl(var(--border-default))] overflow-hidden',
        sizeClasses[size]
      )}>
        <div
          className={cn(
            'h-full rounded-full transition-all duration-300 ease-out',
            colorClasses[color]
          )}
          style={{ width: `${displayPercentage}%` }}
        />
      </div>

      {/* Subtext */}
      {showSubtext && (
        <p className="text-xs text-[hsl(var(--text-tertiary))]">
          {passing} of {total} controls passing
        </p>
      )}
    </div>
  );
}
