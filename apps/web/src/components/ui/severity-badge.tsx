import * as React from 'react';

interface SeverityBadgeProps {
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  size?: 'sm' | 'md';
  dot?: boolean;
  className?: string;
}

// AWS Console severity colors
const SEVERITY_STYLES: Record<string, { color: string; bg: string; border: string; label: string }> = {
  CRITICAL: { color: 'var(--critical)', bg: 'var(--critical-bg)', border: 'var(--critical-border)', label: 'Critical' },
  HIGH:     { color: 'var(--high)',     bg: 'var(--high-bg)',     border: 'var(--high-border)',     label: 'High' },
  MEDIUM:   { color: 'var(--medium)',   bg: 'var(--medium-bg)',   border: 'var(--medium-border)',   label: 'Medium' },
  LOW:      { color: 'var(--low)',      bg: 'var(--low-bg)',      border: 'var(--low-border)',      label: 'Low' },
  INFO:     { color: 'var(--info)',     bg: 'var(--info-bg)',     border: 'var(--info-border)',     label: 'Info' },
};

export function SeverityBadge({ severity, size = 'md', dot = false, className }: SeverityBadgeProps) {
  const s = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.INFO;
  const fontSize = size === 'sm' ? '11px' : '12px';
  const padding = size === 'sm' ? '1px 5px' : '2px 6px';

  return (
    <span
      className={`inline-flex items-center gap-1 font-semibold ${className ?? ''}`}
      style={{
        borderRadius: '2px',
        color: s.color,
        backgroundColor: s.bg,
        border: `1px solid ${s.border}`,
        padding,
        fontSize,
        fontFamily: 'var(--font-sans)',
        whiteSpace: 'nowrap',
      }}
    >
      {dot && (
        <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: s.color }} />
      )}
      {s.label}
    </span>
  );
}
