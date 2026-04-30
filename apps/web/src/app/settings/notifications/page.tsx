'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { Button } from '@/components/ui/button';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bell, Plus, Trash2, Play, CheckCircle2, XCircle,
  Loader2, AlertTriangle, X,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

type ChannelType = 'slack' | 'webhook';

interface NotificationChannel {
  id: string;
  name: string;
  type: ChannelType;
  config: Record<string, string>;
  severity_filter: string[];
  active: boolean;
  created_at: string;
}

const SEVERITY_OPTIONS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as const;

const BREADCRUMBS = [
  { text: 'Home', href: '/console' },
  { text: 'Settings' },
  { text: 'Notifications' },
];

// ─── API helpers ──────────────────────────────────────────────────────────────

async function fetchChannels(): Promise<NotificationChannel[]> {
  const res = await fetch('/api/v1/notifications/channels', {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to fetch channels');
  const data = await res.json();
  return data.channels ?? data ?? [];
}

async function createChannel(payload: Omit<NotificationChannel, 'id' | 'created_at'>): Promise<NotificationChannel> {
  const res = await fetch('/api/v1/notifications/channels', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to create channel');
  return res.json();
}

async function deleteChannel(id: string): Promise<void> {
  const res = await fetch(`/api/v1/notifications/channels/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to delete channel');
}

async function testChannel(channelId: string): Promise<{ success: boolean; error?: string }> {
  const res = await fetch('/api/v1/notifications/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ channel_id: channelId }),
  });
  if (!res.ok) throw new Error('Failed to test channel');
  return res.json();
}

// ─── Type badge ───────────────────────────────────────────────────────────────

function TypeBadge({ type }: { type: ChannelType }) {
  const isSlack = type === 'slack';
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
      style={{
        backgroundColor: isSlack ? 'var(--accent-dim)' : 'var(--medium-dim)',
        color: isSlack ? 'var(--accent)' : 'var(--medium)',
      }}
    >
      {isSlack ? '🔔' : '🔗'} {isSlack ? 'Slack' : 'Webhook'}
    </span>
  );
}

// ─── Add channel form ─────────────────────────────────────────────────────────

function AddChannelForm({ onSuccess }: { onSuccess: () => void }) {
  const [name, setName] = React.useState('');
  const [type, setType] = React.useState<ChannelType>('slack');
  const [webhookUrl, setWebhookUrl] = React.useState('');
  const [webhookSecret, setWebhookSecret] = React.useState('');
  const [severities, setSeverities] = React.useState<Set<string>>(new Set(['CRITICAL', 'HIGH']));
  const [error, setError] = React.useState<string | null>(null);

  const queryClient = useQueryClient();
  const createMutation = useMutation({
    mutationFn: createChannel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications', 'channels'] });
      setName(''); setWebhookUrl(''); setWebhookSecret('');
      setSeverities(new Set(['CRITICAL', 'HIGH']));
      setError(null);
      onSuccess();
    },
    onError: (e: Error) => setError(e.message),
  });

  const toggleSeverity = (sev: string) => {
    setSeverities(prev => {
      const next = new Set(prev);
      if (next.has(sev)) next.delete(sev); else next.add(sev);
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !webhookUrl.trim()) {
      setError('Name and URL are required');
      return;
    }
    const config: Record<string, string> = type === 'slack'
      ? { webhook_url: webhookUrl }
      : { url: webhookUrl, ...(webhookSecret ? { secret: webhookSecret } : {}) };

    createMutation.mutate({
      name: name.trim(),
      type,
      config,
      severity_filter: Array.from(severities),
      active: true,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="cv-container p-6 space-y-4">
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Add Notification Channel</h3>

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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>Channel Name</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="e.g. Security Alerts"
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1"
            style={{
              borderColor: 'var(--border-default)',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
            }}
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>Type</label>
          <select
            value={type}
            onChange={e => setType(e.target.value as ChannelType)}
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1"
            style={{
              borderColor: 'var(--border-default)',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
            }}
          >
            <option value="slack">Slack</option>
            <option value="webhook">Generic Webhook</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
          {type === 'slack' ? 'Slack Webhook URL' : 'Webhook URL'}
        </label>
        <input
          type="url"
          value={webhookUrl}
          onChange={e => setWebhookUrl(e.target.value)}
          placeholder={type === 'slack' ? 'https://hooks.slack.com/services/...' : 'https://your-endpoint.com/webhook'}
          className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1"
          style={{
            borderColor: 'var(--border-default)',
            backgroundColor: 'var(--bg-surface)',
            color: 'var(--text-primary)',
          }}
        />
      </div>

      {type === 'webhook' && (
        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
            Secret (optional — used for HMAC signature)
          </label>
          <input
            type="password"
            value={webhookSecret}
            onChange={e => setWebhookSecret(e.target.value)}
            placeholder="Signing secret"
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1"
            style={{
              borderColor: 'var(--border-default)',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
            }}
          />
        </div>
      )}

      <div>
        <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Severity Filter</label>
        <div className="flex flex-wrap gap-2">
          {SEVERITY_OPTIONS.map(sev => (
            <label key={sev} className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={severities.has(sev)}
                onChange={() => toggleSeverity(sev)}
                className="h-3.5 w-3.5 rounded"
                style={{ borderColor: 'var(--border-default)' }}
              />
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{sev}</span>
            </label>
          ))}
        </div>
      </div>

      <Button type="submit" className="gap-2" disabled={createMutation.isPending}>
        {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
        Add Channel
      </Button>
    </form>
  );
}

// ─── Channel card ─────────────────────────────────────────────────────────────

function ChannelCard({ channel }: { channel: NotificationChannel }) {
  const queryClient = useQueryClient();
  const [testResult, setTestResult] = React.useState<{ success: boolean; error?: string } | null>(null);
  const [testing, setTesting] = React.useState(false);
  const [deleteHover, setDeleteHover] = React.useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => deleteChannel(channel.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications', 'channels'] }),
  });

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testChannel(channel.id);
      setTestResult(result);
    } catch (e) {
      setTestResult({ success: false, error: e instanceof Error ? e.message : 'Test failed' });
    } finally {
      setTesting(false);
    }
  };

  const handleDelete = () => {
    if (confirm(`Delete channel "${channel.name}"?`)) {
      deleteMutation.mutate();
    }
  };

  return (
    <div className="cv-container p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{channel.name}</span>
            <TypeBadge type={channel.type} />
            {channel.active ? (
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-semibold"
                style={{ backgroundColor: 'var(--success-dim)', color: 'var(--success)' }}
              >
                Active
              </span>
            ) : (
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-semibold"
                style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-tertiary)' }}
              >
                Inactive
              </span>
            )}
          </div>
          <div className="text-xs mb-2" style={{ color: 'var(--text-tertiary)' }}>
            Severity: {channel.severity_filter.join(', ') || 'All'}
          </div>
          {testResult && (
            <div
              className="flex items-center gap-1.5 text-xs mt-2"
              style={{ color: testResult.success ? 'var(--success)' : 'var(--critical)' }}
            >
              {testResult.success
                ? <><CheckCircle2 className="h-3.5 w-3.5" /> Test successful</>
                : <><XCircle className="h-3.5 w-3.5" /> {testResult.error ?? 'Test failed'}</>
              }
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" onClick={handleTest} disabled={testing}>
            {testing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
            Test
          </Button>
          <button
            className="h-8 w-8 p-0 flex items-center justify-center rounded-md transition-colors"
            style={{
              color: deleteHover ? 'var(--critical)' : 'var(--text-tertiary)',
              backgroundColor: deleteHover ? 'var(--critical-dim)' : 'transparent',
            }}
            onMouseEnter={() => setDeleteHover(true)}
            onMouseLeave={() => setDeleteHover(false)}
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function NotificationsPage() {
  const [showForm, setShowForm] = React.useState(false);

  React.useEffect(() => {
    document.title = 'Notifications - Settings - CloudVisor';
  }, []);

  const { data: channels = [], isLoading, isError } = useQuery({
    queryKey: ['notifications', 'channels'],
    queryFn: fetchChannels,
    staleTime: 60_000,
  });

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={BREADCRUMBS}>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Notifications</h1>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Configure alert channels for security findings
              </p>
            </div>
            <Button onClick={() => setShowForm(v => !v)} className="gap-2">
              {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
              {showForm ? 'Cancel' : 'Add Channel'}
            </Button>
          </div>

          {/* Add channel form */}
          {showForm && <AddChannelForm onSuccess={() => setShowForm(false)} />}

          {/* Channel list */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          ) : isError ? (
            <div className="cv-container p-6 flex flex-col items-center justify-center gap-3 text-center">
              <AlertTriangle className="h-8 w-8" style={{ color: 'var(--warning)' }} />
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Could not load notification channels. The notifications API may not be configured yet.
              </p>
            </div>
          ) : channels.length === 0 ? (
            <div className="cv-container p-12 flex flex-col items-center justify-center gap-3 text-center">
              <Bell className="h-10 w-10" style={{ color: 'var(--text-tertiary)' }} />
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>No channels configured</h3>
              <p className="text-sm max-w-sm" style={{ color: 'var(--text-secondary)' }}>
                Add a Slack or webhook channel to receive alerts when critical findings are detected.
              </p>
              <Button onClick={() => setShowForm(true)} className="gap-2 mt-2">
                <Plus className="h-4 w-4" />
                Add Channel
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {channels.map(channel => (
                <ChannelCard key={channel.id} channel={channel} />
              ))}
            </div>
          )}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
