'use client';

import * as React from 'react';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Network, Shield, AlertTriangle, Loader2, CheckCircle2 } from 'lucide-react';
import apiClient, { Finding } from '@/lib/api/apiClient';
import { connectorAPI, DiscoveredResource } from '@/lib/api/connector';
import { useScopeStore, getScopeParam } from '@/stores/scope';

export function OverviewTab() {
  const [findings, setFindings] = React.useState<Finding[]>([]);
  const [clusters, setClusters] = React.useState<DiscoveredResource[]>([]);
  const [loading, setLoading] = React.useState(true);
  const scopeAccountId = useScopeStore(s => getScopeParam(s.accountIds));

  React.useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      apiClient.findings.list({ limit: 50, account_id: scopeAccountId || undefined }),
      connectorAPI.listResources({ limit: 200 }),
    ]).then(([findingsRes, resourcesRes]) => {
      if (findingsRes.status === 'fulfilled') setFindings((findingsRes.value?.data as Finding[]) ?? []);
      if (resourcesRes.status === 'fulfilled') {
        setClusters(resourcesRes.value.resources.filter(r =>
          ['eks', 'aks', 'gke', 'cluster', 'kubernetes', 'k8s'].some(k =>
            r.resource_type.toLowerCase().includes(k)
          )
        ));
      }
      setLoading(false);
    });
  }, [scopeAccountId]);

  const k8sFindings = findings.filter(f =>
    ['eks', 'kubernetes', 'k8s', 'cluster', 'pod', 'container', 'node'].some(k =>
      (f.resource_type ?? '').toLowerCase().includes(k) ||
      (f.title ?? '').toLowerCase().includes(k)
    )
  );

  const metrics = [
    { label: 'Clusters', value: loading ? '—' : clusters.length, color: 'var(--accent)', bg: 'var(--accent-dim)', icon: Network },
    { label: 'K8s findings', value: loading ? '—' : k8sFindings.length, color: 'var(--critical)', bg: 'var(--critical-dim)', icon: AlertTriangle },
    { label: 'Critical', value: loading ? '—' : k8sFindings.filter(f => f.severity === 'CRITICAL').length, color: 'var(--critical)', bg: 'var(--critical-dim)', icon: Shield },
    { label: 'High', value: loading ? '—' : k8sFindings.filter(f => f.severity === 'HIGH').length, color: 'var(--high)', bg: 'var(--high-dim)', icon: Shield },
  ];

  return (
    <>
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
        {/* Clusters */}
        <div className="cv-container overflow-hidden">
          <div className="border-b px-5 py-3" style={{ borderColor: 'var(--border-faint)' }}>
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Kubernetes Clusters</h3>
          </div>
          {loading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          ) : clusters.length === 0 ? (
            <div className="flex h-32 flex-col items-center justify-center gap-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
              <Network className="h-8 w-8 opacity-30" />
              No Kubernetes clusters discovered
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
              {clusters.map(c => (
                <div
                  key={c.id}
                  className="flex items-center gap-3 px-5 py-3 transition-colors"
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <div
                    className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-sm"
                    style={{ backgroundColor: 'var(--accent-dim)' }}
                  >
                    ☸️
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{c.name}</div>
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{c.region} · {c.provider.toUpperCase()}</div>
                  </div>
                  <span
                    className="flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold"
                    style={{ backgroundColor: 'var(--success-dim)', color: 'var(--success)' }}
                  >
                    Active
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* K8s findings */}
        <div className="cv-container overflow-hidden">
          <div className="border-b px-5 py-3" style={{ borderColor: 'var(--border-faint)' }}>
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Security Findings</h3>
          </div>
          {loading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          ) : k8sFindings.length === 0 ? (
            <div className="flex h-32 flex-col items-center justify-center gap-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
              <CheckCircle2 className="h-6 w-6" style={{ color: 'var(--success)' }} />
              No Kubernetes findings
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
              {k8sFindings.slice(0, 8).map(f => (
                <div
                  key={f.id}
                  className="flex items-center gap-3 px-5 py-2.5 transition-colors"
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <SeverityBadge severity={f.severity} size="sm" />
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-sm" style={{ color: 'var(--text-primary)' }}>{f.title}</div>
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{f.resource_name}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
