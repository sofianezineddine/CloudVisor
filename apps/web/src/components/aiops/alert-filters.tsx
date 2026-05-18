'use client';

import * as React from 'react';
import { FilterBar, type FilterChip } from '@/components/ui/filter-bar';
import type { AIOpsAlertFilters } from '@/hooks/use-aiops-alerts';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AlertFiltersProps {
  filters: AIOpsAlertFilters;
  onFiltersChange: (filters: AIOpsAlertFilters) => void;
  className?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SEVERITY_OPTIONS = [
  { label: 'Critical', value: 'critical' },
  { label: 'High', value: 'high' },
  { label: 'Warning', value: 'warning' },
  { label: 'Info', value: 'info' },
  { label: 'Low', value: 'low' },
];

const STATUS_OPTIONS = [
  { label: 'Firing', value: 'firing' },
  { label: 'Acknowledged', value: 'acknowledged' },
  { label: 'Resolved', value: 'resolved' },
  { label: 'Suppressed', value: 'suppressed' },
];

const TIME_RANGE_OPTIONS = [
  { label: 'Last 1 hour', value: '1h' },
  { label: 'Last 6 hours', value: '6h' },
  { label: 'Last 24 hours', value: '24h' },
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'All time', value: 'all' },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getTimeFromValue(value: string): string | undefined {
  if (value === 'all') return undefined;
  const now = new Date();
  const map: Record<string, number> = {
    '1h': 60 * 60 * 1000,
    '6h': 6 * 60 * 60 * 1000,
    '24h': 24 * 60 * 60 * 1000,
    '7d': 7 * 24 * 60 * 60 * 1000,
    '30d': 30 * 24 * 60 * 60 * 1000,
  };
  const ms = map[value];
  if (!ms) return undefined;
  return new Date(now.getTime() - ms).toISOString();
}

// ─── Component ────────────────────────────────────────────────────────────────

export function AlertFilters({ filters, onFiltersChange, className }: AlertFiltersProps) {
  const [timeRange, setTimeRange] = React.useState('24h');

  // Build active filter chips for display
  const activeFilters: FilterChip[] = React.useMemo(() => {
    const chips: FilterChip[] = [];
    if (filters.severity?.length) {
      chips.push({
        key: 'severity',
        label: 'Severity',
        value: filters.severity.join(', '),
      });
    }
    if (filters.status?.length) {
      chips.push({
        key: 'status',
        label: 'Status',
        value: filters.status.join(', '),
      });
    }
    if (filters.source) {
      chips.push({
        key: 'source',
        label: 'Source',
        value: filters.source,
      });
    }
    if (timeRange !== '24h') {
      const opt = TIME_RANGE_OPTIONS.find((o) => o.value === timeRange);
      chips.push({
        key: 'time_range',
        label: 'Time',
        value: opt?.label ?? timeRange,
      });
    }
    return chips;
  }, [filters.severity, filters.status, filters.source, timeRange]);

  const handleSearchChange = React.useCallback(
    (value: string) => {
      onFiltersChange({ ...filters, search: value || undefined, page: 1 });
    },
    [filters, onFiltersChange]
  );

  const handleRemoveFilter = React.useCallback(
    (key: string) => {
      const next = { ...filters, page: 1 };
      switch (key) {
        case 'severity':
          next.severity = undefined;
          break;
        case 'status':
          next.status = undefined;
          break;
        case 'source':
          next.source = undefined;
          break;
        case 'time_range':
          setTimeRange('24h');
          next.time_from = getTimeFromValue('24h');
          break;
      }
      onFiltersChange(next);
    },
    [filters, onFiltersChange]
  );

  const handleClearAll = React.useCallback(() => {
    setTimeRange('24h');
    onFiltersChange({
      page: 1,
      page_size: filters.page_size,
      sort_by: filters.sort_by,
      sort_order: filters.sort_order,
      time_from: getTimeFromValue('24h'),
    });
  }, [filters.page_size, filters.sort_by, filters.sort_order, onFiltersChange]);

  const handleSeverityChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = Array.from(e.target.selectedOptions, (opt) => opt.value);
    onFiltersChange({
      ...filters,
      severity: selected.length > 0 ? selected : undefined,
      page: 1,
    });
  };

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = Array.from(e.target.selectedOptions, (opt) => opt.value);
    onFiltersChange({
      ...filters,
      status: selected.length > 0 ? selected : undefined,
      page: 1,
    });
  };

  const handleSourceChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFiltersChange({
      ...filters,
      source: e.target.value || undefined,
      page: 1,
    });
  };

  const handleTimeRangeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setTimeRange(value);
    onFiltersChange({
      ...filters,
      time_from: getTimeFromValue(value),
      page: 1,
    });
  };

  return (
    <div className={className}>
      <FilterBar
        searchValue={filters.search ?? ''}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Search alerts by name, description, labels…"
        activeFilters={activeFilters}
        onRemoveFilter={handleRemoveFilter}
        onClearAll={handleClearAll}
      >
        {/* Severity multi-select */}
        <select
          multiple
          value={filters.severity ?? []}
          onChange={handleSeverityChange}
          className="rounded-md border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))] px-3 py-1.5 text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--accent))] focus:outline-none h-8"
          title="Filter by severity"
        >
          {SEVERITY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Status multi-select */}
        <select
          multiple
          value={filters.status ?? []}
          onChange={handleStatusChange}
          className="rounded-md border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))] px-3 py-1.5 text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--accent))] focus:outline-none h-8"
          title="Filter by status"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Source input */}
        <input
          type="text"
          value={filters.source ?? ''}
          onChange={handleSourceChange}
          placeholder="Source…"
          className="rounded-md border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))] px-3 py-1.5 text-sm text-[hsl(var(--text-primary))] placeholder-[hsl(var(--text-tertiary))] focus:border-[hsl(var(--accent))] focus:outline-none h-8 w-32"
        />

        {/* Time range picker */}
        <select
          value={timeRange}
          onChange={handleTimeRangeChange}
          className="rounded-md border border-[hsl(var(--border-default))] bg-[hsl(var(--bg-surface))] px-3 py-1.5 text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--accent))] focus:outline-none h-8"
          title="Time range"
        >
          {TIME_RANGE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </FilterBar>
    </div>
  );
}
