'use client';

import * as React from 'react';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { Shield, Server, AlertTriangle, Package, RefreshCw, Loader2, CheckCircle2 } from 'lucide-react';
import apiClient, { Finding } from '@/lib/api/apiClient';
import { useScopeStore, getScopeParam } from '@/stores/scope';

const WORKLOAD_TYPES = [
  { label: 'EC2 Instances', icon: '🖥️', key: 'ec2' },
  { label: 'Containers', icon: '📦', key: 'container' },
  { label: 'Lambda', icon: '⚡', key: 'lambda' },
  { label: 'ECS/EKS', icon: '☸️', key: 'eks' },
];

export function OverviewTab() {
  const [findings, setFindings] = React.useState<Finding[]>([]);
  const [stats, setStats] = React.useState<Record<string, any>>({});
  const [loading, setLoading] = React.useState(true);
  const scopeAccountId = useScopeStore(s => getScopeParam(s.accountIds));

  React.useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      apiClient.findings.stats(),
      apiClient.findings.list({ limit: 20, account_id: scopeAccountId || undefined }),
    ]).then(([statsRes, findingsRes]) => {
      if (statsRes.status === 'fulfilled') setStats((statsRes.value?.data as any) ?? {});
      if (findingsRes.status === 'fulfilled') setFindings((findingsRes.value?.data as Finding[]) ?? []);
      setLoading(false);
    });
  }, [scopeAccountId]);

  const workloadFindings = findings.filter(f =>
    ['ec2', 'instance', 'lambda', 'container', 'eks', 'ecs', 'workload'].some(k =>
      (f.resource_type ?? '').toLowerCase().includes(k) ||
      (f.title ?? '').toLowerCase().includes(k)
    )
  );

  const criticalCount = stats?.by_severity?.CRITICAL ?? 0;
  const highCount = stats?.by_severity?.HIGH ?? 0;

  const metrics = [
    { label: 'Critical CVEs', value: loading ? '—' : criticalCount, color: 'var(--critical)', bg: 'var(--critical-dim)', icon: AlertTriangle },
    { label: 'High severity', value: loading ? '—' : highCount, color: 'var(--high)', bg: 'var(--high-dim)', icon: Shield },
    { label: 'Workload findings', value: loading ? '—' : workloadFindings.length, color: 'var(--medium)', bg: 'var(--medium-dim)', icon: Server },
    { label: 'Open findings', value: loading ? '—' : (stats?.by_status?.open ?? 0), color: 'var(--accent)', bg: 'var(--accent-dim)', icon: Package },
  ];

  return (
    <>
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

      {/* Workload type breakdown */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {WORKLOAD_TYPES.map(wt => (
          <div key={wt.key} className="cv-container p-4 text-center">
            <div className="mb-2 text-2xl">{wt.icon}</div>
            <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{wt.label}</div>
            <div className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
              {loading ? '—' : `${workloadFindings.filter(f => (f.resource_type ?? '').toLowerCase().includes(wt.key)).length} findings`}
            </div>
          </div>
        ))}
      </div>

      {/* Findings table */}
      <div className="cv-container overflow-hidden">
        <div
          className="flex items-center justify-between border-b px-5 py-3"
          style={{ borderColor: 'var(--border-faint)' }}
        >
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Workload findings</h3>
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" onClick={() => window.location.reload()}>
            <RefreshCw className="h-3 w-3" />
            Refresh
          </Button>
        </div>
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
          </div>
        ) : workloadFindings.length === 0 ? (
          <div className="flex h-32 flex-col items-center justify-center gap-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
            <CheckCircle2 className="h-6 w-6" style={{ color: 'var(--success)' }} />
            No workload findings — your compute resources look clean
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
            {workloadFindings.slice(0, 10).map(f => (
              <div
                key={f.id}
                className="flex items-center gap-3 px-5 py-3 transition-colors"
                style={{ borderColor: 'var(--border-faint)' }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                <SeverityBadge severity={f.severity} size="sm" />
                <div className="flex-1 min-w-0">
                  <div className="truncate text-sm" style={{ color: 'var(--text-primary)' }}>{f.title}</div>
                  <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{f.resource_name || f.resource_id}</div>
                </div>
                <span className="flex-shrink-0 text-xs" style={{ color: 'var(--text-tertiary)' }}>{f.region}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
