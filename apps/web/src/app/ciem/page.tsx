'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { ModuleTabBar, ModuleTab } from '@/components/ui/module-tab-bar';
import { Lock, Users, Shield, Key, RefreshCw, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';
import apiClient, { Finding } from '@/lib/api/apiClient';
import { connectorAPI, DiscoveredResource } from '@/lib/api/connector';
import { useScopeStore, getScopeParam } from '@/stores/scope';
import { NoAccountsConnectedEmptyState } from '@/components/ui/no-accounts-empty-state';

export default function CIEMPage() {
  const [findings, setFindings] = React.useState<Finding[]>([]);
  const [iamResources, setIamResources] = React.useState<DiscoveredResource[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [activeTab, setActiveTab] = React.useState<ModuleTab>('overview');
  const accountIds = useScopeStore(s => s.accountIds);
  const scopeAccountId = useScopeStore(s => getScopeParam(s.accountIds));

  React.useEffect(() => {
    document.title = 'Identity (CIEM) - CloudVisor';
  }, []);

  React.useEffect(() => {
    Promise.allSettled([
      apiClient.findings.list({ limit: 50, account_id: scopeAccountId || undefined }),
      connectorAPI.listResources({ resource_type: 'aws::iamuser', limit: 100 }),
      connectorAPI.listResources({ resource_type: 'aws::iamrole', limit: 100 }),
    ]).then(([findingsRes, usersRes, rolesRes]) => {
      if (findingsRes.status === 'fulfilled') setFindings((findingsRes.value?.data as Finding[]) ?? []);
      const users = usersRes.status === 'fulfilled' ? usersRes.value.resources : [];
      const roles = rolesRes.status === 'fulfilled' ? rolesRes.value.resources : [];
      setIamResources([...users, ...roles]);
      setLoading(false);
    });
  }, [scopeAccountId]);

  const iamFindings = findings.filter(f =>
    ['iam', 'identity', 'user', 'role', 'permission', 'mfa', 'access'].some(k =>
      (f.resource_type ?? '').toLowerCase().includes(k) ||
      (f.title ?? '').toLowerCase().includes(k) ||
      (f.rule_id ?? '').toLowerCase().includes(k)
    )
  );

  const iamUsers = iamResources.filter(r => r.resource_type.includes('iamuser'));
  const iamRoles = iamResources.filter(r => r.resource_type.includes('iamrole'));

  const metrics = [
    { label: 'IAM Users', value: loading ? '—' : iamUsers.length, color: 'var(--accent)', bg: 'var(--accent-dim)', icon: Users },
    { label: 'IAM Roles', value: loading ? '—' : iamRoles.length, color: 'var(--low)', bg: 'var(--low-dim)', icon: Key },
    { label: 'Identity findings', value: loading ? '—' : iamFindings.length, color: 'var(--critical)', bg: 'var(--critical-dim)', icon: AlertTriangle },
    { label: 'Total identities', value: loading ? '—' : iamResources.length, color: 'var(--medium)', bg: 'var(--medium-dim)', icon: Shield },
  ];

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Identity (CIEM)' }]}>
        {accountIds.length === 0 ? (
          <NoAccountsConnectedEmptyState />
        ) : (
          <>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>CIEM — Cloud Infrastructure Entitlements</h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Identity and permissions management across all clouds</p>
          </div>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={() => window.location.reload()}>
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
        </div>

        <ModuleTabBar module="ciem" activeTab={activeTab} onTabChange={setActiveTab} />

        {activeTab === 'overview' && (<>
        {/* Metrics */}
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {metrics.map(m => (
            <div key={m.label} className="cv-container p-4">
              <div
                className="mb-3 flex h-8 w-8 items-center justify-center rounded-md"
                style={{ backgroundColor: m.bg }}
              >
                <m.icon className="h-4 w-4" style={{ color: m.color }} />
              </div>
              <div className="mb-1 font-mono text-2xl font-bold" style={{ color: m.color }}>{m.value}</div>
              <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>{m.label}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* IAM Identities */}
          <div className="cv-container overflow-hidden">
            <div
              className="border-b px-5 py-3"
              style={{ borderColor: 'var(--border-faint)' }}
            >
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                IAM Identities ({iamResources.length})
              </h3>
            </div>
            {loading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
              </div>
            ) : iamResources.length === 0 ? (
              <div className="flex h-32 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
                No IAM identities discovered yet
              </div>
            ) : (
              <div className="divide-y max-h-64 overflow-y-auto" style={{ borderColor: 'var(--border-faint)' }}>
                {iamResources.slice(0, 15).map(r => (
                  <div
                    key={r.id}
                    className="flex items-center gap-3 px-5 py-2.5 transition-colors"
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <div
                      className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-semibold"
                      style={
                        r.resource_type.includes('user')
                          ? { backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }
                          : { backgroundColor: 'var(--medium-dim)', color: 'var(--medium)' }
                      }
                    >
                      {r.resource_type.includes('user') ? 'U' : 'R'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="truncate text-sm" style={{ color: 'var(--text-primary)' }}>{r.name}</div>
                      <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                        {r.resource_type.includes('user') ? 'IAM User' : 'IAM Role'} · {r.region}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Identity findings */}
          <div className="cv-container overflow-hidden">
            <div
              className="border-b px-5 py-3"
              style={{ borderColor: 'var(--border-faint)' }}
            >
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                Identity Findings ({iamFindings.length})
              </h3>
            </div>
            {loading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
              </div>
            ) : iamFindings.length === 0 ? (
              <div className="flex h-32 flex-col items-center justify-center gap-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                <CheckCircle2 className="h-6 w-6" style={{ color: 'var(--success)' }} />
                No identity findings
              </div>
            ) : (
              <div className="divide-y max-h-64 overflow-y-auto" style={{ borderColor: 'var(--border-faint)' }}>
                {iamFindings.slice(0, 10).map(f => (
                  <div
                    key={f.id}
                    className="flex items-center gap-3 px-5 py-2.5 transition-colors"
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <SeverityBadge severity={f.severity} size="sm" />
                    <div className="flex-1 min-w-0">
                      <div className="truncate text-sm" style={{ color: 'var(--text-primary)' }}>{f.title}</div>
                      <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{f.resource_name || f.resource_id}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        </>)}

        {activeTab === 'findings' && (
          <div className="cv-container p-6"><p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Findings filtered to this module coming soon.</p></div>
        )}
        {activeTab === 'policies' && (
          <div className="cv-container p-6"><p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Policy library coming soon.</p></div>
        )}
        {activeTab === 'reports' && (
          <div className="cv-container p-6"><p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Reports coming soon.</p></div>
        )}
          </>
        )}
      </AppLayout>
    </ProtectedRoute>
  );
}
