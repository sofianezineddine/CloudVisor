'use client';

import * as React from 'react';
import { DetailDrawer } from '@/components/ui/detail-drawer';
import { Button } from '@/components/ui/button';
import { Circle, Trash2, CheckCircle, XCircle } from 'lucide-react';
import {
  useInstallProvider,
  useTestProvider,
  useDeleteProvider,
  type AIOpsProvider,
} from '@/hooks/use-aiops-providers';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ProviderConfigFormProps {
  provider: AIOpsProvider | null;
  onClose: () => void;
}

// ─── Status Styles ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  connected: { color: 'var(--success)', label: 'Connected' },
  disconnected: { color: 'var(--critical)', label: 'Disconnected' },
  not_configured: { color: 'var(--text-tertiary)', label: 'Not Configured' },
};

// ─── Provider Schema (dynamic fields based on type) ───────────────────────────

interface FieldSchema {
  key: string;
  label: string;
  type: 'text' | 'password' | 'url' | 'number';
  placeholder?: string;
  required?: boolean;
}

const PROVIDER_SCHEMAS: Record<string, FieldSchema[]> = {
  prometheus: [
    { key: 'url', label: 'Prometheus URL', type: 'url', placeholder: 'https://prometheus.example.com', required: true },
    { key: 'username', label: 'Username', type: 'text', placeholder: 'Optional' },
    { key: 'password', label: 'Password', type: 'password', placeholder: 'Optional' },
  ],
  grafana: [
    { key: 'url', label: 'Grafana URL', type: 'url', placeholder: 'https://grafana.example.com', required: true },
    { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'Service account token', required: true },
  ],
  datadog: [
    { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'Datadog API key', required: true },
    { key: 'app_key', label: 'Application Key', type: 'password', placeholder: 'Datadog app key', required: true },
    { key: 'site', label: 'Site', type: 'text', placeholder: 'datadoghq.com' },
  ],
  pagerduty: [
    { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'PagerDuty API key', required: true },
    { key: 'routing_key', label: 'Routing Key', type: 'password', placeholder: 'Integration routing key' },
  ],
  cloudwatch: [
    { key: 'aws_access_key_id', label: 'AWS Access Key ID', type: 'text', required: true },
    { key: 'aws_secret_access_key', label: 'AWS Secret Access Key', type: 'password', required: true },
    { key: 'region', label: 'Region', type: 'text', placeholder: 'us-east-1', required: true },
  ],
  webhook: [
    { key: 'url', label: 'Webhook URL', type: 'url', placeholder: 'https://example.com/webhook', required: true },
    { key: 'secret', label: 'Secret', type: 'password', placeholder: 'Webhook secret (optional)' },
  ],
};

function getSchemaForProvider(type: string): FieldSchema[] {
  return PROVIDER_SCHEMAS[type] ?? [
    { key: 'url', label: 'URL', type: 'url', placeholder: 'Provider endpoint URL', required: true },
    { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'API key or token', required: true },
  ];
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ProviderConfigForm({ provider, onClose }: ProviderConfigFormProps) {
  const installProvider = useInstallProvider();
  const testProvider = useTestProvider();
  const deleteProvider = useDeleteProvider();

  const [configValues, setConfigValues] = React.useState<Record<string, string>>({});
  const [testResult, setTestResult] = React.useState<{ success: boolean; message: string } | null>(null);
  const [testing, setTesting] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);

  // Initialize config values from provider
  React.useEffect(() => {
    if (provider?.config) {
      const values: Record<string, string> = {};
      Object.entries(provider.config).forEach(([key, value]) => {
        values[key] = String(value ?? '');
      });
      setConfigValues(values);
    } else {
      setConfigValues({});
    }
    setTestResult(null);
  }, [provider]);

  const schema = provider ? getSchemaForProvider(provider.type) : [];

  const handleFieldChange = (key: string, value: string) => {
    setConfigValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleTestConnection = async () => {
    if (!provider) return;
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testProvider.mutateAsync({ id: provider.id });
      setTestResult(result);
    } catch (err) {
      setTestResult({ success: false, message: (err as Error).message });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (!provider) return;
    setSaving(true);
    try {
      await installProvider.mutateAsync({
        type: provider.type,
        config: configValues,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!provider) return;
    setDeleting(true);
    try {
      await deleteProvider.mutateAsync({ type: provider.type, id: provider.id });
      onClose();
    } finally {
      setDeleting(false);
    }
  };

  const statusConfig = provider ? STATUS_CONFIG[provider.status] ?? STATUS_CONFIG.not_configured : STATUS_CONFIG.not_configured;

  return (
    <DetailDrawer
      isOpen={!!provider}
      onClose={onClose}
      title={provider?.name ?? 'Provider Configuration'}
      subtitle={provider ? provider.type : undefined}
      width={640}
      actions={
        provider ? (
          <div className="flex items-center justify-between">
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={deleting}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
              {deleting ? 'Deleting...' : 'Delete'}
            </Button>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleTestConnection}
                disabled={testing}
              >
                {testing ? 'Testing...' : 'Test Connection'}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </div>
        ) : undefined
      }
    >
      {provider && (
        <div className="space-y-6">
          {/* Status */}
          <div className="flex items-center gap-2">
            <Circle className="h-2.5 w-2.5 fill-current" style={{ color: statusConfig.color }} />
            <span className="text-sm font-medium" style={{ color: statusConfig.color }}>
              {statusConfig.label}
            </span>
            {provider.last_sync && (
              <span className="text-xs ml-2" style={{ color: 'var(--text-tertiary)' }}>
                Last sync: {new Date(provider.last_sync).toLocaleString()}
              </span>
            )}
          </div>

          {/* Test Result */}
          {testResult && (
            <div
              className="flex items-center gap-2 rounded-md p-3"
              style={{
                backgroundColor: testResult.success ? 'var(--success-bg, rgba(61, 184, 122, 0.08))' : 'var(--critical-bg)',
                border: `1px solid ${testResult.success ? 'var(--success)' : 'var(--critical)'}`,
              }}
            >
              {testResult.success ? (
                <CheckCircle className="h-4 w-4 flex-shrink-0" style={{ color: 'var(--success)' }} />
              ) : (
                <XCircle className="h-4 w-4 flex-shrink-0" style={{ color: 'var(--critical)' }} />
              )}
              <span className="text-sm" style={{ color: testResult.success ? 'var(--success)' : 'var(--critical)' }}>
                {testResult.message}
              </span>
            </div>
          )}

          {/* Configuration Fields */}
          <div>
            <h3
              className="text-xs font-medium uppercase tracking-wider mb-3"
              style={{ color: 'var(--text-tertiary)' }}
            >
              Configuration
            </h3>
            <div className="space-y-4">
              {schema.map((field) => (
                <div key={field.key}>
                  <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                    {field.label}
                    {field.required && <span style={{ color: 'var(--critical)' }}> *</span>}
                  </label>
                  <input
                    type={field.type}
                    value={configValues[field.key] ?? ''}
                    onChange={(e) => handleFieldChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    className="w-full rounded-md px-3 py-2 text-sm"
                    style={{
                      backgroundColor: 'var(--bg-elevated)',
                      border: '1px solid var(--border-default)',
                      color: 'var(--text-primary)',
                    }}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </DetailDrawer>
  );
}
