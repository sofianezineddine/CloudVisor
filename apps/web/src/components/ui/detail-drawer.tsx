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
      // Store original overflow values
      const originalBodyOverflow = document.body.style.overflow;
      const originalHtmlOverflow = document.documentElement.style.overflow;
      
      // Prevent scrolling
      document.body.style.overflow = 'hidden';
      document.documentElement.style.overflow = 'hidden';
      
      return () => {
        // Restore original overflow values
        document.body.style.overflow = originalBodyOverflow;
        document.documentElement.style.overflow = originalHtmlOverflow;
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 z-[60] transition-all duration-300 ease-out',
          isOpen ? 'opacity-100' : 'opacity-0'
        )}
        style={{
          backgroundColor: 'rgba(0, 0, 0, 0.6)'
        }}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        ref={drawerRef}
        className={cn(
          'fixed right-0 top-0 z-[70] h-full flex flex-col',
          'transition-transform duration-300 ease-out',
          isOpen ? 'translate-x-0' : 'translate-x-full',
          width === 480 && 'w-[480px] max-w-[90vw]',
          width === 640 && 'w-[640px] max-w-[90vw]',
          width === 800 && 'w-[800px] max-w-[90vw]',
          className
        )}
        style={{
          backgroundColor: 'var(--bg-surface)',
          boxShadow: '0 4px 24px rgba(0, 0, 0, 0.25)',
          border: '1px solid var(--border-default)'
        }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        {/* Header */}
        <div 
          className="flex items-start justify-between px-6 py-4"
          style={{ 
            borderBottom: '1px solid var(--border-default)'
          }}
        >
          <div className="flex-1 min-w-0">
            <h2
              id="drawer-title"
              className="text-lg font-semibold truncate"
              style={{ color: 'var(--text-primary)' }}
            >
              {title}
            </h2>
            {subtitle && (
              <p 
                className="mt-1 text-sm truncate"
                style={{ color: 'var(--text-secondary)' }}
              >
                {subtitle}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-4 rounded-md p-1.5 transition-colors"
            style={{ 
              color: 'var(--text-tertiary)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
              e.currentTarget.style.color = 'var(--text-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.color = 'var(--text-tertiary)';
            }}
            aria-label="Close drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div 
          className="flex-1 overflow-y-auto px-6 py-6"
          style={{
            backgroundColor: 'var(--bg-surface)'
          }}
        >
          {children}
        </div>

        {/* Footer (actions) */}
        {actions && (
          <div 
            className="px-6 py-4"
            style={{ 
              borderTop: '1px solid var(--border-default)'
            }}
          >
            {actions}
          </div>
        )}
      </div>
    </>
  );
}
