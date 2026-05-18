'use client';

import * as React from 'react';
import { X, AlertTriangle } from 'lucide-react';
import { DetailDrawer } from '@/components/ui/detail-drawer';
import { Button } from '@/components/ui/button';
import {
  useToggleWorkflowStatus,
  useRunWorkflow,
  type AIOpsWorkflow,
} from '@/hooks/use-aiops-workflows';

// ─── Types ────────────────────────────────────────────────────────────────────

interface WorkflowEditorProps {
  workflow: AIOpsWorkflow | null;
  onClose: () => void;
}

// ─── YAML Validation ──────────────────────────────────────────────────────────

interface YamlError {
  line: number;
  message: string;
}

function validateYaml(yaml: string): YamlError | null {
  const lines = yaml.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    // Check for tabs (YAML uses spaces)
    if (line.includes('\t')) {
      return { line: i + 1, message: 'Tabs are not allowed in YAML, use spaces' };
    }
    // Check for inconsistent indentation
    const indent = line.match(/^( *)/)?.[1]?.length ?? 0;
    if (indent % 2 !== 0 && line.trim().length > 0) {
      return { line: i + 1, message: 'Indentation must be a multiple of 2 spaces' };
    }
    // Check for missing colon in key-value pairs (basic check)
    if (line.trim().length > 0 && !line.trim().startsWith('#') && !line.trim().startsWith('-')) {
      const trimmed = line.trim();
      if (trimmed.includes(' ') && !trimmed.includes(':') && !trimmed.startsWith('- ')) {
        return { line: i + 1, message: 'Expected key-value pair (missing colon)' };
      }
    }
  }
  return null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(dateStr: string | undefined): string {
  if (!dateStr) return 'Never';
  return new Date(dateStr).toLocaleString();
}

// ─── Component ────────────────────────────────────────────────────────────────

export function WorkflowEditor({ workflow, onClose }: WorkflowEditorProps) {
  const toggleStatus = useToggleWorkflowStatus();
  const runWorkflow = useRunWorkflow();
  const [yamlContent, setYamlContent] = React.useState('');
  const [yamlError, setYamlError] = React.useState<YamlError | null>(null);

  React.useEffect(() => {
    if (workflow) {
      setYamlContent(workflow.yaml_definition);
      setYamlError(null);
    }
  }, [workflow]);

  const handleYamlChange = (value: string) => {
    setYamlContent(value);
    const error = validateYaml(value);
    setYamlError(error);
  };

  const handleToggle = () => {
    if (!workflow) return;
    toggleStatus.mutate({
      id: workflow.id,
      status: workflow.status === 'enabled' ? 'disabled' : 'enabled',
    });
  };

  const handleRun = () => {
    if (!workflow) return;
    runWorkflow.mutate({ id: workflow.id });
  };

  return (
    <DetailDrawer
      isOpen={!!workflow}
      onClose={onClose}
      title={workflow?.name ?? 'Workflow'}
      subtitle={workflow ? `${workflow.status} • ${workflow.execution_count} executions` : undefined}
      width={800}
      actions={
        workflow ? (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleToggle}
            >
              {workflow.status === 'enabled' ? 'Disable' : 'Enable'}
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleRun}
              disabled={workflow.status === 'disabled'}
            >
              Run Now
            </Button>
          </div>
        ) : undefined
      }
    >
      {workflow && (
        <div className="space-y-6">
          {/* Metadata */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <span className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                Status
              </span>
              <p className="text-sm mt-1" style={{ color: workflow.status === 'enabled' ? 'var(--success)' : 'var(--text-secondary)' }}>
                {workflow.status === 'enabled' ? 'Enabled' : 'Disabled'}
              </p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                Last Execution
              </span>
              <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                {formatDateTime(workflow.last_execution)}
              </p>
            </div>
            <div>
              <span className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                Total Executions
              </span>
              <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                {workflow.execution_count}
              </p>
            </div>
          </div>

          {/* YAML Editor */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3
                className="text-xs font-medium uppercase tracking-wider"
                style={{ color: 'var(--text-tertiary)' }}
              >
                YAML Definition
              </h3>
              {yamlError && (
                <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--critical)' }}>
                  <AlertTriangle className="h-3 w-3" />
                  Line {yamlError.line}: {yamlError.message}
                </span>
              )}
            </div>
            <textarea
              value={yamlContent}
              onChange={(e) => handleYamlChange(e.target.value)}
              spellCheck={false}
              className="w-full rounded-md p-4 text-sm leading-relaxed resize-y"
              style={{
                backgroundColor: 'var(--bg-elevated)',
                border: `1px solid ${yamlError ? 'var(--critical)' : 'var(--border-default)'}`,
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-mono, monospace)',
                minHeight: '300px',
              }}
            />
          </div>

          {/* Trigger Configuration */}
          {Object.keys(workflow.trigger_config).length > 0 && (
            <div>
              <h3
                className="text-xs font-medium uppercase tracking-wider mb-2"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Trigger Configuration
              </h3>
              <div
                className="rounded-md p-3"
                style={{
                  backgroundColor: 'var(--bg-elevated)',
                  border: '1px solid var(--border-default)',
                }}
              >
                {Object.entries(workflow.trigger_config).map(([key, value]) => (
                  <div key={key} className="flex items-center gap-2 py-1">
                    <span className="text-xs font-medium" style={{ color: 'var(--text-tertiary)' }}>
                      {key}:
                    </span>
                    <span className="text-sm" style={{ color: 'var(--text-primary)' }}>
                      {String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </DetailDrawer>
  );
}
