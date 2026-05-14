'use client';

import * as React from 'react';
import { AlertTriangle, X } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * ErrorBanner — displays an error message with an AlertTriangle icon.
 *
 * Supports an optional onDismiss callback to allow the user to close the banner.
 * Uses CSS variables for theming (dark mode compatible).
 */
export function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div
      className="flex items-center gap-3 rounded-lg border px-4 py-3"
      style={{
        borderColor: 'hsl(var(--critical))',
        backgroundColor: 'hsl(var(--critical-dim))',
        color: 'hsl(var(--critical))',
      }}
      role="alert"
    >
      <AlertTriangle className="h-5 w-5 flex-shrink-0" />
      <span className="flex-1 text-sm font-medium">{message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="flex-shrink-0 rounded p-1 transition-opacity hover:opacity-70"
          aria-label="Dismiss error"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
