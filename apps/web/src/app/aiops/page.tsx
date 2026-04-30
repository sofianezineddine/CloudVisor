'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { Brain, TrendingDown, CheckCircle2, AlertTriangle, RefreshCw, Loader2, Lightbulb, Zap } from 'lucide-react';
import apiClient, { Finding } from '@/lib/api/apiClient';

// ─── AI insight generator ─────────────────────────────────────────────────────

function generateInsights(findings: Finding[]): Array<{ title: string; description: string; impact: string; severity: 'high' | 'medium' | 'low' }> {
  const insights: Array<{ title: string; description: string; impact: string; severity: 'high' | 'medium' | 'low' }> = [];

  const byResource = new Map<string, Finding[]>();
  for (const f of findings) {
    const key = f.resource_id || 'unknown';
    if (!byResource.has(key)) byResource.set(key, []);
    byResource.get(key)!.push(f);
  }

  for (const [resourceId, resourceFindings] of Array.from(byResource.entries())) {
    if (resourceFindings.length >= 2) {
      const name = resourceFindings[0].resource_name || resourceId;
      const hasCritical = resourceFindings.some(f => f.severity === 'CRITICAL');
      insights.push({
        title: `${resourceFindings.length} correlated findings on ${name}`,
        description: `Multiple security issues detected on the same resource. Fixing the root cause could resolve all ${resourceFindings.length} findings at once.`,
        impact: `Resolves ${resourceFindings.length} findings`,
        severity: hasCritical ? 'high' : 'medium',
      });
    }
  }

  const byRule = new Map<string, Finding[]>();
  for (const f of findings) {
    if (!byRule.has(f.rule_id)) byRule.set(f.rule_id, []);
    byRule.get(f.rule_id)!.push(f);
  }

  for (const [ruleId, ruleFindings] of Array.from(byRule.entries())) {
    if (ruleFindings.length >= 3) {
      insights.push({
        title: `${ruleFindings.length} resources affected by the same misconfiguration`,
        description: `Rule "${ruleFindings[0].title}" is triggered on ${ruleFindings.length} resources. A policy-level fix would resolve all instances.`,
        impact: `Resolves ${ruleFindings.length} findings`,
        severity: ruleFindings[0].severity === 'CRITICAL' ? 'high' : 'medium',
      });
    }
  }

  if (insights.length === 0 && findings.length > 0) {
    insights.push({
      title: 'Security posture analysis complete',
      description: `Analyzed ${findings.length} findings. No correlated patterns detected — each finding appears to be an independent issue.`,
      impact: 'Individual remediation recommended',
      severity: 'low',
    });
  }

  return insights.slice(0, 5);
}

export default function AIOpsPage() {
  const [findings, setFindings] = React.useState<Finding[]>([]);
  const [stats, setStats] = React.useState<Record<string, any>>({});
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    document.title = 'AIOps - CloudVisor';
  }, []);

  React.useEffect(() => {
    Promise.allSettled([
      apiClient.findings.list({ limit: 100 }),
      apiClient.findings.stats(),
    ]).then(([findingsRes, statsRes]) => {
      if (findingsRes.status === 'fulfilled') setFindings((findingsRes.value?.data as Finding[]) ?? []);
      if (statsRes.status === 'fulfilled') setStats((statsRes.value?.data as any) ?? {});
      setLoading(false);
    });
  }, []);

  const insights = React.useMemo(() => generateInsights(findings), [findings]);
  const totalFindings = stats?.total ?? 0;
  const openFindings = stats?.by_status?.open ?? 0;
  const resolvedFindings = stats?.by_status?.resolved ?? 0;
  const suppressionRate = totalFindings > 0 ? Math.round(((totalFindings - openFindings) / totalFindings) * 100) : 0;

  const metrics = [
    { label: 'Noise reduction', value: loading ? '—' : `${suppressionRate}%`, color: 'var(--success)', bg: 'var(--success-dim)', icon: TrendingDown },
    { label: 'Resolved findings', value: loading ? '—' : resolvedFindings, color: 'var(--accent)', bg: 'var(--accent-dim)', icon: CheckCircle2 },
    { label: 'AI insights', value: loading ? '—' : insights.length, color: 'var(--medium)', bg: 'var(--medium-dim)', icon: Lightbulb },
    { label: 'Open findings', value: loading ? '—' : openFindings, color: 'var(--critical)', bg: 'var(--critical-dim)', icon: AlertTriangle },
  ];

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'AIOps' }]}>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>AIOps — Intelligence Layer</h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>ML-powered noise reduction and risk prioritization</p>
          </div>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={() => window.location.reload()}>
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Refresh
          </Button>
        </div>

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

        {/* AI Insights */}
        <div className="mb-6 cv-container p-6">
          <div className="mb-4 flex items-center gap-2">
            <Brain className="h-4 w-4" style={{ color: 'var(--accent)' }} />
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>AI-powered insights</h3>
          </div>
          {loading ? (
            <div className="flex h-24 items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent)' }} />
            </div>
          ) : insights.length === 0 ? (
            <div className="flex h-24 flex-col items-center justify-center gap-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
              <CheckCircle2 className="h-6 w-6" style={{ color: 'var(--success)' }} />
              Connect a cloud account to generate AI insights
            </div>
          ) : (
            <div className="space-y-3">
              {insights.map((insight, i) => (
                <div
                  key={i}
                  className="rounded-lg border p-4"
                  style={
                    insight.severity === 'high'
                      ? { borderColor: 'var(--critical-border)', backgroundColor: 'var(--critical-bg)' }
                      : insight.severity === 'medium'
                      ? { borderColor: 'var(--medium-border)', backgroundColor: 'var(--medium-bg)' }
                      : { borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-elevated)' }
                  }
                >
                  <div className="mb-1 flex items-start gap-2">
                    <Lightbulb
                      className="mt-0.5 h-4 w-4 flex-shrink-0"
                      style={{
                        color: insight.severity === 'high'
                          ? 'var(--critical)'
                          : insight.severity === 'medium'
                          ? 'var(--medium)'
                          : 'var(--accent)',
                      }}
                    />
                    <div>
                      <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{insight.title}</div>
                      <div className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>{insight.description}</div>
                      <div className="mt-2 flex items-center gap-1.5">
                        <Zap className="h-3 w-3" style={{ color: 'var(--accent)' }} />
                        <span className="text-xs font-medium" style={{ color: 'var(--accent)' }}>{insight.impact}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top findings to remediate */}
        {findings.length > 0 && (
          <div className="cv-container overflow-hidden">
            <div className="border-b px-5 py-3" style={{ borderColor: 'var(--border-faint)' }}>
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                Prioritized remediation queue
              </h3>
            </div>
            <div className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
              {findings
                .filter(f => f.status === 'open')
                .sort((a, b) => {
                  const order = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 };
                  return (order[a.severity] ?? 5) - (order[b.severity] ?? 5);
                })
                .slice(0, 8)
                .map(f => (
                  <div
                    key={f.id}
                    className="flex items-center gap-3 px-5 py-3 transition-colors"
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <SeverityBadge severity={f.severity} size="sm" />
                    <div className="flex-1 min-w-0">
                      <div className="truncate text-sm" style={{ color: 'var(--text-primary)' }}>{f.title}</div>
                      <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                        {f.resource_name || f.resource_id}
                        {f.remediation && ` · ${f.remediation.slice(0, 60)}…`}
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </AppLayout>
    </ProtectedRoute>
  );
}
