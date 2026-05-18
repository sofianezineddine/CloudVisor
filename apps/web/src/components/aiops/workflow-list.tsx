'use client';

import * as React from 'react';
import { Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useToggleWorkflowStatus,
  useRunWorkflow,
  type AIOpsWorkflow,
} from '@/hooks/use-aiops-workflows';

// ─── Types ────────────────────────────────────────────────────────────────────

interface WorkflowListProps {
  workflows: AIOpsWorkflow[];
  isLoading?: boolean;
  error?: string | null;
  onRowClick: (workflow: AIOpsWorkflow) => void;
  className?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatRelativeTime(dateStr: string | undefined): string {
  if (!dateStr) return 'Never';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 30) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

// ─── Toggle Switch ────────────────────────────────────────────────────────────

function StatusToggle({
  enabled,
  onToggle,
  disabled,
}: {
  enabled: boolean;
  onToggle: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      disabled={disabled}
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
      className="relative inline-flex h-5 w-9 items-center rounded-full transition-colors disabled:opacity-50"
      style={{
        backgroundColor: enabled ? 'var(--accent)' : 'var(--bg-elevated)',
        border: `1px solid ${enabled ? 'var(--accent)' : 'var(--border-default)'}`,
      }}
    >
      <span
        className="inline-block h-3.5 w-3.5 rounded-full transition-transform"
        style={{
          backgroundColor: enabled ? '#fff' : 'var(--text-tertiary)',
          transform: enabled ? 'translateX(17px)' : 'translateX(3px)',
        }}
      />
    </button>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function WorkflowList({
  workflows,
  isLoading,
  error,
  onRowClick,
  className,
}: WorkflowListProps) {
  const toggleStatus = useToggleWorkflowStatus();
  const runWorkflow = useRunWorkflow();

  const handleToggle = (workflow: AIOpsWorkflow) => {
    toggleStatus.mutate({
      id: workflow.id,
      status: workflow.status === 'enabled' ? 'disabled' : 'enabled',
    });
  };

  const handleRun = (workflow: AIOpsWorkflow) => {
    runWorkflow.mutate({ id: workflow.id });
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={className}>
        <div className="card overflow-hidden">
          <div className="animate-pulse space-y-4 p-6">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 rounded" style={{ backgroundColor: 'var(--bg-elevated)' }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={className}>
        <div
          className="flex items-center justify-center rounded-lg border p-12"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border-default)' }}
        >
          <p className="text-sm" style={{ color: 'var(--critical)' }}>{error}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (workflows.length === 0) {
    return (
      <div className={className}>
        <div
          className="flex flex-col items-center justify-center rounded-lg border p-12"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border-default)' }}
        >
          <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            No workflows found
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
            Create a workflow to automate alert response actions
          </p>
        </div>
      </div>
    );
  }

  // Sorted by last_execution desc
  const sorted = [...workflows].sort((a, b) => {
    if (!a.last_execution && !b.last_execution) return 0;
    if (!a.last_execution) return 1;
    if (!b.last_execution) return -1;
    return new Date(b.last_execution).getTime() - new Date(a.last_execution).getTime();
  });

  return (
    <div className={className}>
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)' }}>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Name</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider w-[100px]" style={{ color: 'var(--text-secondary)' }}>Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider hidden md:table-cell" style={{ color: 'var(--text-secondary)' }}>Trigger</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider w-[120px] hidden sm:table-cell" style={{ color: 'var(--text-secondary)' }}>Last Run</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider w-[80px] hidden sm:table-cell" style={{ color: 'var(--text-secondary)' }}>Runs</th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider w-[80px]" style={{ color: 'var(--text-secondary)' }}>Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y" style={{ borderColor: 'var(--border-default)' }}>
            {sorted.map((workflow) => (
              <tr
                key={workflow.id}
                onClick={() => onRowClick(workflow)}
                className="cursor-pointer transition-colors hover:bg-[var(--bg-elevated)]"
              >
                <td className="px-4 py-3">
                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                    {workflow.name}
                  </span>
                </td>
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <StatusToggle
                    enabled={workflow.status === 'enabled'}
                    onToggle={() => handleToggle(workflow)}
                  />
                </td>
                <td className="px-4 py-3 hidden md:table-cell">
                  <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {Object.keys(workflow.trigger_config).length > 0
                      ? Object.entries(workflow.trigger_config).map(([k, v]) => `${k}: ${v}`).join(', ')
                      : 'Manual'}
                  </span>
                </td>
                <td className="px-4 py-3 hidden sm:table-cell">
                  <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {formatRelativeTime(workflow.last_execution)}
                  </span>
                </td>
                <td className="px-4 py-3 hidden sm:table-cell">
                  <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {workflow.execution_count}
                  </span>
                </td>
                <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRun(workflow)}
                    title="Run workflow"
                    disabled={workflow.status === 'disabled'}
                  >
                    <Play className="h-3.5 w-3.5" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
