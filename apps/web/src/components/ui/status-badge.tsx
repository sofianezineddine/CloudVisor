import * as React from 'react';

interface StatusBadgeProps {
  status: 'open' | 'in_progress' | 'resolved' | 'suppressed' | 'accepted_risk';
  size?: 'sm' | 'md';
}

const STATUS_MAP: Record<string, { label: string; color: string; bg: string; border: string }> = {
  open:          { label: 'Open',        color: 'var(--critical)', bg: 'var(--critical-bg)', border: 'var(--critical-border)' },
  in_progress:   { label: 'In progress', color: 'var(--medium)',   bg: 'var(--medium-bg)',   border: 'var(--medium-border)' },
  resolved:      { label: 'Resolved',    color: 'var(--success)',  bg: 'var(--success-bg)',  border: 'var(--low-border)' },
  suppressed:    { label: 'Suppressed',  color: 'var(--info)',     bg: 'var(--info-bg)',     border: 'var(--info-border)' },
  accepted_risk: { label: 'Accepted',    color: '#6b2fa0',         bg: 'rgba(107,47,160,0.08)', border: 'rgba(107,47,160,0.25)' },
};

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const s = STATUS_MAP[status] ?? STATUS_MAP.open;
  return (
    <span
      className="inline-flex items-center gap-1 font-semibold"
      style={{
        borderRadius: '2px',
        color: s.color,
        backgroundColor: s.bg,
        border: `1px solid ${s.border}`,
        padding: size === 'sm' ? '1px 5px' : '2px 6px',
        fontSize: size === 'sm' ? '11px' : '12px',
        fontFamily: 'var(--font-sans)',
        whiteSpace: 'nowrap',
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: s.color }} />
      {s.label}
    </span>
  );
}
