'use client';

import * as React from 'react';
import {
  CheckCircle2, XCircle, AlertTriangle, Info,
  Loader2, Clock, MinusSquare,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type StatusType = 'success' | 'error' | 'warning' | 'info' | 'loading' | 'pending' | 'stopped';

interface StatusIndicatorProps {
  type: StatusType;
  label: string;
  size?: 'sm' | 'md';
  className?: string;
}

const CONFIG: Record<StatusType, { icon: React.ElementType; color: string }> = {
  success: { icon: CheckCircle2,  color: 'var(--success)' },
  error:   { icon: XCircle,       color: 'var(--danger)' },
  warning: { icon: AlertTriangle, color: 'var(--warning)' },
  info:    { icon: Info,          color: 'var(--accent)' },
  loading: { icon: Loader2,       color: 'var(--accent)' },
  pending: { icon: Clock,         color: 'var(--text-secondary)' },
  stopped: { icon: MinusSquare,   color: 'var(--text-secondary)' },
};

export function StatusIndicator({ type, label, size = 'md', className }: StatusIndicatorProps) {
  const { icon: Icon, color } = CONFIG[type];
  const iconSize = size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4';
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm';
  const isColored = type === 'error' || type === 'warning';

  return (
    <span
      className={cn('inline-flex items-center gap-1', className)}
      style={{ gap: '4px' }}
    >
      <Icon
        className={cn(iconSize, type === 'loading' && 'animate-spin')}
        style={{ color, flexShrink: 0 }}
        strokeWidth={1.75}
      />
      <span
        className={textSize}
        style={{ color: isColored ? color : 'var(--text-primary)' }}
      >
        {label}
      </span>
    </span>
  );
}
