'use client';

import * as React from 'react';
import { ChevronLeft, ChevronRight, Loader2, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './button';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Column<T> {
  key: string;
  header: string;
  width?: string;
  className?: string;
  hideOnMobile?: boolean;
  hideOnTablet?: boolean;
  render?: (row: T) => React.ReactNode;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  isLoading?: boolean;
  error?: string | null;
  emptyState?: React.ReactNode;
  onRowClick?: (row: T) => void;
  selectable?: boolean;
  selectedRows?: Set<string>;
  onSelectionChange?: (selected: Set<string>) => void;
  getRowId?: (row: T) => string;
  pagination?: {
    total: number;
    pageSize: number;
    currentPage: number;
    onPageChange: (page: number) => void;
  };
  className?: string;
  rowClassName?: (row: T) => string;
}

// ─── Skeleton Loader ──────────────────────────────────────────────────────────

function SkeletonRow({ columns }: { columns: Column<any>[] }) {
  return (
    <tr className="animate-pulse">
      {columns.map((col, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-[hsl(var(--bg-elevated))] rounded w-3/4" />
        </td>
      ))}
    </tr>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function DefaultEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="mb-3 rounded-full bg-[hsl(var(--bg-elevated))] p-3">
        <AlertTriangle className="h-6 w-6 text-[hsl(var(--text-tertiary))]" />
      </div>
      <p className="text-sm font-medium text-[hsl(var(--text-primary))]">No data found</p>
      <p className="text-xs text-[hsl(var(--text-tertiary))] mt-1">
        Try adjusting your filters or search query
      </p>
    </div>
  );
}

// ─── Error State ──────────────────────────────────────────────────────────────

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="mb-3 rounded-full bg-[hsl(var(--critical-dim))] p-3">
        <AlertTriangle className="h-6 w-6 text-[hsl(var(--critical))]" />
      </div>
      <p className="text-sm font-medium text-[hsl(var(--text-primary))]">Failed to load data</p>
      <p className="text-xs text-[hsl(var(--text-tertiary))] mt-1 max-w-md">
        {message}
      </p>
    </div>
  );
}

// ─── DataTable Component ──────────────────────────────────────────────────────

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  isLoading = false,
  error = null,
  emptyState,
  onRowClick,
  selectable = false,
  selectedRows = new Set(),
  onSelectionChange,
  getRowId = (row) => row.id,
  pagination,
  className,
  rowClassName,
}: DataTableProps<T>) {
  // Select all toggle
  const toggleAll = () => {
    if (!onSelectionChange) return;
    if (selectedRows.size === data.length && data.length > 0) {
      onSelectionChange(new Set());
    } else {
      onSelectionChange(new Set(data.map(getRowId)));
    }
  };

  // Toggle single row
  const toggleRow = (id: string) => {
    if (!onSelectionChange) return;
    const next = new Set(selectedRows);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    onSelectionChange(next);
  };

  // Visible columns (filter out hidden on current breakpoint)
  const visibleColumns = columns;

  return (
    <div className={cn('card overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[hsl(var(--border-faint))] bg-[hsl(var(--bg-elevated))]">
              {selectable && (
                <th className="w-10 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedRows.size === data.length && data.length > 0}
                    onChange={toggleAll}
                    disabled={isLoading || data.length === 0}
                    className="h-3.5 w-3.5 rounded border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))] text-[hsl(var(--accent))] focus:ring-[hsl(var(--accent))] disabled:opacity-50"
                  />
                </th>
              )}
              {visibleColumns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[hsl(var(--text-secondary))]',
                    col.width,
                    col.hideOnMobile && 'hidden sm:table-cell',
                    col.hideOnTablet && 'hidden lg:table-cell',
                    col.className
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[hsl(var(--border-faint))]">
            {/* Loading State */}
            {isLoading && (
              <>
                {[...Array(8)].map((_, i) => (
                  <SkeletonRow key={i} columns={(selectable ? [{ key: 'checkbox', header: '' } as Column<T>, ...visibleColumns] : visibleColumns)} />
                ))}
              </>
            )}

            {/* Error State */}
            {!isLoading && error && (
              <tr>
                <td colSpan={visibleColumns.length + (selectable ? 1 : 0)} className="p-0">
                  <ErrorState message={error} />
                </td>
              </tr>
            )}

            {/* Empty State */}
            {!isLoading && !error && data.length === 0 && (
              <tr>
                <td colSpan={visibleColumns.length + (selectable ? 1 : 0)} className="p-0">
                  {emptyState || <DefaultEmptyState />}
                </td>
              </tr>
            )}

            {/* Data Rows */}
            {!isLoading && !error && data.length > 0 && data.map((row) => {
              const rowId = getRowId(row);
              const isSelected = selectedRows.has(rowId);
              const isClickable = !!onRowClick;

              return (
                <tr
                  key={rowId}
                  onClick={() => onRowClick?.(row)}
                  className={cn(
                    'transition-colors',
                    isSelected && 'bg-[hsl(var(--accent-dim))] border-l-2 border-l-[hsl(var(--accent))]',
                    !isSelected && 'hover:bg-[hsl(var(--bg-elevated))]',
                    isClickable && 'cursor-pointer',
                    rowClassName?.(row)
                  )}
                >
                  {selectable && (
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleRow(rowId)}
                        className="h-3.5 w-3.5 rounded border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))] text-[hsl(var(--accent))] focus:ring-[hsl(var(--accent))]"
                      />
                    </td>
                  )}
                  {visibleColumns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        'px-4 py-3',
                        col.hideOnMobile && 'hidden sm:table-cell',
                        col.hideOnTablet && 'hidden lg:table-cell',
                        col.className
                      )}
                    >
                      {col.render ? col.render(row) : row[col.key]}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && !isLoading && !error && data.length > 0 && (
        <div className="flex items-center justify-between border-t border-[hsl(var(--border-faint))] px-4 py-3">
          <p className="text-xs text-[hsl(var(--text-tertiary))]">
            Showing {data.length} of {pagination.total.toLocaleString()} items
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={pagination.currentPage === 1}
              onClick={() => pagination.onPageChange(pagination.currentPage - 1)}
              className="h-7 px-2.5 text-xs"
            >
              <ChevronLeft className="h-3 w-3" />
            </Button>
            <span className="text-xs text-[hsl(var(--text-secondary))]">
              Page {pagination.currentPage} of {Math.max(1, Math.ceil(pagination.total / pagination.pageSize))}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={pagination.currentPage >= Math.ceil(pagination.total / pagination.pageSize)}
              onClick={() => pagination.onPageChange(pagination.currentPage + 1)}
              className="h-7 px-2.5 text-xs"
            >
              <ChevronRight className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
