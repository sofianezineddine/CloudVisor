/**
 * StatusBadge — Cloudscape StatusIndicator pattern.
 *
 * Spec §3.2: "NEVER just a colored dot, never a bare label alone."
 * Every state indicator is an icon + label pair (StatusIndicator).
 *
 * Maps finding lifecycle statuses to the correct Cloudscape StatusIndicator type:
 *   open          → type="error"   (XCircle, red)
 *   in_progress   → type="warning" (AlertTriangle, amber)
 *   resolved      → type="success" (CheckCircle2, green)
 *   suppressed    → type="stopped" (MinusSquare, gray)
 *   accepted_risk → custom "accepted" (CheckCircle2, purple)
 */

import * as React from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  MinusSquare,
} from 'lucide-react';

type FindingStatus = 'open' | 'in_progress' | 'resolved' | 'suppressed' | 'accepted_risk';

interface StatusBadgeProps {
  status: FindingStatus;
  size?: 'sm' | 'md';
}

interface StatusConfig {
  label: string;
  icon: React.ReactNode;
  color: string;
}

function getStatusConfig(status: FindingStatus, iconSize: number): StatusConfig {
  switch (status) {
    case 'open':
      return {
        label: 'Open',
        icon: <XCircle size={iconSize} strokeWidth={2} />,
        color: 'var(--critical)',
      };
    case 'in_progress':
      return {
        label: 'In progress',
        icon: <AlertTriangle size={iconSize} strokeWidth={2} />,
        color: 'var(--medium)',
      };
    case 'resolved':
      return {
        label: 'Resolved',
        icon: <CheckCircle2 size={iconSize} strokeWidth={2} />,
        color: 'var(--success)',
      };
    case 'suppressed':
      return {
        label: 'Suppressed',
        icon: <MinusSquare size={iconSize} strokeWidth={2} />,
        color: 'var(--info)',
      };
    case 'accepted_risk':
      return {
        label: 'Accepted',
        icon: <CheckCircle2 size={iconSize} strokeWidth={2} />,
        color: '#7c3aed',
      };
    default:
      return {
        label: String(status),
        icon: <MinusSquare size={iconSize} strokeWidth={2} />,
        color: 'var(--text-tertiary)',
      };
  }
}

/**
 * StatusBadge renders a Cloudscape-style StatusIndicator: icon + label.
 * Never a bare colored dot. Never a label without an icon.
 */
export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const iconSize = size === 'sm' ? 12 : 14;
  const fontSize = size === 'sm' ? '11px' : '13px';
  const { label, icon, color } = getStatusConfig(status, iconSize);

  return (
    <span
      className="inline-flex items-center gap-1 font-medium"
      style={{
        color,
        fontSize,
        fontFamily: 'var(--font-sans)',
        whiteSpace: 'nowrap',
        lineHeight: 1.4,
      }}
      aria-label={`Status: ${label}`}
    >
      {icon}
      {label}
    </span>
  );
}
