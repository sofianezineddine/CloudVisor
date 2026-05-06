'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { Key, Plus, AlertTriangle, Loader2, Copy, Trash2, Eye, EyeOff } from 'lucide-react';

// Mock data for demonstration
const mockApiKeys = [
  {
    id: '1',
    name: 'Production API Key',
    key: 'cv_prod_1234567890abcdef',
    created: '2024-01-15',
    lastUsed: '2024-01-20',
    permissions: ['read', 'write']
  },
  {
    id: '2', 
    name: 'Development Key',
    key: 'cv_dev_abcdef1234567890',
    created: '2024-01-10',
    lastUsed: '2024-01-18',
    permissions: ['read']
  }
];

export default function ApiKeysPage() {
  const [showKeys, setShowKeys] = React.useState<Record<string, boolean>>({});

  React.useEffect(() => {
    document.title = 'API Keys - Settings - CloudVisor';
  }, []);

  const toggleKeyVisibility = (keyId: string) => {
    setShowKeys(prev => ({ ...prev, [keyId]: !prev[keyId] }));
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>API Keys</h1>
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Create API Key
          </Button>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Manage programmatic access to the CloudVisor API
        </p>
      </div>

      {/* API Keys List */}
      <div className="space-y-4">
        {mockApiKeys.map((apiKey) => (
          <div key={apiKey.id} className="rounded-lg border p-6" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ backgroundColor: 'var(--accent-dim)' }}>
                  <Key className="h-5 w-5" style={{ color: 'var(--accent)' }} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{apiKey.name}</h3>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    Created {new Date(apiKey.created).toLocaleDateString()} • Last used {new Date(apiKey.lastUsed).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => toggleKeyVisibility(apiKey.id)}>
                  {showKeys[apiKey.id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
                <Button variant="outline" size="sm" onClick={() => copyToClipboard(apiKey.key)}>
                  <Copy className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm">
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* API Key */}
            <div className="mb-4">
              <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>API Key</label>
              <div className="mt-1 flex items-center gap-2">
                <code className="flex-1 rounded px-3 py-2 text-sm font-mono" style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)' }}>
                  {showKeys[apiKey.id] ? apiKey.key : '•'.repeat(apiKey.key.length)}
                </code>
              </div>
            </div>

            {/* Permissions */}
            <div>
              <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Permissions</label>
              <div className="mt-1 flex gap-2">
                {apiKey.permissions.map((permission) => (
                  <span
                    key={permission}
                    className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize"
                    style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}
                  >
                    {permission}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}

        {/* Empty state for when no API keys exist */}
        {mockApiKeys.length === 0 && (
          <div className="rounded-lg border p-8 flex flex-col items-center justify-center gap-3 text-center" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
            <Key className="h-8 w-8" style={{ color: 'var(--text-tertiary)' }} />
            <div>
              <h3 className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>No API keys yet</h3>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Create your first API key to start using the CloudVisor API programmatically.
              </p>
            </div>
            <Button className="gap-2 mt-2">
              <Plus className="h-4 w-4" />
              Create API Key
            </Button>
          </div>
        )}
      </div>
    </>
  );
}