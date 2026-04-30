'use client';

import * as React from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Info, Loader2, X } from 'lucide-react';

export interface FlashbarItem {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info' | 'in-progress';
  header: string;
  content?: string;
  action?: React.ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
  loading?: boolean;
}

interface FlashbarProps {
  items: FlashbarItem[];
}

// AWS Console notification bar style
const TYPE_CONFIG = {
  success:       { icon: CheckCircle2,  borderLeft: 'var(--success)',  bg: 'var(--success-bg)',  iconColor: 'var(--success)' },
  error:         { icon: XCircle,       borderLeft: 'var(--critical)', bg: 'var(--critical-bg)', iconColor: 'var(--critical)' },
  warning:       { icon: AlertTriangle, borderLeft: 'var(--warning)',  bg: 'var(--warning-bg)',  iconColor: 'var(--warning)' },
  info:          { icon: Info,          borderLeft: 'var(--info)',     bg: 'var(--info-bg)',     iconColor: 'var(--info)' },
  'in-progress': { icon: Loader2,       borderLeft: 'var(--info)',     bg: 'var(--info-bg)',     iconColor: 'var(--info)' },
};

function FlashItem({ item }: { item: FlashbarItem }) {
  const cfg = TYPE_CONFIG[item.type];
  const Icon = cfg.icon;
  const isLoading = item.type === 'in-progress' || item.loading;

  return (
    <div
      className="flex min-h-[44px] items-start gap-3 border px-4 py-3"
      style={{
        borderLeft: `4px solid ${cfg.borderLeft}`,
        borderTop: '1px solid var(--border-default)',
        borderRight: '1px solid var(--border-default)',
        borderBottom: '1px solid var(--border-default)',
        backgroundColor: cfg.bg,
        borderRadius: '2px',
      }}
    >
      <Icon
        className={`mt-0.5 h-4 w-4 flex-shrink-0 ${isLoading ? 'animate-spin' : ''}`}
        style={{ color: cfg.iconColor }}
        strokeWidth={1.75}
      />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
          {item.header}
        </div>
        {item.content && (
          <div className="mt-0.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
            {item.content}
          </div>
        )}
        {item.action && <div className="mt-2">{item.action}</div>}
      </div>
      {item.dismissible && item.onDismiss && (
        <button
          onClick={item.onDismiss}
          className="flex-shrink-0 rounded p-0.5 transition-colors"
          style={{ color: 'var(--text-secondary)' }}
          onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0.08)')}
          onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

export function Flashbar({ items }: FlashbarProps) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-col gap-2 w-full">
      {items.map(item => (
        <FlashItem key={item.id} item={item} />
      ))}
    </div>
  );
}
