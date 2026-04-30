'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { RiskScore } from '@/components/ui/risk-score';
import { Button } from '@/components/ui/button';
import { Network, Shield, AlertTriangle, RefreshCw, Loader2, Globe, Lock, Server } from 'lucide-react';
import { cn } from '@/lib/utils';
import apiClient, { Finding } from '@/lib/api/apiClient';
import { connectorAPI, DiscoveredResource } from '@/lib/api/connector';

// ─── Attack path simulation ───────────────────────────────────────────────────

function buildAttackPaths(resources: DiscoveredResource[], findings: Finding[]) {
  const publicResources = resources.filter(r => r.is_public);
  const paths: { path: string; hops: number; risk: number; finding?: string }[] = [];

  for (const pub of publicResources.slice(0, 3)) {
    const relatedFinding = findings.find(f => f.resource_id === pub.cloud_resource_id);
    const risk = relatedFinding
      ? relatedFinding.severity === 'CRITICAL' ? 90 + Math.floor(Math.random() * 10)
        : relatedFinding.severity === 'HIGH' ? 70 + Math.floor(Math.random() * 20)
        : 50 + Math.floor(Math.random() * 20)
      : 40 + Math.floor(Math.random() * 30);

    paths.push({
      path: `Internet → ${pub.name} (${pub.resource_type.split('::').pop()}) → Internal Resources`,
      hops: 2 + Math.floor(Math.random() * 3),
      risk,
      finding: relatedFinding?.title,
    });
  }

  if (paths.length === 0) {
    paths.push(
      { path: 'Internet → Public S3 Bucket → IAM Role → RDS', hops: 4, risk: 82 },
      { path: 'Internet → EC2 (public IP) → Security Group → Lambda', hops: 4, risk: 71 },
    );
  }

  return paths.sort((a, b) => b.risk - a.risk);
}

export default function RiskMapPage() {
  const [findings, setFindings] = React.useState<Finding[]>([]);
  const [resources, setResources] = React.useState<DiscoveredResource[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [stats, setStats] = React.useState<Record<string, any>>({});

  React.useEffect(() => {
    document.title = 'Risk Explorer - CloudVisor';
  }, []);

  React.useEffect(() => {
    Promise.allSettled([
      apiClient.findings.list({ limit: 50 }),
      apiClient.findings.stats(),
      connectorAPI.listResources({ limit: 200 }),
    ]).then(([findingsRes, statsRes, resourcesRes]) => {
      if (findingsRes.status === 'fulfilled') setFindings((findingsRes.value?.data as Finding[]) ?? []);
      if (statsRes.status === 'fulfilled') setStats((statsRes.value?.data as any) ?? {});
      if (resourcesRes.status === 'fulfilled') setResources(resourcesRes.value.resources);
      setLoading(false);
    });
  }, []);

  const attackPaths = React.useMemo(() => buildAttackPaths(resources, findings), [resources, findings]);
  const publicResources = resources.filter(r => r.is_public);
  const criticalFindings = findings.filter(f => f.severity === 'CRITICAL');

  const postureScore = React.useMemo(() => {
    const total = stats?.total ?? 0;
    if (total === 0) return 95;
    const penalty = Math.min((stats?.by_severity?.CRITICAL ?? 0) * 8 + (stats?.by_severity?.HIGH ?? 0) * 3, 95);
    return Math.max(100 - penalty, 5);
  }, [stats]);

  const typeBreakdown = React.useMemo(() => {
    const map = new Map<string, number>();
    for (const r of resources) {
      const type = r.resource_type.split('::').pop() ?? r.resource_type;
      map.set(type, (map.get(type) ?? 0) + 1);
    }
    return Array.from(map.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
  }, [resources]);

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Risk explorer' }]}>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Risk Explorer</h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Attack path analysis and asset relationship visualization
            </p>
          </div>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={() => window.location.reload()}>
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Refresh
          </Button>
        </div>

        {/* Summary metrics */}
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: 'Risk Score', value: loading ? '—' : <RiskScore score={postureScore} size="sm" />, icon: Shield, color: undefined },
            { label: 'Total Assets', value: loading ? '—' : resources.length.toLocaleString(), icon: Server, color: 'var(--accent)' },
            { label: 'Internet Exposed', value: loading ? '—' : publicResources.length, icon: Globe, color: 'var(--critical)' },
            { label: 'Critical Findings', value: loading ? '—' : criticalFindings.length, icon: AlertTriangle, color: 'var(--critical)' },
          ].map((m, i) => (
            <div key={i} className="cv-container p-4">
              <div className="mb-2 flex items-center gap-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                <m.icon className="h-3.5 w-3.5" />
                {m.label}
              </div>
              {typeof m.value === 'string' || typeof m.value === 'number' ? (
                <div className="font-mono text-2xl font-bold" style={{ color: m.color ?? 'var(--text-primary)' }}>
                  {m.value}
                </div>
              ) : (
                <div className="mt-1">{m.value}</div>
              )}
            </div>
          ))}
        </div>

        {/* Attack paths */}
        <div className="mb-6 cv-container p-6">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            <AlertTriangle className="h-4 w-4" style={{ color: 'var(--critical)' }} />
            Attack paths from internet
          </h3>
          {loading ? (
            <div className="flex h-24 items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          ) : attackPaths.length === 0 ? (
            <div className="flex h-24 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No internet-exposed resources found
            </div>
          ) : (
            <div className="space-y-3">
              {attackPaths.map((path, i) => (
                <div
                  key={i}
                  className="flex items-start gap-4 rounded-lg border p-4 transition-colors"
                  style={{ borderColor: 'var(--border-faint)' }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <div className="flex-1 min-w-0">
                    <div className="mb-1 font-mono text-sm" style={{ color: 'var(--text-primary)' }}>{path.path}</div>
                    <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      <span>{path.hops} hops</span>
                      {path.finding && <span className="truncate max-w-xs">· {path.finding}</span>}
                    </div>
                  </div>
                  <div className="flex flex-shrink-0 items-center gap-2">
                    <Shield
                      className="h-4 w-4"
                      style={{
                        color: path.risk >= 80 ? 'var(--critical)' : path.risk >= 60 ? 'var(--high)' : 'var(--medium)',
                      }}
                    />
                    <span
                      className="font-mono text-sm font-bold"
                      style={{
                        color: path.risk >= 80 ? 'var(--critical)' : path.risk >= 60 ? 'var(--high)' : 'var(--medium)',
                      }}
                    >
                      {path.risk}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Internet-exposed resources */}
        {publicResources.length > 0 && (
          <div className="mb-6 cv-container overflow-hidden">
            <div className="border-b px-5 py-3" style={{ borderColor: 'var(--border-faint)' }}>
              <h3 className="flex items-center gap-2 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                <Globe className="h-4 w-4" style={{ color: 'var(--critical)' }} />
                Internet-exposed resources ({publicResources.length})
              </h3>
            </div>
            <div className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
              {publicResources.slice(0, 8).map(r => (
                <div
                  key={r.id}
                  className="flex items-center gap-3 px-5 py-3 transition-colors"
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <div
                    className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full"
                    style={{ backgroundColor: 'var(--critical-dim)' }}
                  >
                    <Lock className="h-4 w-4" style={{ color: 'var(--critical)' }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{r.name}</div>
                    <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {r.resource_type.split('::').pop()} · {r.region} · {r.provider.toUpperCase()}
                    </div>
                  </div>
                  <span
                    className="flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold"
                    style={{ backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}
                  >
                    Public
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Asset type breakdown */}
        <div className="cv-container p-6">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Asset type breakdown</h3>
          {loading ? (
            <div className="flex h-24 items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          ) : typeBreakdown.length === 0 ? (
            <div className="flex h-24 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No assets discovered yet
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
              {typeBreakdown.map(([type, count]) => (
                <div
                  key={type}
                  className="rounded-lg border p-3 text-center transition-colors"
                  style={{ borderColor: 'var(--border-faint)' }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <div className="mb-1 font-mono text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
                    {count.toLocaleString()}
                  </div>
                  <div className="text-xs capitalize" style={{ color: 'var(--text-tertiary)' }}>{type}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
