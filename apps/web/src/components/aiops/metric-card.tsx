'use client';

import * as React from 'react';

interface AIOpsMetricCardProps {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
  color?: 'accent' | 'critical' | 'medium' | 'success' | 'info';
}

const COLOR_MAP: Record<string, string> = {
  accent: 'var(--accent)',
  critical: 'var(--critical)',
  medium: 'var(--medium)',
  success: 'var(--success)',
  info: 'var(--info)',
};

const DIM_MAP: Record<string, string> = {
  accent: 'var(--accent-dim)',
  critical: 'var(--critical-dim)',
  medium: 'var(--medium-dim)',
  success: 'var(--success-dim)',
  info: 'var(--info-dim)',
};

/**
 * AIOps metric card for the overview dashboard.
 * Displays a numeric count with label and icon, using CloudVisor design tokens.
 */
export function AIOpsMetricCard({ label, value, icon: Icon, color = 'accent' }: AIOpsMetricCardProps) {
  const mainColor = COLOR_MAP[color];
  const dimColor = DIM_MAP[color];

  return (
    <div className="cv-container p-4">
      <div className="mb-2 flex items-center justify-between">
        <div
          className="flex h-7 w-7 items-center justify-center rounded"
          style={{ backgroundColor: dimColor }}
        >
          <Icon className="h-4 w-4" style={{ color: mainColor }} />
        </div>
      </div>
      <div
        className="mb-0.5 text-2xl font-bold leading-none"
        style={{ color: mainColor, fontFamily: 'var(--font-mono)' }}
      >
        {value}
      </div>
      <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
        {label}
      </div>
    </div>
  );
}
