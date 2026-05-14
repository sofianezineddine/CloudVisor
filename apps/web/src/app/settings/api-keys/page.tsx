'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Key, Plus, Loader2, Copy, Trash2, Eye, EyeOff, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { authAPI } from '@/lib/api/auth';

interface ApiKey {
  id: string;
  name: string;
  scopes: string[];
  last_used_at: string | null;
  created_at: string;
  expires_at: string | null;
  is_active: boolean;
}

export default function ApiKeysPage() {
  const queryClient = useQueryClient();
  const [showKeys, setShowKeys] = React.useState<Record<string, boolean>>({});
  const [showCreate, setShowCreate] = React.useState(false);
  const [newKeyName, setNewKeyName] = React.useState('');
  const [newKeyValue, setNewKeyValue] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    document.title = 'API Keys - Settings - CloudVisor';
  }, []);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => authAPI.getApiKeys(),
    select: (d: any) => (d?.keys ?? []) as ApiKey[],
  });

  const createMutation = useMutation({
    mutationFn: (name: string) =>
      authAPI.createApiKey({ name, scopes: ['findings:read', 'assets:read'] }),
    onSuccess: (result: any) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setNewKeyValue(result?.key ?? null);
      setShowCreate(false);
      setNewKeyName('');
    },
    onError: (e: Error) => setError(e.message),
  });

  const rotateMutation = useMutation({
    mutationFn: (keyId: string) => authAPI.rotateApiKey(keyId),
    onSuccess: (result: any) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setNewKeyValue(result?.key ?? null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const revokeMutation = useMutation({
    mutationFn: (keyId: string) => authAPI.revokeApiKey(keyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-keys'] }),
    onError: (e: Error) => setError(e.message),
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const apiKeys = data ?? [];

  return (
    <>
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>API Keys</h1>
          <Button className="gap-2" onClick={() => setShowCreate(v => !v)}>
            <Plus className="h-4 w-4" />
            Create API Key
          </Button>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Manage programmatic access to the CloudVisor API
        </p>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border p-3 text-sm"
          style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}>
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-xs underline">Dismiss</button>
        </div>
      )}

      {/* New key revealed */}
      {newKeyValue && (
        <div className="mb-4 rounded-lg border p-4"
          style={{ borderColor: 'var(--success)', backgroundColor: 'var(--success-bg)' }}>
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
            <span className="text-sm font-semibold" style={{ color: 'var(--success)' }}>
              API key created — copy it now, it won't be shown again
            </span>
          </div>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded px-3 py-2 text-sm font-mono break-all"
              style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)' }}>
              {newKeyValue}
            </code>
            <Button variant="outline" size="sm" onClick={() => copyToClipboard(newKeyValue)}>
              <Copy className="h-4 w-4" />
            </Button>
          </div>
          <button onClick={() => setNewKeyValue(null)} className="mt-2 text-xs underline"
            style={{ color: 'var(--text-tertiary)' }}>Dismiss</button>
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className="mb-4 rounded-lg border p-4"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>New API Key</h3>
          <div className="flex gap-3">
            <input
              type="text"
              value={newKeyName}
              onChange={e => setNewKeyName(e.target.value)}
              placeholder="Key name (e.g. CI/CD Pipeline)"
              className="flex-1 rounded-md border px-3 py-2 text-sm focus:outline-none"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-base)', color: 'var(--text-primary)' }}
            />
            <Button
              onClick={() => { if (newKeyName.trim()) createMutation.mutate(newKeyName.trim()); }}
              disabled={!newKeyName.trim() || createMutation.isPending}
              className="gap-2"
            >
              {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Create
            </Button>
            <Button variant="outline" onClick={() => { setShowCreate(false); setNewKeyName(''); }}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Keys list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
        </div>
      ) : isError ? (
        <div className="rounded-lg border p-8 text-center"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <AlertTriangle className="h-8 w-8 mx-auto mb-3" style={{ color: 'var(--warning)' }} />
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Could not load API keys</p>
        </div>
      ) : apiKeys.length === 0 ? (
        <div className="rounded-lg border p-8 flex flex-col items-center justify-center gap-3 text-center"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <Key className="h-8 w-8" style={{ color: 'var(--text-tertiary)' }} />
          <div>
            <h3 className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>No API keys yet</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Create your first API key to start using the CloudVisor API programmatically.
            </p>
          </div>
          <Button className="gap-2 mt-2" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4" />
            Create API Key
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {apiKeys.map((apiKey) => (
            <div key={apiKey.id} className="rounded-lg border p-6"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg"
                    style={{ backgroundColor: 'var(--accent-dim)' }}>
                    <Key className="h-5 w-5" style={{ color: 'var(--accent)' }} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{apiKey.name}</h3>
                    <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      Created {new Date(apiKey.created_at).toLocaleDateString()}
                      {apiKey.last_used_at && ` · Last used ${new Date(apiKey.last_used_at).toLocaleDateString()}`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm"
                    onClick={() => setShowKeys(p => ({ ...p, [apiKey.id]: !p[apiKey.id] }))}>
                    {showKeys[apiKey.id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                  <Button variant="outline" size="sm"
                    onClick={() => copyToClipboard(apiKey.id)}
                    title="Copy key ID">
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm"
                    onClick={() => rotateMutation.mutate(apiKey.id)}
                    disabled={rotateMutation.isPending}
                    title="Rotate key">
                    {rotateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : '↻'}
                  </Button>
                  <Button variant="outline" size="sm"
                    onClick={() => { if (confirm(`Revoke "${apiKey.name}"?`)) revokeMutation.mutate(apiKey.id); }}
                    disabled={revokeMutation.isPending}>
                    {revokeMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                  </Button>
                </div>
              </div>

              <div className="mb-4">
                <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>API Key</label>
                <div className="mt-1 flex items-center gap-2">
                  <code className="flex-1 rounded px-3 py-2 text-sm font-mono"
                    style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)' }}>
                    {showKeys[apiKey.id] ? `cv_live_${'•'.repeat(8)}...` : '•'.repeat(32)}
                  </code>
                </div>
                <p className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  Key value is only shown once at creation. Rotate to get a new key.
                </p>
              </div>

              {apiKey.scopes?.length > 0 && (
                <div>
                  <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Scopes</label>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {apiKey.scopes.map((scope) => (
                      <span key={scope}
                        className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize"
                        style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                        {scope}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
