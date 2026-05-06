'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import {
  useNotificationChannels,
  useCreateChannel,
  useUpdateChannel,
  useDeleteChannel,
  useTestChannel,
} from '@/hooks/use-notifications';
import {
  Bell, Plus, Trash2, Play, CheckCircle2, XCircle, Edit2,
  Loader2, AlertTriangle, X, Mail, MessageSquare, Webhook,
} from 'lucide-react';

const SEVERITY_OPTIONS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as const;
const MODULE_OPTIONS = ['cspm', 'cwpp', 'cicd', 'ciem', 'kspm', 'dspm', 'cdr'] as const;

const CHANNEL_TYPES = [
  { value: 'slack', label: 'Slack', icon: '💬', description: 'Send alerts to Slack channels' },
  { value: 'email', label: 'Email', icon: '📧', description: 'Email notifications (CRITICAL/HIGH real-time)' },
  { value: 'jira', label: 'Jira', icon: '🎫', description: 'Auto-create Jira issues' },
  { value: 'pagerduty', label: 'PagerDuty', icon: '🚨', description: 'On-call escalation for CRITICAL' },
  { value: 'teams', label: 'Microsoft Teams', icon: '👥', description: 'Teams Adaptive Cards' },
  { value: 'webhook', label: 'Generic Webhook', icon: '🔗', description: 'Custom HTTPS endpoint' },
] as const;

// ─── Channel form ─────────────────────────────────────────────────────────────

interface ChannelFormProps {
  onSuccess: () => void;
  editingChannel?: any;
}

function ChannelForm({ onSuccess, editingChannel }: ChannelFormProps) {
  const [name, setName] = React.useState(editingChannel?.name || '');
  const [channelType, setChannelType] = React.useState(editingChannel?.channel_type || 'slack');
  const [config, setConfig] = React.useState<Record<string, string>>(editingChannel?.config || {});
  const [severities, setSeverities] = React.useState<Set<string>>(
    new Set(editingChannel?.severity_filter || ['CRITICAL', 'HIGH'])
  );
  const [modules, setModules] = React.useState<Set<string>>(
    new Set(editingChannel?.module_filter || [])
  );
  const [accounts, setAccounts] = React.useState<string>(
    editingChannel?.account_filter?.join(', ') || ''
  );
  const [tagKey, setTagKey] = React.useState('');
  const [tagValue, setTagValue] = React.useState('');
  const [tags, setTags] = React.useState<Record<string, string>>(editingChannel?.tag_filter || {});
  const [error, setError] = React.useState<string | null>(null);

  const createMutation = useCreateChannel();
  const updateMutation = useUpdateChannel();

  const toggleSeverity = (sev: string) => {
    setSeverities(prev => {
      const next = new Set(prev);
      if (next.has(sev)) next.delete(sev); else next.add(sev);
      return next;
    });
  };

  const toggleModule = (mod: string) => {
    setModules(prev => {
      const next = new Set(prev);
      if (next.has(mod)) next.delete(mod); else next.add(mod);
      return next;
    });
  };

  const addTag = () => {
    if (tagKey && tagValue) {
      setTags(prev => ({ ...prev, [tagKey]: tagValue }));
      setTagKey('');
      setTagValue('');
    }
  };

  const removeTag = (key: string) => {
    setTags(prev => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Channel name is required');
      return;
    }

    const data = {
      name: name.trim(),
      channel_type: channelType,
      config,
      severity_filter: Array.from(severities),
      module_filter: modules.size > 0 ? Array.from(modules) : undefined,
      account_filter: accounts ? accounts.split(',').map(a => a.trim()).filter(Boolean) : undefined,
      tag_filter: Object.keys(tags).length > 0 ? tags : undefined,
      is_active: true,
    };

    try {
      if (editingChannel) {
        await updateMutation.mutateAsync({ channelId: editingChannel.id, data });
      } else {
        await createMutation.mutateAsync(data);
      }
      setError(null);
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save channel');
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <form onSubmit={handleSubmit} className="cv-container p-6 space-y-5">
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
        {editingChannel ? 'Edit Channel' : 'Add Notification Channel'}
      </h3>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border p-3 text-sm" style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}>
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Basic info */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>Channel Name *</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="e.g. Security Alerts"
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>Channel Type *</label>
          <select
            value={channelType}
            onChange={e => setChannelType(e.target.value)}
            disabled={!!editingChannel}
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
          >
            {CHANNEL_TYPES.map(ct => (
              <option key={ct.value} value={ct.value}>{ct.icon} {ct.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Channel-specific config */}
      <div className="space-y-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Configuration</h4>
        
        {channelType === 'slack' && (
          <input
            type="url"
            value={config.webhook_url || ''}
            onChange={e => setConfig({ ...config, webhook_url: e.target.value })}
            placeholder="https://hooks.slack.com/services/..."
            className="w-full rounded-md border px-3 py-2 text-sm"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
          />
        )}

        {channelType === 'email' && (
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="SMTP Host" value={config.smtp_host || ''} onChange={e => setConfig({ ...config, smtp_host: e.target.value })} className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
            <input placeholder="SMTP Port" value={config.smtp_port || '587'} onChange={e => setConfig({ ...config, smtp_port: e.target.value })} className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
            <input placeholder="SMTP User" value={config.smtp_user || ''} onChange={e => setConfig({ ...config, smtp_user: e.target.value })} className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
            <input type="password" placeholder="SMTP Password" value={config.smtp_password || ''} onChange={e => setConfig({ ...config, smtp_password: e.target.value })} className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
            <input placeholder="From Email" value={config.from_email || ''} onChange={e => setConfig({ ...config, from_email: e.target.value })} className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
            <input placeholder="To Emails (comma-separated)" value={config.to_emails || ''} onChange={e => setConfig({ ...config, to_emails: e.target.value })} className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
          </div>
        )}

        {channelType === 'jira' && (
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Jira URL" value={config.url || ''} onChange={e => setConfig({ ...config, url: e.target.value })} className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
            <input placeholder="Email" value={config.email || ''} onChange={e => setConfig({ ...config, email: e.target.value })} className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
            <input type="password" placeholder="API Token" value={config.api_token || ''} onChange={e => setConfig({ ...config, api_token: e.target.value })} className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
            <input placeholder="Project Key" value={config.project_key || ''} onChange={e => setConfig({ ...config, project_key: e.target.value })} className="rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
          </div>
        )}

        {channelType === 'pagerduty' && (
          <input placeholder="Integration Key" value={config.integration_key || ''} onChange={e => setConfig({ ...config, integration_key: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
        )}

        {channelType === 'teams' && (
          <input type="url" placeholder="Teams Webhook URL" value={config.webhook_url || ''} onChange={e => setConfig({ ...config, webhook_url: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
        )}

        {channelType === 'webhook' && (
          <div className="space-y-2">
            <input type="url" placeholder="Webhook URL" value={config.url || ''} onChange={e => setConfig({ ...config, url: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
            <input type="password" placeholder="Secret (optional, for HMAC)" value={config.secret || ''} onChange={e => setConfig({ ...config, secret: e.target.value })} className="w-full rounded-md border px-3 py-2 text-sm" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
          </div>
        )}
      </div>

      {/* Routing filters */}
      <div className="space-y-4">
        <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Routing Filters</h4>
        
        {/* Severity */}
        <div>
          <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Severity Filter</label>
          <div className="flex flex-wrap gap-2">
            {SEVERITY_OPTIONS.map(sev => (
              <label key={sev} className="flex items-center gap-1.5 cursor-pointer">
                <input type="checkbox" checked={severities.has(sev)} onChange={() => toggleSeverity(sev)} className="h-3.5 w-3.5 rounded" />
                <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{sev}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Modules */}
        <div>
          <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Module Filter (optional)</label>
          <div className="flex flex-wrap gap-2">
            {MODULE_OPTIONS.map(mod => (
              <label key={mod} className="flex items-center gap-1.5 cursor-pointer">
                <input type="checkbox" checked={modules.has(mod)} onChange={() => toggleModule(mod)} className="h-3.5 w-3.5 rounded" />
                <span className="text-xs uppercase" style={{ color: 'var(--text-secondary)' }}>{mod}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Accounts */}
        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>Account Filter (optional)</label>
          <input
            type="text"
            value={accounts}
            onChange={e => setAccounts(e.target.value)}
            placeholder="account-123, account-456 (comma-separated)"
            className="w-full rounded-md border px-3 py-2 text-sm"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>Tag Filter (optional)</label>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={tagKey}
              onChange={e => setTagKey(e.target.value)}
              placeholder="Key"
              className="flex-1 rounded-md border px-3 py-2 text-sm"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            />
            <input
              type="text"
              value={tagValue}
              onChange={e => setTagValue(e.target.value)}
              placeholder="Value"
              className="flex-1 rounded-md border px-3 py-2 text-sm"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            />
            <Button type="button" variant="outline" size="sm" onClick={addTag}>Add</Button>
          </div>
          {Object.keys(tags).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(tags).map(([k, v]) => (
                <span key={k} className="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs" style={{ borderColor: 'var(--accent)', backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}>
                  {k}={v}
                  <button type="button" onClick={() => removeTag(k)} className="ml-0.5 rounded-full p-0.5">
                    <X className="h-2.5 w-2.5" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <Button type="submit" className="gap-2" disabled={isPending}>
        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
        {editingChannel ? 'Update Channel' : 'Add Channel'}
      </Button>
    </form>
  );
}

// ─── Channel card ─────────────────────────────────────────────────────────────

function ChannelCard({ channel, onEdit }: { channel: any; onEdit: () => void }) {
  const deleteMutation = useDeleteChannel();
  const testMutation = useTestChannel();

  const handleTest = () => {
    testMutation.mutate({ channel_id: channel.id });
  };

  const handleDelete = () => {
    if (confirm(`Delete channel "${channel.name}"?`)) {
      deleteMutation.mutate(channel.id);
    }
  };

  const channelTypeInfo = CHANNEL_TYPES.find(ct => ct.value === channel.channel_type);

  return (
    <div className="cv-container p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{channel.name}</span>
            <span className="text-lg">{channelTypeInfo?.icon}</span>
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{channelTypeInfo?.label}</span>
          </div>
          <div className="text-xs space-y-1" style={{ color: 'var(--text-tertiary)' }}>
            <div>Severity: {channel.severity_filter?.join(', ') || 'All'}</div>
            {channel.module_filter?.length > 0 && <div>Modules: {channel.module_filter.join(', ')}</div>}
            {channel.account_filter?.length > 0 && <div>Accounts: {channel.account_filter.join(', ')}</div>}
          </div>
          {testMutation.data && (
            <div className="flex items-center gap-1.5 text-xs mt-2" style={{ color: testMutation.data.data.success ? 'var(--success)' : 'var(--critical)' }}>
              {testMutation.data.data.success ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
              {testMutation.data.data.message}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onEdit}>
            <Edit2 className="h-3 w-3" />
          </Button>
          <Button variant="outline" size="sm" onClick={handleTest} disabled={testMutation.isPending}>
            {testMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
          </Button>
          <Button variant="outline" size="sm" onClick={handleDelete} disabled={deleteMutation.isPending}>
            {deleteMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function NotificationsPage() {
  const [showForm, setShowForm] = React.useState(false);
  const [editingChannel, setEditingChannel] = React.useState<any>(null);

  React.useEffect(() => {
    document.title = 'Notifications - Settings - CloudVisor';
  }, []);

  const { data, isLoading, isError } = useNotificationChannels();
  const channels = data?.data || [];

  const handleEdit = (channel: any) => {
    setEditingChannel(channel);
    setShowForm(true);
  };

  const handleFormSuccess = () => {
    setShowForm(false);
    setEditingChannel(null);
  };

  return (
    <>
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Notifications</h1>
          <Button onClick={() => { setShowForm(v => !v); setEditingChannel(null); }} className="gap-2">
            {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showForm ? 'Cancel' : 'Add Channel'}
          </Button>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Configure alert channels with advanced routing rules
        </p>
      </div>

      <div className="space-y-6">

          {showForm && <ChannelForm onSuccess={handleFormSuccess} editingChannel={editingChannel} />}

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          ) : isError ? (
            <div className="cv-container p-6 flex flex-col items-center justify-center gap-3 text-center">
              <AlertTriangle className="h-8 w-8" style={{ color: 'var(--warning)' }} />
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Could not load notification channels
              </p>
            </div>
          ) : channels.length === 0 ? (
            <div className="cv-container p-12 flex flex-col items-center justify-center gap-3 text-center">
              <Bell className="h-10 w-10" style={{ color: 'var(--text-tertiary)' }} />
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>No channels configured</h3>
              <p className="text-sm max-w-sm" style={{ color: 'var(--text-secondary)' }}>
                Add notification channels to receive alerts via Slack, Email, Jira, PagerDuty, Teams, or Webhooks
              </p>
              <Button onClick={() => setShowForm(true)} className="gap-2 mt-2">
                <Plus className="h-4 w-4" />
                Add Channel
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {channels.map((channel: any) => (
                <ChannelCard key={channel.id} channel={channel} onEdit={() => handleEdit(channel)} />
              ))}
            </div>
          )}
        </div>
      </>
    );
  }
