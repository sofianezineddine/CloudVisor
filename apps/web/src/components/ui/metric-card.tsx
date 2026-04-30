import * as React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: React.ComponentType<{ className?: string }>;
  color?: 'accent' | 'critical' | 'high' | 'medium' | 'success' | 'info';
  trend?: { value: number; direction: 'up' | 'down'; isPositive?: boolean };
  onClick?: () => void;
  className?: string;
}

const COLOR_MAP: Record<string, string> = {
  accent:   'var(--accent)',
  critical: 'var(--critical)',
  high:     'var(--high)',
  medium:   'var(--medium)',
  success:  'var(--success)',
  info:     'var(--info)',
};

const DIM_MAP: Record<string, string> = {
  accent:   'var(--accent-dim)',
  critical: 'var(--critical-dim)',
  high:     'var(--high-dim)',
  medium:   'var(--medium-dim)',
  success:  'var(--success-dim)',
  info:     'var(--info-dim)',
};

export function MetricCard({ label, value, icon: Icon, color = 'accent', trend, onClick, className }: MetricCardProps) {
  const mainColor = COLOR_MAP[color];
  const dimColor = DIM_MAP[color];

  return (
    <div
      onClick={onClick}
      className={`cv-container p-4 ${onClick ? 'cursor-pointer' : ''} ${className ?? ''}`}
      onMouseEnter={onClick ? (e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--accent)'; } : undefined}
      onMouseLeave={onClick ? (e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-default)'; } : undefined}
    >
      <div className="mb-2 flex items-center justify-between">
        {Icon && (
          <div
            className="flex h-7 w-7 items-center justify-center rounded"
            style={{ backgroundColor: dimColor }}
          >
            <Icon className="h-4 w-4" />
          </div>
        )}
        {trend && (
          <div className="flex items-center gap-1 text-xs" style={{ color: trend.isPositive ? 'var(--success)' : 'var(--critical)' }}>
            <span>{trend.direction === 'down' ? '↓' : '↑'} {trend.value}</span>
          </div>
        )}
      </div>
      <div className="mb-0.5 text-2xl font-bold leading-none" style={{ color: mainColor, fontFamily: 'var(--font-mono)' }}>
        {value}
      </div>
      <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
        {label}
      </div>
    </div>
  );
}
