'use client';

import * as React from 'react';
import { X, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './button';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FilterGroup {
  id: string;
  label: string;
  options: FilterOption[];
  defaultExpanded?: boolean;
}

export interface FilterOption {
  value: string;
  label: string;
  count?: number;
}

export interface FilterSidebarProps {
  groups: FilterGroup[];
  activeFilters: Record<string, string[]>;
  onFilterChange: (groupId: string, values: string[]) => void;
  onClearAll: () => void;
  className?: string;
  width?: number;
}

// ─── FilterSidebar Component ──────────────────────────────────────────────────

export function FilterSidebar({
  groups,
  activeFilters,
  onFilterChange,
  onClearAll,
  className,
  width = 240,
}: FilterSidebarProps) {
  const [expandedGroups, setExpandedGroups] = React.useState<Set<string>>(
    new Set(groups.filter(g => g.defaultExpanded !== false).map(g => g.id))
  );

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  const toggleOption = (groupId: string, value: string) => {
    const current = activeFilters[groupId] || [];
    const next = current.includes(value)
      ? current.filter(v => v !== value)
      : [...current, value];
    onFilterChange(groupId, next);
  };

  const totalActiveFilters = Object.values(activeFilters).reduce(
    (sum, values) => sum + values.length,
    0
  );

  return (
    <div
      className={cn(
        'flex flex-col border-r border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))]',
        className
      )}
      style={{ width: `${width}px` }}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[hsl(var(--border-default))] px-4 py-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
            Filters
          </h3>
          {totalActiveFilters > 0 && (
            <span className="rounded-full bg-[hsl(var(--accent))] px-2 py-0.5 text-xs font-medium text-white">
              {totalActiveFilters}
            </span>
          )}
        </div>
        {totalActiveFilters > 0 && (
          <button
            onClick={onClearAll}
            className="text-xs font-medium text-[hsl(var(--text-tertiary))] hover:text-[hsl(var(--text-primary))] underline"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Filter Groups */}
      <div className="flex-1 overflow-y-auto">
        {groups.map((group) => {
          const isExpanded = expandedGroups.has(group.id);
          const activeCount = (activeFilters[group.id] || []).length;

          return (
            <div key={group.id} className="border-b border-[hsl(var(--border-faint))]">
              {/* Group Header */}
              <button
                onClick={() => toggleGroup(group.id)}
                className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-[hsl(var(--bg-elevated))] transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                    {group.label}
                  </span>
                  {activeCount > 0 && (
                    <span className="rounded-full bg-[hsl(var(--accent-dim))] px-1.5 py-0.5 text-xs font-medium text-[hsl(var(--accent))]">
                      {activeCount}
                    </span>
                  )}
                </div>
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4 text-[hsl(var(--text-tertiary))]" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-[hsl(var(--text-tertiary))]" />
                )}
              </button>

              {/* Group Options */}
              {isExpanded && (
                <div className="px-4 pb-3 space-y-2">
                  {group.options.map((option) => {
                    const isActive = (activeFilters[group.id] || []).includes(option.value);

                    return (
                      <label
                        key={option.value}
                        className="flex items-center gap-2 cursor-pointer group"
                      >
                        <input
                          type="checkbox"
                          checked={isActive}
                          onChange={() => toggleOption(group.id, option.value)}
                          className="h-4 w-4 rounded border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))] text-[hsl(var(--accent))] focus:ring-[hsl(var(--accent))] focus:ring-offset-0"
                        />
                        <span className="flex-1 text-sm text-[hsl(var(--text-primary))] group-hover:text-[hsl(var(--accent))]">
                          {option.label}
                        </span>
                        {option.count !== undefined && (
                          <span className="text-xs font-mono text-[hsl(var(--text-tertiary))]">
                            {option.count}
                          </span>
                        )}
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Mobile Filter Button ─────────────────────────────────────────────────────

export interface FilterButtonProps {
  activeFilterCount: number;
  onClick: () => void;
}

export function FilterButton({ activeFilterCount, onClick }: FilterButtonProps) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onClick}
      className="gap-1.5 lg:hidden"
    >
      <svg
        className="h-3.5 w-3.5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
        />
      </svg>
      Filters
      {activeFilterCount > 0 && (
        <span className="rounded-full bg-[hsl(var(--accent))] px-1.5 py-0.5 text-xs font-medium text-white">
          {activeFilterCount}
        </span>
      )}
    </Button>
  );
}

// ─── Mobile Filter Sheet ──────────────────────────────────────────────────────

export interface MobileFilterSheetProps extends FilterSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MobileFilterSheet({
  isOpen,
  onClose,
  groups,
  activeFilters,
  onFilterChange,
  onClearAll,
}: MobileFilterSheetProps) {
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
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
        onClick={onClose}
      />

      {/* Sheet */}
      <div className="fixed bottom-0 left-0 right-0 z-50 max-h-[80vh] rounded-t-2xl bg-[hsl(var(--bg-surface))] shadow-2xl lg:hidden">
        {/* Handle */}
        <div className="flex justify-center pt-3 pb-2">
          <div className="h-1 w-12 rounded-full bg-[hsl(var(--border-default))]" />
        </div>

        {/* Content */}
        <div className="flex flex-col max-h-[calc(80vh-2rem)]">
          <FilterSidebar
            groups={groups}
            activeFilters={activeFilters}
            onFilterChange={onFilterChange}
            onClearAll={onClearAll}
            width={0}
            className="w-full border-r-0"
          />

          {/* Footer */}
          <div className="border-t border-[hsl(var(--border-default))] p-4">
            <Button onClick={onClose} className="w-full">
              Apply Filters
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
