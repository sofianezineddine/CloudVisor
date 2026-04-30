'use client';

import { Toaster as SonnerToaster } from 'sonner';

export function Toaster() {
  return (
    <SonnerToaster
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast: 'bg-[hsl(var(--bg-overlay))] border border-[hsl(var(--border-strong))] text-[hsl(var(--text-primary))] shadow-lg',
          title: 'text-sm font-medium',
          description: 'text-xs text-[hsl(var(--text-secondary))]',
          actionButton: 'bg-[hsl(var(--accent))] text-white',
          cancelButton: 'bg-[hsl(var(--bg-elevated))] text-[hsl(var(--text-secondary))]',
          closeButton: 'bg-[hsl(var(--bg-elevated))] border-[hsl(var(--border-default))] text-[hsl(var(--text-tertiary))] hover:text-[hsl(var(--text-primary))]',
          success: 'border-l-4 border-l-[hsl(var(--success))] bg-[hsl(var(--success-dim))]',
          error: 'border-l-4 border-l-[hsl(var(--critical))] bg-[hsl(var(--critical-dim))]',
          warning: 'border-l-4 border-l-[hsl(var(--warning))] bg-[hsl(var(--warning-dim))]',
          info: 'border-l-4 border-l-[hsl(var(--accent))] bg-[hsl(var(--accent-dim))]',
        },
        duration: 4000,
      }}
      closeButton
      richColors
    />
  );
}
