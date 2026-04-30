'use client';

import * as React from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  width?: 480 | 640 | 800;
  children: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

// ─── DetailDrawer Component ───────────────────────────────────────────────────

export function DetailDrawer({
  isOpen,
  onClose,
  title,
  subtitle,
  width = 640,
  children,
  actions,
  className,
}: DetailDrawerProps) {
  const drawerRef = React.useRef<HTMLDivElement>(null);

  // Close on Escape key
  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Focus trap
  React.useEffect(() => {
    if (!isOpen) return;

    const drawer = drawerRef.current;
    if (!drawer) return;

    const focusableElements = drawer.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    drawer.addEventListener('keydown', handleTab as any);
    firstElement?.focus();

    return () => {
      drawer.removeEventListener('keydown', handleTab as any);
    };
  }, [isOpen]);

  // Prevent body scroll when open
  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        ref={drawerRef}
        className={cn(
          'fixed right-0 top-0 z-50 h-full bg-[hsl(var(--bg-surface))] shadow-2xl transition-transform duration-200 ease-out flex flex-col',
          isOpen ? 'translate-x-0' : 'translate-x-full',
          width === 480 && 'w-[480px] max-w-[90vw]',
          width === 640 && 'w-[640px] max-w-[90vw]',
          width === 800 && 'w-[800px] max-w-[90vw]',
          className
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-[hsl(var(--border-default))] px-6 py-4">
          <div className="flex-1 min-w-0">
            <h2
              id="drawer-title"
              className="text-lg font-semibold text-[hsl(var(--text-primary))] truncate"
            >
              {title}
            </h2>
            {subtitle && (
              <p className="mt-1 text-sm text-[hsl(var(--text-secondary))] truncate">
                {subtitle}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-4 rounded-md p-1.5 text-[hsl(var(--text-tertiary))] hover:bg-[hsl(var(--bg-elevated))] hover:text-[hsl(var(--text-primary))] transition-colors"
            aria-label="Close drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {children}
        </div>

        {/* Footer (actions) */}
        {actions && (
          <div className="border-t border-[hsl(var(--border-default))] px-6 py-4">
            {actions}
          </div>
        )}
      </div>
    </>
  );
}
