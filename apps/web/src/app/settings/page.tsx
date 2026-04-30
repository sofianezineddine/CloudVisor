'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import ProviderBadge from '@/components/ui/provider-badge';
import { Button } from '@/components/ui/button';
import { Shield, RefreshCw, CheckCircle2, XCircle, Clock, Plus, Trash2, AlertTriangle, Loader2, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { connectorAPI, CloudAccount, CreateAccountRequest } from '@/lib/api/connector';

const PROVIDER_LABELS: Record<string, string> = {
  aws: 'AWS',
  azure: 'Azure',
  gcp: 'GCP',
  oci: 'OCI',
};

const PROVIDER_DESCRIPTIONS: Record<string, string> = {
  aws: 'CloudFormation template with read-only IAM role',
  azure: 'Service principal with Reader role',
  gcp: 'Service account with Viewer role',
  oci: 'API signing key with cross-tenancy policy',
};

// Field key conventions:
//   Keys that match top-level CreateAccountRequest fields (account_id, region) are
//   stored in formData and mapped directly — NOT placed inside credentials{}.
//   All other keys go into credentials{}.
const PROVIDER_CREDENTIAL_FIELDS: Record<string, { key: string; label: string; type?: string; placeholder?: string }[][]> = {
  aws: [
    // account_id → top-level field (maps to CreateAccountRequest.account_id)
    [{ key: 'account_id', label: 'AWS Account ID', placeholder: '123456789012' }],
    [{ key: 'access_key', label: 'Access Key ID', placeholder: 'AKIAIOSFODNN7EXAMPLE' }],
    [{ key: 'secret_key', label: 'Secret Access Key', type: 'password', placeholder: 'Enter secret access key' }],
  ],
  azure: [
    // subscription_id → top-level field (maps to CreateAccountRequest.account_id)
    [{ key: 'subscription_id', label: 'Subscription ID', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' }],
    [{ key: 'tenant_id', label: 'Tenant (Directory) ID', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' }],
    [{ key: 'client_id', label: 'Application (Client) ID', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' }],
    [{ key: 'client_secret', label: 'Client Secret', type: 'password', placeholder: 'Enter client secret' }],
  ],
  gcp: [
    // project_id → top-level field (maps to CreateAccountRequest.account_id)
    [{ key: 'project_id', label: 'Project ID', placeholder: 'my-gcp-project-123' }],
    [{ key: 'service_account_json', label: 'Service Account JSON', type: 'textarea', placeholder: 'Paste contents of your service account key file...' }],
  ],
  oci: [
    // tenancy_ocid → top-level field (maps to CreateAccountRequest.account_id)
    [{ key: 'tenancy_ocid', label: 'Tenancy OCID', placeholder: 'ocid1.tenancy.oc1..' }],
    [{ key: 'user_ocid', label: 'User OCID', placeholder: 'ocid1.user.oc1..' }],
    [{ key: 'fingerprint', label: 'API Key Fingerprint', placeholder: 'xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx' }],
    [{ key: 'region', label: 'Region', placeholder: 'us-ashburn-1' }],
    [{ key: 'private_key', label: 'Private Key', type: 'textarea', placeholder: '-----BEGIN RSA PRIVATE KEY-----\n...' }],
  ],
};

export default function SettingsPage() {
  const [accounts, setAccounts] = React.useState<CloudAccount[]>([]);
  const [loading, setLoading] = React.useState(true);

  // Set browser tab title
  React.useEffect(() => {
    document.title = 'Cloud Accounts - Settings - CloudVisor';
  }, []);
  const [error, setError] = React.useState<string | null>(null);
  const [syncing, setSyncing] = React.useState<Record<string, boolean>>({});
  const [showConnectModal, setShowConnectModal] = React.useState(false);
  const [selectedProvider, setSelectedProvider] = React.useState<string | null>(null);
  const [formData, setFormData] = React.useState<Record<string, string>>({});
  const [submitting, setSubmitting] = React.useState(false);
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  const fetchAccounts = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await connectorAPI.listAccounts();
      setAccounts(response.accounts || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load accounts');
      console.error('Failed to fetch accounts:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  const handleSync = async (accountId: string) => {
    try {
      setSyncing(prev => ({ ...prev, [accountId]: true }));
      await connectorAPI.triggerSync(accountId);
      await new Promise(resolve => setTimeout(resolve, 2000));
      await fetchAccounts();
    } catch (err) {
      console.error('Sync failed:', err);
      alert('Failed to trigger sync. Check console for details.');
    } finally {
      setSyncing(prev => ({ ...prev, [accountId]: false }));
    }
  };

  const handleDelete = async (accountId: string, accountName: string) => {
    if (!confirm(`Are you sure you want to delete "${accountName}"?`)) return;
    try {
      await connectorAPI.deleteAccount(accountId);
      await fetchAccounts();
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete account.');
    }
  };

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProvider) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      // Resolve the canonical account_id for each provider:
      //   AWS   → AWS Account ID  (formData.account_id)
      //   Azure → Subscription ID (formData.subscription_id)
      //   GCP   → Project ID      (formData.project_id)
      //   OCI   → Tenancy OCID    (formData.tenancy_ocid)
      const providerAccountIdMap: Record<string, string> = {
        aws: formData.account_id || '',
        azure: formData.subscription_id || '',
        gcp: formData.project_id || '',
        oci: formData.tenancy_ocid || '',
      };
      const resolvedAccountId = providerAccountIdMap[selectedProvider] || '';

      if (!resolvedAccountId.trim()) {
        const fieldLabels: Record<string, string> = {
          aws: 'AWS Account ID',
          azure: 'Subscription ID',
          gcp: 'Project ID',
          oci: 'Tenancy OCID',
        };
        setSubmitError(`${fieldLabels[selectedProvider] || 'Account ID'} is required.`);
        setSubmitting(false);
        return;
      }

      // Fields that go directly into the top-level request body (not inside credentials{})
      const topLevelFields = new Set(['name', 'account_id', 'subscription_id', 'project_id', 'tenancy_ocid', 'region', 'polling_interval']);

      const credentials: Record<string, any> = {};
      for (const [key, value] of Object.entries(formData)) {
        if (topLevelFields.has(key)) continue;
        if (!value) continue;

        if (key === 'service_account_json') {
          try {
            credentials[key] = JSON.parse(value);
          } catch {
            credentials[key] = value; // send as-is if not valid JSON
          }
        } else {
          credentials[key] = value;
        }
      }

      const data: CreateAccountRequest = {
        provider: selectedProvider,
        name: formData.name?.trim() || `${PROVIDER_LABELS[selectedProvider]} Account`,
        account_id: resolvedAccountId,
        region: formData.region?.trim() || 'global',
        credentials,
        polling_interval_minutes: parseInt(formData.polling_interval || '15', 10),
      };

      await connectorAPI.createAccount(data);
      setShowConnectModal(false);
      setSelectedProvider(null);
      setFormData({});
      await fetchAccounts();
    } catch (err) {
      let errorMessage = 'Failed to create account';
      if (err instanceof Error) {
        // If the error message contains JSON, try to parse it for a better message
        const match = err.message.match(/\{.*\}/);
        if (match) {
          try {
            const parsed = JSON.parse(match[0]);
            if (parsed.detail) {
              if (Array.isArray(parsed.detail)) {
                errorMessage = parsed.detail.map((e: any) => e.msg || e.message).join(', ');
              } else if (typeof parsed.detail === 'string') {
                errorMessage = parsed.detail;
              }
            }
          } catch {
            errorMessage = err.message;
          }
        } else {
          errorMessage = err.message;
        }
      }
      setSubmitError(errorMessage);
      console.error('Create account failed:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const getHealthIcon = (account: CloudAccount) => {
    if (account.status === 'error' || account.status === 'auth_failed') {
      return <XCircle className="h-5 w-5" style={{ color: 'var(--critical)' }} />;
    }
    if (account.consecutive_errors > 0) {
      return <AlertTriangle className="h-5 w-5" style={{ color: 'var(--warning)' }} />;
    }
    return <CheckCircle2 className="h-5 w-5" style={{ color: 'var(--success)' }} />;
  };

  const getSyncStatusText = (account: CloudAccount) => {
    if (!account.last_sync_at) return 'Never synced';
    const date = new Date(account.last_sync_at);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHrs = Math.floor(diffMins / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    return `${Math.floor(diffHrs / 24)}d ago`;
  };

  const closeModal = () => {
    setShowConnectModal(false);
    setSelectedProvider(null);
    setFormData({});
    setSubmitError(null);
  };

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Settings' }, { text: 'Cloud accounts' }]}>
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Cloud accounts</h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Manage your connected cloud environments
            </p>
          </div>
          <Button className="gap-2" style={{ backgroundColor: 'var(--accent)', color: '#ffffff' }} onClick={() => setShowConnectModal(true)}>
            <Plus className="h-4 w-4" />
            Connect Account
          </Button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border p-4 text-sm" style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}>
            {error}
          </div>
        )}

        {/* Connected Accounts */}
        <div className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--text-secondary)' }} />
            </div>
          ) : accounts.length === 0 ? (
            <div className="cv-container flex flex-col items-center justify-center p-12 text-center">
              <Shield className="mb-3 h-12 w-12" style={{ color: 'var(--text-tertiary)' }} />
              <h3 className="mb-1 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>No cloud accounts connected</h3>
              <p className="mb-4 max-w-sm text-sm" style={{ color: 'var(--text-secondary)' }}>
                Connect your first cloud account to start discovering resources and monitoring your cloud security posture.
              </p>
              <Button onClick={() => setShowConnectModal(true)} className="gap-2" style={{ backgroundColor: 'var(--accent)', color: '#ffffff' }}>
                <Plus className="h-4 w-4" />
                Connect Account
              </Button>
            </div>
          ) : (
            accounts.map((account) => (
              <div key={account.id} className="cv-container p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div className="mt-1">
                      <ProviderBadge provider={account.provider} />
                    </div>
                    <div className="flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{account.name}</h3>
                        <span
                          className="rounded-full px-2 py-0.5 text-[10px] font-semibold"
                          style={
                            account.status === 'active'
                              ? { backgroundColor: 'var(--success-dim)', color: 'var(--success)' }
                              : account.status === 'error' || account.status === 'auth_failed'
                              ? { backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }
                              : { backgroundColor: 'var(--warning-dim)', color: 'var(--warning)' }
                          }
                        >
                          {account.status}
                        </span>
                        {account.sync_status !== 'idle' && (
                          <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold" style={{ backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}>
                            {account.sync_status}
                          </span>
                        )}
                      </div>
                      <div className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>{account.account_id}</div>
                      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                        <span className="flex items-center gap-1">
                          <Shield className="h-3 w-3" />
                          {account.resource_count.toLocaleString()} resources
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {getSyncStatusText(account)}
                        </span>
                        {account.consecutive_errors > 0 && (
                          <span className="flex items-center gap-1" style={{ color: 'var(--critical)' }}>
                            <AlertTriangle className="h-3 w-3" />
                            {account.consecutive_errors} error{account.consecutive_errors > 1 ? 's' : ''}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <RefreshCw className="h-3 w-3" />
                          Every {account.polling_interval_minutes}m
                        </span>
                      </div>
                      {account.error_message && (
                        <div className="mt-2 text-xs" style={{ color: 'var(--critical)' }}>
                          Error: {account.error_message}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {getHealthIcon(account)}
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1.5 text-xs"
                      onClick={() => handleSync(account.id)}
                      disabled={syncing[account.id]}
                    >
                      {syncing[account.id] ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3" />
                      )}
                      Sync
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0"
                      style={{ color: 'var(--text-tertiary)' }}
                      onClick={() => handleDelete(account.id, account.name)}
                      onMouseEnter={e => {
                        (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--critical-dim)';
                        (e.currentTarget as HTMLElement).style.color = 'var(--critical)';
                      }}
                      onMouseLeave={e => {
                        (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                        (e.currentTarget as HTMLElement).style.color = 'var(--text-tertiary)';
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Connect New Account Guide */}
        <div className="mt-8 cv-container p-6">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Connect a new cloud account</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(PROVIDER_LABELS).map(([key, label]) => (
              <button
                key={key}
                onClick={() => {
                  setSelectedProvider(key);
                  setShowConnectModal(true);
                }}
                className="rounded-lg border p-4 text-left transition-all"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)' }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = 'var(--accent)';
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-default)';
                }}
              >
                <ProviderBadge provider={key as 'aws' | 'azure' | 'gcp' | 'oci'} />
                <p className="mt-2 text-xs" style={{ color: 'var(--text-secondary)' }}>{PROVIDER_DESCRIPTIONS[key]}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Connect Account Modal */}
        {showConnectModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              className="fixed inset-0 backdrop-blur-sm"
              style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
              onClick={closeModal}
            />
            <div
              className="relative z-50 w-full max-w-lg rounded-xl shadow-2xl"
              style={{ border: '1px solid var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
            >
              {/* Modal header */}
              <div className="flex items-center justify-between border-b px-6 py-4" style={{ borderColor: 'var(--border-default)' }}>
                <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {selectedProvider ? `Connect ${PROVIDER_LABELS[selectedProvider]} Account` : 'Connect Cloud Account'}
                </h2>
                <button
                  onClick={closeModal}
                  className="rounded-md p-1 transition-colors"
                  style={{ color: 'var(--text-tertiary)' }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Modal body */}
              <div className="p-6">
                {!selectedProvider ? (
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(PROVIDER_LABELS).map(([key, label]) => (
                      <button
                        key={key}
                        onClick={() => setSelectedProvider(key)}
                        className="rounded-lg border p-4 text-left transition-all"
                        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)' }}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border-default)')}
                      >
                        <ProviderBadge provider={key as 'aws' | 'azure' | 'gcp' | 'oci'} />
                        <p className="mt-2 text-xs" style={{ color: 'var(--text-secondary)' }}>{PROVIDER_DESCRIPTIONS[key]}</p>
                      </button>
                    ))}
                  </div>
                ) : (
                  <form onSubmit={handleConnect} className="space-y-4">
                    {submitError && (
                      <div className="rounded-lg border p-3 text-xs" style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}>
                        {submitError}
                      </div>
                    )}

                    {/* Account Name */}
                    <div>
                      <label className="mb-1.5 block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                        Account Name <span style={{ color: 'var(--critical)' }}>*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.name || ''}
                        onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                        placeholder={`${PROVIDER_LABELS[selectedProvider]} Account`}
                        className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
                        onFocus={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
                        onBlur={e => (e.currentTarget.style.borderColor = 'var(--border-default)')}
                      />
                    </div>

                    {/* Provider-specific credential fields */}
                    {PROVIDER_CREDENTIAL_FIELDS[selectedProvider]?.map((row, i) => (
                      <div key={i} className={row.length > 1 ? 'grid grid-cols-2 gap-3' : 'space-y-3'}>
                        {row.map(field => (
                          <div key={field.key}>
                            <label className="mb-1.5 block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                              {field.label} <span style={{ color: 'var(--critical)' }}>*</span>
                            </label>
                            {field.type === 'textarea' ? (
                              <textarea
                                required
                                value={formData[field.key] || ''}
                                onChange={e => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
                                placeholder={field.placeholder || field.label}
                                rows={4}
                                className="w-full rounded-md border px-3 py-2 text-xs font-mono focus:outline-none resize-none"
                                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
                                onFocus={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                onBlur={e => (e.currentTarget.style.borderColor = 'var(--border-default)')}
                              />
                            ) : (
                              <input
                                type={field.type || 'text'}
                                required
                                value={formData[field.key] || ''}
                                onChange={e => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
                                placeholder={field.placeholder || field.label}
                                className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
                                onFocus={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                onBlur={e => (e.currentTarget.style.borderColor = 'var(--border-default)')}
                              />
                            )}
                          </div>
                        ))}
                      </div>
                    ))}

                    {/* Polling interval */}
                    <div>
                      <label className="mb-1.5 block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                        Sync Interval
                      </label>
                      <select
                        value={formData.polling_interval || '1'}
                        onChange={e => setFormData(prev => ({ ...prev, polling_interval: e.target.value }))}
                        className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none"
                        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
                      >
                        <option value="1">Every 1 minute (near real-time)</option>
                        <option value="5">Every 5 minutes</option>
                        <option value="15">Every 15 minutes</option>
                        <option value="30">Every 30 minutes</option>
                        <option value="60">Every 60 minutes</option>
                      </select>
                    </div>

                    {/* Action buttons */}
                    <div className="flex gap-3 pt-2">
                      <Button
                        type="submit"
                        disabled={submitting}
                        className="flex-1 gap-2"
                        style={{ backgroundColor: 'var(--accent)', color: '#ffffff' }}
                      >
                        {submitting ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Connecting...
                          </>
                        ) : (
                          <>
                            <Plus className="h-4 w-4" />
                            Connect Account
                          </>
                        )}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setSelectedProvider(null)}
                      >
                        Back
                      </Button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          </div>
        )}
      </AppLayout>
    </ProtectedRoute>
  );
}
