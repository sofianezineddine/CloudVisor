'use client';

import * as React from 'react';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Database, Shield, AlertTriangle, Loader2, CheckCircle2, HardDrive } from 'lucide-react';
import apiClient, { Finding } from '@/lib/api/apiClient';
import { connectorAPI, DiscoveredResource } from '@/lib/api/connector';
import { useScopeStore, getScopeParam } from '@/stores/scope';

export function OverviewTab() {
  const [findings, setFindings] = React.useState<Finding[]>([]);
  const [dataStores, setDataStores] = React.useState<DiscoveredResource[]>([]);
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
        setDataStores(resourcesRes.value.resources.filter(r =>
          ['s3', 'bucket', 'rds', 'database', 'dynamo', 'storage', 'blob', 'secret'].some(k =>
            r.resource_type.toLowerCase().includes(k)
          )
        ));
      }
      setLoading(false);
    });
  }, [scopeAccountId]);

  const dataFindings = findings.filter(f =>
    ['s3', 'bucket', 'rds', 'database', 'storage', 'data', 'secret', 'encryption', 'kms'].some(k =>
      (f.resource_type ?? '').toLowerCase().includes(k) ||
      (f.title ?? '').toLowerCase().includes(k) ||
      (f.rule_id ?? '').toLowerCase().includes(k)
    )
  );

  const publicDataStores = dataStores.filter(r => r.is_public);

  const metrics = [
    { label: 'Data stores', value: loading ? '—' : dataStores.length, color: 'var(--accent)', bg: 'var(--accent-dim)', icon: Database },
    { label: 'Public exposure', value: loading ? '—' : publicDataStores.length, color: 'var(--critical)', bg: 'var(--critical-dim)', icon: AlertTriangle },
    { label: 'Data findings', value: loading ? '—' : dataFindings.length, color: 'var(--high)', bg: 'var(--high-dim)', icon: Shield },
    {
      label: 'Encrypted',
      value: loading ? '—' : `${dataStores.length > 0 ? Math.round(((dataStores.length - publicDataStores.length) / dataStores.length) * 100) : 100}%`,
      color: 'var(--success)',
      bg: 'var(--success-dim)',
      icon: HardDrive,
    },
  ];

  const getDataStoreIcon = (type: string) => {
    if (type.includes('s3') || type.includes('bucket')) return '🪣';
    if (type.includes('rds') || type.includes('database')) return '🗄️';
    if (type.includes('dynamo')) return '⚡';
    if (type.includes('secret')) return '🔐';
    return '💾';
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
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
        {/* Data stores */}
        <div className="cv-container overflow-hidden">
          <div className="border-b px-5 py-3" style={{ borderColor: 'var(--border-faint)' }}>
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
              Data Stores ({dataStores.length})
            </h3>
          </div>
          {loading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          ) : dataStores.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No data stores discovered yet
            </div>
          ) : (
            <div className="divide-y max-h-72 overflow-y-auto" style={{ borderColor: 'var(--border-faint)' }}>
              {dataStores.slice(0, 15).map(r => (
                <div
                  key={r.id}
                  className="flex items-center gap-3 px-5 py-2.5 transition-colors"
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <span className="text-lg flex-shrink-0">{getDataStoreIcon(r.resource_type)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-sm" style={{ color: 'var(--text-primary)' }}>{r.name}</div>
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{r.region}</div>
                  </div>
                  {r.is_public && (
                    <span
                      className="flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold"
                      style={{ backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}
                    >
                      Public
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Data findings */}
        <div className="cv-container overflow-hidden">
          <div className="border-b px-5 py-3" style={{ borderColor: 'var(--border-faint)' }}>
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
              Data Security Findings ({dataFindings.length})
            </h3>
          </div>
          {loading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          ) : dataFindings.length === 0 ? (
            <div className="flex h-32 flex-col items-center justify-center gap-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
              <CheckCircle2 className="h-6 w-6" style={{ color: 'var(--success)' }} />
              No data security findings
            </div>
          ) : (
            <div className="divide-y max-h-72 overflow-y-auto" style={{ borderColor: 'var(--border-faint)' }}>
              {dataFindings.slice(0, 10).map(f => (
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
    </div>
  );
}
