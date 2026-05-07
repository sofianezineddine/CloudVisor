'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShieldOff, Plus, Trash2, Loader2, AlertTriangle, CheckCircle2, X } from 'lucide-react';
import apiClient from '@/lib/api/apiClient';

// ─── Types ────────────────────────────────────────────────────────────────────

interface SuppressionRule {
  id: string;
  rule_id: string | null;
  resource_tag_key: string | null;
  resource_tag_value: string | null;
  account_id: string | null;
  region: string | null;
  reason: string | null;
  created_by: string;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
}

// ─── API helpers ──────────────────────────────────────────────────────────────

const suppressionsAPI = {
  list: () => apiClient['findings'] // reuse apiFetch via gateway
    ? fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005'}/v1/suppressions`, {
        headers: {
          'Content-Type': 'application/json',
          ...(typeof window !== 'undefined' && localStorage.getItem('access_token')
            ? { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
            : {}),
        },
      }).then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
    : Promise.resolve({ data: [] }),

  create: (data: Partial<SuppressionRule>) =>
    fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005'}/v1/suppressions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(typeof window !== 'undefined' && localStorage.getItem('access_token')
          ? { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
          : {}),
      },
      body: JSON.stringify(data),
    }).then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(new Error(e.detail || `HTTP ${r.status}`)))),

  delete: (id: string) =>
    fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005'}/v1/suppressions/${id}`, {
      method: 'DELETE',
      headers: {
        ...(typeof window !== 'undefined' && localStorage.getItem('access_token')
          ? { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
          : {}),
      },
    }).then(r => r.ok || r.status === 204 ? null : Promise.reject(new Error(`HTTP ${r.status}`))),
};

// ─── Create form ──────────────────────────────────────────────────────────────

function CreateSuppressionForm({ onSuccess, onCancel }: { onSuccess: () => void; onCancel: () => void }) {
  const [form, setForm] = React.useState({
    rule_id: '',
    resource_tag_key: '',
    resource_tag_value: '',
    account_id: '',
    region: '',
    reason: '',
    expires_in_days: '',
  });
  const [error, setError] = React.useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () => suppressionsAPI.create({
      rule_id: form.rule_id || undefined,
      resource_tag_key: form.resource_tag_key || undefined,
      resource_tag_value: form.resource_tag_value || undefined,
      account_id: form.account_id || undefined,
      region: form.region || undefined,
      reason: form.reason || undefined,
      expires_in_days: form.expires_in_days ? parseInt(form.expires_in_days) : undefined,
    } as any),
    onSuccess: () => { setError(null); onSuccess(); },
    onError: (e: Error) => setError(e.message),
  });

  const field = (key: keyof typeof form, label: string, placeholder: string, type = 'text') => (
    <div>
      <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>{label}</label>
      <input
        type={type}
        value={form[key]}
        onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
        placeholder={placeholder}
        className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
      />
    </div>
  );

  return (
    <div className="cv-container p-5 space-y-4">
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>New Suppression Rule</h3>
      <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
        At least one criteria is required. Findings matching ALL specified criteria will be suppressed.
      </p>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border p-3 text-sm"
          style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}>
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {field('rule_id', 'Rule ID (optional)', 'e.g. cspm.aws.s3.public-access')}
        {field('account_id', 'Account ID (optional)', 'e.g. 123456789012')}
        {field('region', 'Region (optional)', 'e.g. us-east-1')}
        {field('resource_tag_key', 'Tag Key (optional)', 'e.g. env')}
        {field('resource_tag_value', 'Tag Value (optional)', 'e.g. dev')}
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Expires In</label>
          <select
            value={form.expires_in_days}
            onChange={e => setForm(p => ({ ...p, expires_in_days: e.target.value }))}
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
          >
            <option value="">Never</option>
            <option value="7">7 days</option>
            <option value="30">30 days</option>
          </select>
        </div>
      </div>

      {field('reason', 'Reason (optional)', 'Why are you suppressing these findings?')}

      <div className="flex gap-3 pt-1">
        <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending} className="gap-2">
          {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Create Rule
        </Button>
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function SuppressionsPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = React.useState(false);
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  React.useEffect(() => { document.title = 'Suppression Rules - Settings - CloudVisor'; }, []);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['suppressions'],
    queryFn: suppressionsAPI.list,
    select: (d) => (d?.data ?? d ?? []) as SuppressionRule[],
  });

  const deleteMutation = useMutation({
    mutationFn: suppressionsAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppressions'] });
      setSuccessMsg('Suppression rule deleted');
      setTimeout(() => setSuccessMsg(null), 3000);
    },
  });

  const rules = data ?? [];

  return (
    <>
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Suppression Rules</h1>
          <Button className="gap-2" onClick={() => setShowCreate(v => !v)}>
            {showCreate ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showCreate ? 'Cancel' : 'New Rule'}
          </Button>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Automatically suppress findings that match specified criteria. Suppressed findings are logged but not alerted.
        </p>
      </div>

      {successMsg && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border p-3 text-sm"
          style={{ borderColor: 'var(--success)', backgroundColor: 'var(--success-bg)', color: 'var(--success)' }}>
          <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
          {successMsg}
        </div>
      )}

      {showCreate && (
        <div className="mb-4">
          <CreateSuppressionForm
            onSuccess={() => {
              setShowCreate(false);
              queryClient.invalidateQueries({ queryKey: ['suppressions'] });
              setSuccessMsg('Suppression rule created');
              setTimeout(() => setSuccessMsg(null), 3000);
            }}
            onCancel={() => setShowCreate(false)}
          />
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
        </div>
      ) : isError ? (
        <div className="cv-container p-8 flex flex-col items-center gap-3 text-center">
          <AlertTriangle className="h-8 w-8" style={{ color: 'var(--warning)' }} />
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Could not load suppression rules</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Retry</Button>
        </div>
      ) : rules.length === 0 ? (
        <div className="cv-container p-12 flex flex-col items-center gap-3 text-center">
          <ShieldOff className="h-10 w-10" style={{ color: 'var(--text-tertiary)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>No suppression rules</h3>
          <p className="text-sm max-w-sm" style={{ color: 'var(--text-secondary)' }}>
            Create rules to automatically suppress findings that match criteria like rule ID, resource tags, account, or region.
          </p>
          <Button className="gap-2 mt-2" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4" />
            New Rule
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map((rule) => (
            <div key={rule.id} className="cv-container p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {rule.rule_id && (
                      <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-mono"
                        style={{ backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}>
                        rule: {rule.rule_id}
                      </span>
                    )}
                    {rule.account_id && (
                      <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-mono"
                        style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                        account: {rule.account_id}
                      </span>
                    )}
                    {rule.region && (
                      <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-mono"
                        style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                        region: {rule.region}
                      </span>
                    )}
                    {rule.resource_tag_key && (
                      <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-mono"
                        style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                        tag: {rule.resource_tag_key}={rule.resource_tag_value}
                      </span>
                    )}
                    {!rule.rule_id && !rule.account_id && !rule.region && !rule.resource_tag_key && (
                      <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Matches all findings</span>
                    )}
                  </div>
                  {rule.reason && (
                    <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{rule.reason}</p>
                  )}
                  <div className="flex items-center gap-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    <span>Created {new Date(rule.created_at).toLocaleDateString()}</span>
                    {rule.expires_at && (
                      <span>· Expires {new Date(rule.expires_at).toLocaleDateString()}</span>
                    )}
                    {!rule.expires_at && <span>· Never expires</span>}
                    <span className="inline-flex items-center gap-1"
                      style={{ color: rule.is_active ? 'var(--success)' : 'var(--text-tertiary)' }}>
                      <span className="h-1.5 w-1.5 rounded-full"
                        style={{ backgroundColor: rule.is_active ? 'var(--success)' : 'var(--text-tertiary)' }} />
                      {rule.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => { if (confirm('Delete this suppression rule?')) deleteMutation.mutate(rule.id); }}
                  disabled={deleteMutation.isPending}
                >
                  {deleteMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
