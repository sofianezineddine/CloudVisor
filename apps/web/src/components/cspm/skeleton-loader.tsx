'use client';

import * as React from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SkeletonLoaderProps {
  variant: 'cards' | 'table' | 'timeline' | 'editor' | 'graph';
  rows?: number;
  columns?: number;
}

// ─── Skeleton Block ───────────────────────────────────────────────────────────

function SkeletonBlock({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`animate-pulse rounded ${className ?? ''}`}
      style={{ backgroundColor: 'var(--bg-elevated, hsl(var(--bg-elevated)))', ...style }}
    />
  );
}

// ─── Variant Renderers ────────────────────────────────────────────────────────

function CardsSkeleton({ rows = 1, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: rows }, (_, rowIdx) => (
        <div key={rowIdx} className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
          {Array.from({ length: columns }, (_, colIdx) => (
            <div
              key={colIdx}
              className="rounded-lg border p-4 space-y-3"
              style={{ borderColor: 'hsl(var(--border-faint))' }}
            >
              <SkeletonBlock className="h-4 w-2/3" />
              <SkeletonBlock className="h-8 w-1/2" />
              <SkeletonBlock className="h-3 w-full" />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function TableSkeleton({ rows = 5, columns = 5 }: { rows?: number; columns?: number }) {
  return (
    <div className="w-full space-y-2">
      {/* Header */}
      <div className="flex gap-4 pb-2" style={{ borderBottom: '1px solid hsl(var(--border-faint))' }}>
        {Array.from({ length: columns }, (_, i) => (
          <SkeletonBlock key={i} className="h-4 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }, (_, rowIdx) => (
        <div key={rowIdx} className="flex gap-4 py-3" style={{ borderBottom: '1px solid hsl(var(--border-faint))' }}>
          {Array.from({ length: columns }, (_, colIdx) => (
            <SkeletonBlock
              key={colIdx}
              className="h-4 flex-1"
              // Vary widths for visual interest
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function TimelineSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-4 pl-4" style={{ borderLeft: '2px solid hsl(var(--border-faint))' }}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="relative pl-6 space-y-2">
          {/* Timeline dot */}
          <div
            className="absolute -left-[9px] top-1 h-4 w-4 rounded-full animate-pulse"
            style={{ backgroundColor: 'var(--bg-elevated, hsl(var(--bg-elevated)))' }}
          />
          <SkeletonBlock className="h-4 w-1/3" />
          <SkeletonBlock className="h-3 w-2/3" />
          <SkeletonBlock className="h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}

function EditorSkeleton({ rows = 12 }: { rows?: number }) {
  return (
    <div
      className="rounded-lg border p-4 space-y-2"
      style={{ borderColor: 'hsl(var(--border-default))' }}
    >
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex gap-3">
          {/* Line number */}
          <SkeletonBlock className="h-4 w-6 flex-shrink-0" />
          {/* Code line — varying widths */}
          <SkeletonBlock
            className="h-4"
            style={{ width: `${30 + Math.random() * 50}%` } as React.CSSProperties}
          />
        </div>
      ))}
    </div>
  );
}

function GraphSkeleton() {
  return (
    <div
      className="rounded-lg border flex items-center justify-center"
      style={{
        borderColor: 'hsl(var(--border-default))',
        height: '300px',
      }}
    >
      <div className="space-y-4 flex flex-col items-center">
        {/* Simulated graph nodes */}
        <SkeletonBlock className="h-12 w-32" />
        <div className="flex gap-8">
          <SkeletonBlock className="h-12 w-28" />
          <SkeletonBlock className="h-12 w-28" />
        </div>
        <div className="flex gap-12">
          <SkeletonBlock className="h-12 w-24" />
          <SkeletonBlock className="h-12 w-24" />
          <SkeletonBlock className="h-12 w-24" />
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

/**
 * SkeletonLoader — reusable loading skeleton patterns for CSPM tabs.
 *
 * Variants:
 * - cards: Grid of card placeholders
 * - table: Table rows with header
 * - timeline: Vertical timeline with dots
 * - editor: Code editor with line numbers
 * - graph: Graph visualization placeholder
 *
 * Uses animate-pulse with var(--bg-elevated) background.
 */
export function SkeletonLoader({ variant, rows, columns }: SkeletonLoaderProps) {
  switch (variant) {
    case 'cards':
      return <CardsSkeleton rows={rows} columns={columns} />;
    case 'table':
      return <TableSkeleton rows={rows} columns={columns} />;
    case 'timeline':
      return <TimelineSkeleton rows={rows} />;
    case 'editor':
      return <EditorSkeleton rows={rows} />;
    case 'graph':
      return <GraphSkeleton />;
    default:
      return <TableSkeleton rows={rows} columns={columns} />;
  }
}
