'use client';

import * as React from 'react';
import { Plus, Pencil, Trash2, Clock, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useAIOpsMaintenanceWindows,
  useCreateMaintenanceWindow,
  useUpdateMaintenanceWindow,
  useDeleteMaintenanceWindow,
  type AIOpsMaintenanceWindow,
  type CreateMaintenanceWindowPayload,
} from '@/hooks/use-aiops-maintenance';

// ─── Types ────────────────────────────────────────────────────────────────────

interface MaintenanceWindowFormProps {
  className?: string;
}

interface FormState {
  name: string;
  start_time: string;
  end_time: string;
  provider: string;
  labels: string;
  service: string;
}

interface FormErrors {
  name?: string;
  start_time?: string;
  end_time?: string;
}

// ─── Status Styles ────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  active: { color: 'var(--success)', bg: 'var(--success-bg, rgba(61, 184, 122, 0.12))', label: 'Active' },
  scheduled: { color: 'var(--info)', bg: 'var(--info-bg)', label: 'Scheduled' },
  expired: { color: 'var(--text-tertiary)', bg: 'var(--bg-elevated)', label: 'Expired' },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function toLocalDatetimeString(isoStr: string): string {
  if (!isoStr) return '';
  const date = new Date(isoStr);
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60 * 1000);
  return local.toISOString().slice(0, 16);
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

function validateForm(form: FormState): FormErrors {
  const errors: FormErrors = {};

  if (!form.name.trim() || form.name.trim().length < 1) {
    errors.name = 'Name is required';
  } else if (form.name.trim().length > 128) {
    errors.name = 'Name must be 128 characters or less';
  }

  if (!form.start_time) {
    errors.start_time = 'Start time is required';
  }

  if (!form.end_time) {
    errors.end_time = 'End time is required';
  } else if (form.start_time && new Date(form.end_time) <= new Date(form.start_time)) {
    errors.end_time = 'End time must be after start time';
  } else if (new Date(form.end_time) < new Date()) {
    errors.end_time = 'End time cannot be in the past';
  }

  return errors;
}

// ─── Form Dialog ──────────────────────────────────────────────────────────────

function MaintenanceFormDialog({
  isOpen,
  onClose,
  editingWindow,
}: {
  isOpen: boolean;
  onClose: () => void;
  editingWindow: AIOpsMaintenanceWindow | null;
}) {
  const createWindow = useCreateMaintenanceWindow();
  const updateWindow = useUpdateMaintenanceWindow();
  const [submitting, setSubmitting] = React.useState(false);
  const [errors, setErrors] = React.useState<FormErrors>({});

  const [form, setForm] = React.useState<FormState>({
    name: '',
    start_time: '',
    end_time: '',
    provider: '',
    labels: '',
    service: '',
  });

  // Populate form when editing
  React.useEffect(() => {
    if (editingWindow) {
      setForm({
        name: editingWindow.name,
        start_time: toLocalDatetimeString(editingWindow.start_time),
        end_time: toLocalDatetimeString(editingWindow.end_time),
        provider: (editingWindow.filters?.provider as string) ?? '',
        labels: (editingWindow.filters?.labels as string) ?? '',
        service: (editingWindow.filters?.service as string) ?? '',
      });
    } else {
      setForm({ name: '', start_time: '', end_time: '', provider: '', labels: '', service: '' });
    }
    setErrors({});
  }, [editingWindow, isOpen]);

  const handleChange = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationErrors = validateForm(form);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    const filters: Record<string, unknown> = {};
    if (form.provider.trim()) filters.provider = form.provider.trim();
    if (form.labels.trim()) filters.labels = form.labels.trim();
    if (form.service.trim()) filters.service = form.service.trim();

    const payload: CreateMaintenanceWindowPayload = {
      name: form.name.trim(),
      start_time: new Date(form.start_time).toISOString(),
      end_time: new Date(form.end_time).toISOString(),
      filters,
    };

    setSubmitting(true);
    try {
      if (editingWindow) {
        await updateWindow.mutateAsync({ id: editingWindow.id, ...payload });
      } else {
        await createWindow.mutateAsync(payload);
      }
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-[60]"
        style={{ backgroundColor: 'rgba(0, 0, 0, 0.6)' }}
        onClick={onClose}
      />
      <div
        className="fixed top-1/2 left-1/2 z-[70] -translate-x-1/2 -translate-y-1/2 w-[520px] max-w-[90vw] rounded-lg p-6"
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          boxShadow: '0 4px 24px rgba(0, 0, 0, 0.25)',
        }}
      >
        <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
          {editingWindow ? 'Edit Maintenance Window' : 'Create Maintenance Window'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
              Name <span style={{ color: 'var(--critical)' }}>*</span>
            </label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="Maintenance window name"
              maxLength={128}
              className="w-full rounded-md px-3 py-2 text-sm"
              style={{
                backgroundColor: 'var(--bg-elevated)',
                border: `1px solid ${errors.name ? 'var(--critical)' : 'var(--border-default)'}`,
                color: 'var(--text-primary)',
              }}
            />
            {errors.name && (
              <p className="text-xs mt-1" style={{ color: 'var(--critical)' }}>{errors.name}</p>
            )}
          </div>

          {/* Start Time */}
          <div>
            <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
              Start Time <span style={{ color: 'var(--critical)' }}>*</span>
            </label>
            <input
              type="datetime-local"
              value={form.start_time}
              onChange={(e) => handleChange('start_time', e.target.value)}
              className="w-full rounded-md px-3 py-2 text-sm"
              style={{
                backgroundColor: 'var(--bg-elevated)',
                border: `1px solid ${errors.start_time ? 'var(--critical)' : 'var(--border-default)'}`,
                color: 'var(--text-primary)',
              }}
            />
            {errors.start_time && (
              <p className="text-xs mt-1" style={{ color: 'var(--critical)' }}>{errors.start_time}</p>
            )}
          </div>

          {/* End Time */}
          <div>
            <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
              End Time <span style={{ color: 'var(--critical)' }}>*</span>
            </label>
            <input
              type="datetime-local"
              value={form.end_time}
              onChange={(e) => handleChange('end_time', e.target.value)}
              className="w-full rounded-md px-3 py-2 text-sm"
              style={{
                backgroundColor: 'var(--bg-elevated)',
                border: `1px solid ${errors.end_time ? 'var(--critical)' : 'var(--border-default)'}`,
                color: 'var(--text-primary)',
              }}
            />
            {errors.end_time && (
              <p className="text-xs mt-1" style={{ color: 'var(--critical)' }}>{errors.end_time}</p>
            )}
          </div>

          {/* Filter Criteria */}
          <div
            className="pt-3"
            style={{ borderTop: '1px solid var(--border-default)' }}
          >
            <p className="text-xs font-medium uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>
              Filter Criteria
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                  Provider
                </label>
                <input
                  type="text"
                  value={form.provider}
                  onChange={(e) => handleChange('provider', e.target.value)}
                  placeholder="e.g. prometheus, datadog"
                  className="w-full rounded-md px-3 py-2 text-sm"
                  style={{
                    backgroundColor: 'var(--bg-elevated)',
                    border: '1px solid var(--border-default)',
                    color: 'var(--text-primary)',
                  }}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                  Labels
                </label>
                <input
                  type="text"
                  value={form.labels}
                  onChange={(e) => handleChange('labels', e.target.value)}
                  placeholder="e.g. env=production, team=backend"
                  className="w-full rounded-md px-3 py-2 text-sm"
                  style={{
                    backgroundColor: 'var(--bg-elevated)',
                    border: '1px solid var(--border-default)',
                    color: 'var(--text-primary)',
                  }}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                  Service
                </label>
                <input
                  type="text"
                  value={form.service}
                  onChange={(e) => handleChange('service', e.target.value)}
                  placeholder="e.g. api-gateway, auth-service"
                  className="w-full rounded-md px-3 py-2 text-sm"
                  style={{
                    backgroundColor: 'var(--bg-elevated)',
                    border: '1px solid var(--border-default)',
                    color: 'var(--text-primary)',
                  }}
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" disabled={submitting}>
              {submitting ? 'Saving...' : editingWindow ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </div>
    </>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function MaintenanceWindowManager({ className }: MaintenanceWindowFormProps) {
  const { data: windows, isLoading, error } = useAIOpsMaintenanceWindows();
  const deleteWindow = useDeleteMaintenanceWindow();

  const [showForm, setShowForm] = React.useState(false);
  const [editingWindow, setEditingWindow] = React.useState<AIOpsMaintenanceWindow | null>(null);

  const handleCreate = () => {
    setEditingWindow(null);
    setShowForm(true);
  };

  const handleEdit = (window: AIOpsMaintenanceWindow) => {
    setEditingWindow(window);
    setShowForm(true);
  };

  const handleDelete = async (window: AIOpsMaintenanceWindow) => {
    await deleteWindow.mutateAsync({ id: window.id });
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingWindow(null);
  };

  // Build filter summary
  const getFilterSummary = (filters: Record<string, unknown>): string => {
    const parts: string[] = [];
    if (filters.provider) parts.push(`provider: ${filters.provider}`);
    if (filters.labels) parts.push(`labels: ${filters.labels}`);
    if (filters.service) parts.push(`service: ${filters.service}`);
    return parts.length > 0 ? parts.join(', ') : 'All alerts';
  };

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-h2" style={{ color: 'var(--text-primary)' }}>
            Maintenance Windows
          </h1>
          <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
            Schedule maintenance windows to suppress alerts during planned downtime
          </p>
        </div>
        <Button variant="primary" size="sm" onClick={handleCreate}>
          <Plus className="h-3.5 w-3.5 mr-1.5" />
          Create Window
        </Button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="card overflow-hidden">
          <div className="animate-pulse space-y-4 p-6">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 rounded" style={{ backgroundColor: 'var(--bg-elevated)' }} />
            ))}
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div
          className="flex items-center justify-center rounded-lg border p-12"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border-default)' }}
        >
          <p className="text-sm" style={{ color: 'var(--critical)' }}>
            {(error as Error).message}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && windows && windows.length === 0 && (
        <div
          className="flex flex-col items-center justify-center rounded-lg border p-12"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border-default)' }}
        >
          <Clock className="h-8 w-8 mb-3" style={{ color: 'var(--text-tertiary)' }} />
          <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            No maintenance windows
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
            Create a maintenance window to suppress alerts during planned downtime
          </p>
        </div>
      )}

      {/* List */}
      {!isLoading && !error && windows && windows.length > 0 && (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)' }}>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider w-[110px]" style={{ color: 'var(--text-secondary)' }}>Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider hidden sm:table-cell" style={{ color: 'var(--text-secondary)' }}>Start</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider hidden sm:table-cell" style={{ color: 'var(--text-secondary)' }}>End</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider hidden md:table-cell" style={{ color: 'var(--text-secondary)' }}>Filters</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider w-[100px]" style={{ color: 'var(--text-secondary)' }}>Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: 'var(--border-default)' }}>
              {windows.map((window) => {
                const statusStyle = STATUS_STYLES[window.status] ?? STATUS_STYLES.expired;
                return (
                  <tr key={window.id} className="transition-colors hover:bg-[var(--bg-elevated)]">
                    <td className="px-4 py-3">
                      <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                        {window.name}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="inline-flex items-center text-xs font-medium whitespace-nowrap"
                        style={{
                          color: statusStyle.color,
                          backgroundColor: statusStyle.bg,
                          padding: '2px 8px',
                          borderRadius: '99px',
                        }}
                      >
                        {statusStyle.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                        {formatDateTime(window.start_time)}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                        {formatDateTime(window.end_time)}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                        {getFilterSummary(window.filters)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(window)}
                          title="Edit"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(window)}
                          title="Delete"
                        >
                          <Trash2 className="h-3.5 w-3.5" style={{ color: 'var(--critical)' }} />
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Form Dialog */}
      <MaintenanceFormDialog
        isOpen={showForm}
        onClose={handleCloseForm}
        editingWindow={editingWindow}
      />
    </div>
  );
}
