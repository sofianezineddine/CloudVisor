'use client';

import * as React from 'react';
import { Search, Filter, Download, X, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './button';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FilterChip {
  key: string;
  label: string;
  value: string;
}

export interface FilterBarProps {
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  activeFilters?: FilterChip[];
  onRemoveFilter?: (key: string) => void;
  onClearAll?: () => void;
  onExport?: () => void;
  onFilterClick?: () => void;
  sortOptions?: Array<{ label: string; value: string }>;
  sortValue?: string;
  onSortChange?: (value: string) => void;
  densityOptions?: Array<{ label: string; value: string }>;
  densityValue?: string;
  onDensityChange?: (value: string) => void;
  className?: string;
  children?: React.ReactNode;
}

// ─── FilterBar Component ──────────────────────────────────────────────────────

export function FilterBar({
  searchValue = '',
  onSearchChange,
  searchPlaceholder = 'Search…',
  activeFilters = [],
  onRemoveFilter,
  onClearAll,
  onExport,
  onFilterClick,
  sortOptions,
  sortValue,
  onSortChange,
  densityOptions,
  densityValue,
  onDensityChange,
  className,
  children,
}: FilterBarProps) {
  const [localSearch, setLocalSearch] = React.useState(searchValue);

  // Debounce search
  React.useEffect(() => {
    const timer = setTimeout(() => {
      onSearchChange?.(localSearch);
    }, 300);
    return () => clearTimeout(timer);
  }, [localSearch, onSearchChange]);

  // Sync external changes
  React.useEffect(() => {
    setLocalSearch(searchValue);
  }, [searchValue]);

  return (
    <div className={cn('space-y-3', className)}>
      {/* Main filter row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search input */}
        {onSearchChange && (
          <div className="relative flex-1 min-w-[180px] max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--text-tertiary))]" />
            <input
              type="text"
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full rounded-md border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))] pl-9 pr-3 py-2 text-sm text-[hsl(var(--text-primary))] placeholder-[hsl(var(--text-tertiary))] focus:border-[hsl(var(--accent))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--accent))]"
            />
            {localSearch && (
              <button
                onClick={() => setLocalSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-tertiary))] hover:text-[hsl(var(--text-primary))]"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        )}

        {/* Custom children (e.g., status dropdown, provider filter) */}
        {children}

        {/* Right-side actions */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Filter button */}
          {onFilterClick && (
            <Button
              variant="outline"
              size="sm"
              onClick={onFilterClick}
              className="gap-1.5"
            >
              <Filter className="h-3.5 w-3.5" />
              Filters
              {activeFilters.length > 0 && (
                <span className="ml-1 rounded-full bg-[hsl(var(--accent))] px-1.5 py-0.5 text-xs font-medium text-white">
                  {activeFilters.length}
                </span>
              )}
            </Button>
          )}

          {/* Sort dropdown */}
          {sortOptions && sortOptions.length > 0 && (
            <select
              value={sortValue}
              onChange={(e) => onSortChange?.(e.target.value)}
              className="rounded-md border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))] px-3 py-1.5 text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--accent))] focus:outline-none h-8"
            >
              {sortOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          )}

          {/* Density toggle */}
          {densityOptions && densityOptions.length > 0 && (
            <select
              value={densityValue}
              onChange={(e) => onDensityChange?.(e.target.value)}
              className="rounded-md border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))] px-3 py-1.5 text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--accent))] focus:outline-none h-8"
            >
              {densityOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          )}

          {/* Export button */}
          {onExport && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExport}
              className="gap-1.5"
            >
              <Download className="h-3.5 w-3.5" />
              Export
            </Button>
          )}
        </div>
      </div>

      {/* Active filter chips */}
      {activeFilters.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-[hsl(var(--text-tertiary))]">
            Active filters:
          </span>
          {activeFilters.map((filter) => (
            <div
              key={filter.key}
              className="inline-flex items-center gap-1.5 rounded-md bg-[hsl(var(--accent-dim))] px-2.5 py-1 text-xs font-medium text-[hsl(var(--accent))]"
            >
              <span>{filter.label}: {filter.value}</span>
              {onRemoveFilter && (
                <button
                  onClick={() => onRemoveFilter(filter.key)}
                  className="hover:text-[hsl(var(--accent-hover))]"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          ))}
          {onClearAll && activeFilters.length > 1 && (
            <button
              onClick={onClearAll}
              className="text-xs font-medium text-[hsl(var(--text-tertiary))] hover:text-[hsl(var(--text-primary))] underline"
            >
              Clear all
            </button>
          )}
        </div>
      )}
    </div>
  );
}
