'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Webhook, Plus, Trash2, Loader2, AlertTriangle, CheckCircle2, X, Copy } from 'lucide-react';
import { getCsrfToken } from '@/lib/csrf';

const GW = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8080';

/**
 * CSRF-safe fetch through the API gateway.
 * Authentication: HttpOnly cookies via credentials: 'include'
 * Tokens are NEVER stored in or read from localStorage.
 */
function gwFetch(path: string, options: RequestInit = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  // CSRF protection for state-changing requests
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) headers['X-CSRF-Token'] = csrf;
  }

  return fetch(`${GW}${path}`, {
    credentials: 'include',
    headers,
    ...options,
  }).then(r => {
    if (r.ok || r.status === 204) return r.status === 204 ? null : r.json();
    return r.json().then(e => Promise.reject(new Error(e.detail || `HTTP ${r.status}`)));
  });
}

const webhooksAPI = {
  list: () => gwFetch('/v1/webhooks'),
  create: (data: object) => gwFetch('/v1/webhooks', { method: 'POST', body: JSON.stringify(data) }),
  delete: (id: string) => gwFetch(`/v1/webhooks/${id}`, { method: 'DELETE' }),
};

const EVENT_OPTIONS = [
  'finding.created', 'finding.updated', 'finding.resolved',
  'incident.created', 'incident.updated',
  'scan.completed', 'connector.health_changed',
];

function CreateWebhookForm({ onSuccess, onCancel }: { onSuccess: () => void; onCancel: () => void }) {
  const [form, setForm] = React.useState({
    name: '',
    url: '',
    secret: '',
    events: new Set<string>(),
    severity_filter: new Set<string>(),
  });
  const [error, setError] = React.useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () => webhooksAPI.create({
      name: form.name,
      url: form.url,
      secret: form.secret || undefined,
      events: form.events.size > 0 ? Array.from(form.events) : [],
      severity_filter: form.severity_filter.size > 0 ? Array.from(form.severity_filter) : [],
      is_active: true,
    }),
    onSuccess: () => { setError(null); onSuccess(); },
    onError: (e: Error) => setError(e.message),
  });

  const toggleEvent = (ev: string) => {
    setForm(p => {
      const next = new Set(p.events);
      next.has(ev) ? next.delete(ev) : next.add(ev);
      return { ...p, events: next };
    });
  };

  const toggleSeverity = (sev: string) => {
    setForm(p => {
      const next = new Set(p.severity_filter);
      next.has(sev) ? next.delete(sev) : next.add(sev);
      return { ...p, severity_filter: next };
    });
  };

  return (
    <div className="cv-container p-5 space-y-4">
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Register Webhook</h3>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border p-3 text-sm"
          style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}>
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Name *</label>
          <input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
            placeholder="e.g. SIEM Integration"
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>HTTPS URL *</label>
          <input type="url" value={form.url} onChange={e => setForm(p => ({ ...p, url: e.target.value }))}
            placeholder="https://your-endpoint.com/webhook"
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
            Secret (optional — used for HMAC-SHA256 signature)
          </label>
          <input type="password" value={form.secret} onChange={e => setForm(p => ({ ...p, secret: e.target.value }))}
            placeholder="Min 16 characters"
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
          <p className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
            CloudVisor will include <code>X-CloudVisor-Signature: sha256=&lt;hmac&gt;</code> on every delivery.
          </p>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
          Events (empty = all events)
        </label>
        <div className="flex flex-wrap gap-2">
          {EVENT_OPTIONS.map(ev => (
            <label key={ev} className="flex items-center gap-1.5 cursor-pointer">
              <input type="checkbox" checked={form.events.has(ev)} onChange={() => toggleEvent(ev)} className="h-3.5 w-3.5 rounded" />
              <span className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>{ev}</span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
          Severity filter (empty = all severities)
        </label>
        <div className="flex flex-wrap gap-2">
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'].map(sev => (
            <label key={sev} className="flex items-center gap-1.5 cursor-pointer">
              <input type="checkbox" checked={form.severity_filter.has(sev)} onChange={() => toggleSeverity(sev)} className="h-3.5 w-3.5 rounded" />
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{sev}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="flex gap-3 pt-1">
        <Button onClick={() => createMutation.mutate()} disabled={!form.name || !form.url || createMutation.isPending} className="gap-2">
          {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Register
        </Button>
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  );
}

export default function WebhooksPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = React.useState(false);
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  React.useEffect(() => { document.title = 'Webhooks - Settings - CloudVisor'; }, []);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['webhooks'],
    queryFn: webhooksAPI.list,
    select: (d) => (d?.data ?? d ?? []) as any[],
  });

  const deleteMutation = useMutation({
    mutationFn: webhooksAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      setSuccessMsg('Webhook removed');
      setTimeout(() => setSuccessMsg(null), 3000);
    },
  });

  const webhooks = data ?? [];

  return (
    <>
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Webhooks</h1>
          <Button className="gap-2" onClick={() => setShowCreate(v => !v)}>
            {showCreate ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showCreate ? 'Cancel' : 'Register Webhook'}
          </Button>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Receive real-time event payloads at your HTTPS endpoint. Payloads are signed with HMAC-SHA256.
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
          <CreateWebhookForm
            onSuccess={() => {
              setShowCreate(false);
              queryClient.invalidateQueries({ queryKey: ['webhooks'] });
              setSuccessMsg('Webhook registered');
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
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Could not load webhooks</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Retry</Button>
        </div>
      ) : webhooks.length === 0 ? (
        <div className="cv-container p-12 flex flex-col items-center gap-3 text-center">
          <Webhook className="h-10 w-10" style={{ color: 'var(--text-tertiary)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>No webhooks registered</h3>
          <p className="text-sm max-w-sm" style={{ color: 'var(--text-secondary)' }}>
            Register a webhook to receive real-time event notifications at your HTTPS endpoint.
          </p>
          <Button className="gap-2 mt-2" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4" />
            Register Webhook
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {webhooks.map((wh: any) => (
            <div key={wh.id} className="cv-container p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{wh.name}</span>
                    <span className="inline-flex items-center gap-1 text-xs"
                      style={{ color: wh.is_active ? 'var(--success)' : 'var(--text-tertiary)' }}>
                      <span className="h-1.5 w-1.5 rounded-full"
                        style={{ backgroundColor: wh.is_active ? 'var(--success)' : 'var(--text-tertiary)' }} />
                      {wh.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <code className="text-xs font-mono truncate max-w-xs" style={{ color: 'var(--text-secondary)' }}>
                      {wh.url}
                    </code>
                    <button onClick={() => navigator.clipboard.writeText(wh.url)}
                      className="flex-shrink-0" style={{ color: 'var(--text-tertiary)' }}>
                      <Copy className="h-3 w-3" />
                    </button>
                  </div>
                  {wh.events?.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {wh.events.map((ev: string) => (
                        <span key={ev} className="text-xs font-mono rounded px-1.5 py-0.5"
                          style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-tertiary)' }}>
                          {ev}
                        </span>
                      ))}
                    </div>
                  )}
                  {wh.events?.length === 0 && (
                    <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>All events</span>
                  )}
                </div>
                <Button variant="outline" size="sm"
                  onClick={() => { if (confirm(`Remove webhook "${wh.name}"?`)) deleteMutation.mutate(wh.id); }}
                  disabled={deleteMutation.isPending}>
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
