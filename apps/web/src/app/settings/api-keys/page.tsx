'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { Button } from '@/components/ui/button';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Key, Plus, Trash2, Copy, Check, Loader2, AlertTriangle, X, Eye, EyeOff,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ApiKey {
  id: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
  scopes: string[];
  key_prefix?: string;
}

interface CreatedApiKey extends ApiKey {
  key: string; // full key — only shown once
}

const AVAILABLE_SCOPES = [
  { value: 'findings:read', label: 'Read Findings' },
  { value: 'findings:write', label: 'Write Findings' },
  { value: 'assets:read', label: 'Read Assets' },
  { value: 'accounts:read', label: 'Read Accounts' },
  { value: 'accounts:write', label: 'Write Accounts' },
  { value: 'reports:read', label: 'Read Reports' },
];

const BREADCRUMBS = [
  { text: 'Home', href: '/console' },
  { text: 'Settings' },
  { text: 'API Keys' },
];

// ─── API helpers ──────────────────────────────────────────────────────────────

async function fetchApiKeys(): Promise<ApiKey[]> {
  const res = await fetch('/api/v1/auth/api-keys', { credentials: 'include' });
  if (!res.ok) throw new Error('Failed to fetch API keys');
  const data = await res.json();
  return data.keys ?? data ?? [];
}

async function createApiKey(payload: { name: string; scopes: string[] }): Promise<CreatedApiKey> {
  const res = await fetch('/api/v1/auth/api-keys', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to create API key');
  return res.json();
}

async function revokeApiKey(id: string): Promise<void> {
  const res = await fetch(`/api/v1/auth/api-keys/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to revoke API key');
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function timeAgo(iso: string | null): string {
  if (!iso) return 'Never';
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  return `${days}d ago`;
}

// ─── Copy button ──────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = React.useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors"
      style={{
        borderColor: 'var(--border-default)',
        backgroundColor: 'var(--bg-elevated)',
        color: 'var(--text-secondary)',
      }}
    >
      {copied
        ? <Check className="h-3.5 w-3.5" style={{ color: 'var(--success)' }} />
        : <Copy className="h-3.5 w-3.5" />
      }
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

// ─── New key dialog ───────────────────────────────────────────────────────────

function NewKeyDialog({ apiKey, onClose }: { apiKey: CreatedApiKey; onClose: () => void }) {
  const [visible, setVisible] = React.useState(false);

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div
        className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border shadow-2xl"
        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
      >
        <div
          className="flex items-center justify-between border-b px-6 py-4"
          style={{ borderColor: 'var(--border-default)' }}
        >
          <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>API Key Created</h3>
          <button
            onClick={onClose}
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-tertiary)')}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div
            className="flex items-start gap-3 rounded-lg border p-4"
            style={{ borderColor: 'var(--warning)', backgroundColor: 'var(--warning-dim)' }}
          >
            <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" style={{ color: 'var(--warning)' }} />
            <p className="text-sm" style={{ color: 'var(--text-primary)' }}>
              This key will not be shown again. Copy it now and store it securely.
            </p>
          </div>
          <div>
            <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Your API Key</label>
            <div className="flex items-center gap-2">
              <div
                className="flex-1 rounded-md border px-3 py-2 font-mono text-sm overflow-hidden"
                style={{
                  borderColor: 'var(--border-default)',
                  backgroundColor: 'var(--bg-elevated)',
                  color: 'var(--text-primary)',
                }}
              >
                {visible ? apiKey.key : '•'.repeat(Math.min(apiKey.key.length, 40))}
              </div>
              <button
                onClick={() => setVisible(v => !v)}
                className="p-2"
                style={{ color: 'var(--text-tertiary)' }}
                onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
                onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-tertiary)')}
              >
                {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
              <CopyButton text={apiKey.key} />
            </div>
          </div>
          <Button onClick={onClose} className="w-full">Done</Button>
        </div>
      </div>
    </>
  );
}

// ─── Create key modal ─────────────────────────────────────────────────────────

function CreateKeyModal({ onClose, onCreated }: { onClose: () => void; onCreated: (key: CreatedApiKey) => void }) {
  const [name, setName] = React.useState('');
  const [scopes, setScopes] = React.useState<Set<string>>(new Set(['findings:read']));
  const [error, setError] = React.useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: createApiKey,
    onSuccess: (data) => onCreated(data),
    onError: (e: Error) => setError(e.message),
  });

  const toggleScope = (scope: string) => {
    setScopes(prev => {
      const next = new Set(prev);
      if (next.has(scope)) next.delete(scope); else next.add(scope);
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) { setError('Name is required'); return; }
    createMutation.mutate({ name: name.trim(), scopes: Array.from(scopes) });
  };

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div
        className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border shadow-2xl"
        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
      >
        <div
          className="flex items-center justify-between border-b px-6 py-4"
          style={{ borderColor: 'var(--border-default)' }}
        >
          <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Create API Key</h3>
          <button
            onClick={onClose}
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-tertiary)')}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div
              className="flex items-center gap-2 rounded-lg border p-3 text-sm"
              style={{
                borderColor: 'var(--critical)',
                backgroundColor: 'var(--critical-dim)',
                color: 'var(--critical)',
              }}
            >
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>Key Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. CI/CD Pipeline"
              className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1"
              style={{
                borderColor: 'var(--border-default)',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-primary)',
              }}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>Scopes</label>
            <div className="space-y-2">
              {AVAILABLE_SCOPES.map(scope => (
                <label key={scope.value} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={scopes.has(scope.value)}
                    onChange={() => toggleScope(scope.value)}
                    className="h-4 w-4 rounded"
                    style={{ borderColor: 'var(--border-default)' }}
                  />
                  <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{scope.label}</span>
                  <span className="font-mono text-xs" style={{ color: 'var(--text-tertiary)' }}>{scope.value}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">Cancel</Button>
            <Button type="submit" className="flex-1 gap-2" disabled={createMutation.isPending}>
              {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Key className="h-4 w-4" />}
              Create Key
            </Button>
          </div>
        </form>
      </div>
    </>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function ApiKeysPage() {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [newKey, setNewKey] = React.useState<CreatedApiKey | null>(null);

  React.useEffect(() => {
    document.title = 'API Keys - Settings - CloudVisor';
  }, []);

  const { data: keys = [], isLoading, isError } = useQuery({
    queryKey: ['auth', 'api-keys'],
    queryFn: fetchApiKeys,
    staleTime: 60_000,
  });

  const revokeMutation = useMutation({
    mutationFn: revokeApiKey,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['auth', 'api-keys'] }),
  });

  const handleRevoke = (id: string, name: string) => {
    if (confirm(`Revoke API key "${name}"? This action cannot be undone.`)) {
      revokeMutation.mutate(id);
    }
  };

  const handleCreated = (key: CreatedApiKey) => {
    setShowCreateModal(false);
    setNewKey(key);
    queryClient.invalidateQueries({ queryKey: ['auth', 'api-keys'] });
  };

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={BREADCRUMBS}>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>API Keys</h1>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Manage programmatic access to the CloudVisor API
              </p>
            </div>
            <Button onClick={() => setShowCreateModal(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Create API Key
            </Button>
          </div>

          {/* Keys list */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          ) : isError ? (
            <div className="cv-container p-6 flex flex-col items-center justify-center gap-3 text-center">
              <AlertTriangle className="h-8 w-8" style={{ color: 'var(--warning)' }} />
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Could not load API keys. The API keys endpoint may not be configured yet.
              </p>
            </div>
          ) : keys.length === 0 ? (
            <div className="cv-container p-12 flex flex-col items-center justify-center gap-3 text-center">
              <Key className="h-10 w-10" style={{ color: 'var(--text-tertiary)' }} />
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>No API keys</h3>
              <p className="text-sm max-w-sm" style={{ color: 'var(--text-secondary)' }}>
                Create an API key to access CloudVisor programmatically from CI/CD pipelines or scripts.
              </p>
              <Button onClick={() => setShowCreateModal(true)} className="gap-2 mt-2">
                <Plus className="h-4 w-4" />
                Create API Key
              </Button>
            </div>
          ) : (
            <div className="cv-container overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr
                    className="border-b"
                    style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}
                  >
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Created</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Last Used</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Scopes</th>
                    <th className="w-16 px-4 py-3" />
                  </tr>
                </thead>
                <tbody style={{ borderColor: 'var(--border-faint)' }} className="divide-y">
                  {keys.map(key => (
                    <TableRow
                      key={key.id}
                      apiKey={key}
                      onRevoke={handleRevoke}
                      revoking={revokeMutation.isPending}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Modals */}
        {showCreateModal && (
          <CreateKeyModal onClose={() => setShowCreateModal(false)} onCreated={handleCreated} />
        )}
        {newKey && (
          <NewKeyDialog apiKey={newKey} onClose={() => setNewKey(null)} />
        )}
      </AppLayout>
    </ProtectedRoute>
  );
}

function TableRow({
  apiKey: key,
  onRevoke,
  revoking,
}: {
  apiKey: ApiKey;
  onRevoke: (id: string, name: string) => void;
  revoking: boolean;
}) {
  const [hover, setHover] = React.useState(false);
  const [deleteHover, setDeleteHover] = React.useState(false);

  return (
    <tr
      style={{ backgroundColor: hover ? 'var(--bg-elevated)' : 'transparent' }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <Key className="h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
          <div>
            <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{key.name}</div>
            {key.key_prefix && (
              <div className="font-mono text-xs" style={{ color: 'var(--text-tertiary)' }}>{key.key_prefix}...</div>
            )}
          </div>
        </div>
      </td>
      <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
        {formatDate(key.created_at)}
      </td>
      <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-tertiary)' }}>
        {timeAgo(key.last_used_at)}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {key.scopes.map(scope => (
            <span
              key={scope}
              className="rounded px-1.5 py-0.5 font-mono text-[10px]"
              style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-tertiary)' }}
            >
              {scope}
            </span>
          ))}
        </div>
      </td>
      <td className="px-4 py-3">
        <button
          className="h-8 w-8 p-0 flex items-center justify-center rounded-md transition-colors"
          style={{
            color: deleteHover ? 'var(--critical)' : 'var(--text-tertiary)',
            backgroundColor: deleteHover ? 'var(--critical-dim)' : 'transparent',
          }}
          onMouseEnter={() => setDeleteHover(true)}
          onMouseLeave={() => setDeleteHover(false)}
          onClick={() => onRevoke(key.id, key.name)}
          disabled={revoking}
        >
          {revoking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
        </button>
      </td>
    </tr>
  );
}
