'use client';

import * as React from 'react';

interface ContainerHeader {
  title: string;
  counter?: string;
  description?: string;
  actions?: React.ReactNode;
}

interface ContainerProps {
  header?: ContainerHeader;
  footer?: React.ReactNode;
  variant?: 'default' | 'stacked' | 'embedded';
  children: React.ReactNode;
  className?: string;
}

// AWS Console-style container — flat, 1px border, 2px radius, no shadow
export function CvContainer({ header, footer, variant = 'default', children, className }: ContainerProps) {
  const isEmbedded = variant === 'embedded';

  return (
    <div
      className={`cv-container ${isEmbedded ? 'border-0 !rounded-none' : ''} ${className ?? ''}`}
    >
      {header && (
        <div
          className="flex items-center justify-between border-b px-4"
          style={{ minHeight: '44px', borderColor: 'var(--border-faint)', paddingTop: '10px', paddingBottom: '10px' }}
        >
          <div className="min-w-0">
            <div className="flex items-baseline gap-2">
              <h2 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                {header.title}
              </h2>
              {header.counter && (
                <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  {header.counter}
                </span>
              )}
            </div>
            {header.description && (
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                {header.description}
              </p>
            )}
          </div>
          {header.actions && (
            <div className="ml-4 flex flex-shrink-0 items-center gap-2">
              {header.actions}
            </div>
          )}
        </div>
      )}

      <div className="p-4">{children}</div>

      {footer && (
        <div className="border-t px-4 py-3" style={{ borderColor: 'var(--border-faint)' }}>
          <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            {footer}
          </div>
        </div>
      )}
    </div>
  );
}
