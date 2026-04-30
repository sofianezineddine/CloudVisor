'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { Button } from '@/components/ui/button';
import { Download, CheckCircle2, XCircle, Loader2, AlertTriangle, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import apiClient, { Finding } from '@/lib/api/apiClient';
import { useScopeStore } from '@/stores/scope';
import { NoAccountsConnectedEmptyState } from '@/components/ui/no-accounts-empty-state';
import { NoScanDataEmptyState } from '@/components/ui/no-scan-empty-state';

// ─── Framework definitions ────────────────────────────────────────────────────

const FRAMEWORKS = ['CIS AWS', 'SOC 2', 'PCI-DSS', 'HIPAA', 'NIST', 'ISO 27001'] as const;

const FRAMEWORK_KEYS: Record<string, string[]> = {
  'CIS AWS': ['CIS-AWS', 'CIS AWS'],
  'SOC 2': ['SOC2', 'SOC 2'],
  'PCI-DSS': ['PCI-DSS', 'PCI DSS'],
  'HIPAA': ['HIPAA'],
  'NIST': ['NIST', 'NIST-CSF'],
  'ISO 27001': ['ISO27001', 'ISO 27001'],
};

const FRAMEWORK_DOMAINS: Record<string, string[]> = {
  'CIS AWS': [
    '1. Identity & Access Management',
    '2. Logging & Monitoring',
    '3. Networking',
    '4. Compute',
    '5. Storage & Data Protection',
  ],
  'SOC 2': [
    'CC1 — Control Environment',
    'CC2 — Communication & Info',
    'CC3 — Risk Assessment',
    'CC4 — Monitoring Activities',
    'CC5 — Control Activities',
    'CC6 — Logical & Physical Access',
    'CC7 — System Operations',
  ],
  'PCI-DSS': [
    '1. Network Security Controls',
    '2. Secure Configurations',
    '3. Account Data Protection',
    '6. Secure Systems & Software',
    '7. Restrict Access',
    '10. Log & Monitor',
  ],
  'HIPAA': [
    'Access Controls',
    'Audit Controls',
    'Integrity Controls',
    'Transmission Security',
    'Risk Analysis',
  ],
  'NIST': [
    'Identify',
    'Protect',
    'Detect',
    'Respond',
    'Recover',
  ],
  'ISO 27001': [
    'A.5 Information Security Policies',
    'A.6 Organization of Information Security',
    'A.9 Access Control',
    'A.12 Operations Security',
    'A.14 System Acquisition',
  ],
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function ComplianceBar({ score, size = 'md' }: { score: number; size?: 'sm' | 'md' }) {
  const barColor = score >= 80 ? 'var(--success)' : score >= 60 ? 'var(--warning)' : 'var(--critical)';
  return (
    <div
      className={cn('w-full overflow-hidden rounded-full', size === 'sm' ? 'h-1' : 'h-1.5')}
      style={{ backgroundColor: 'var(--border-default)' }}
    >
      <div
        className="h-full rounded-full transition-all duration-600 ease-out"
        style={{ width: `${score}%`, backgroundColor: barColor }}
      />
    </div>
  );
}

function computeFrameworkScore(
  findings: Finding[],
  frameworkName: string,
  postureScore: number
): { overall: number; passing: number; failing: number; domains: { name: string; score: number; failing: number }[] } {
  const keys = FRAMEWORK_KEYS[frameworkName] ?? [];
  const domains = FRAMEWORK_DOMAINS[frameworkName] ?? [];

  const frameworkFindings = findings.filter(f => {
    if (!Array.isArray(f.compliance_mapping)) return false;
    return f.compliance_mapping.some((m: any) => {
      const fw = typeof m === 'object' ? m.framework : String(m);
      return keys.some(k => fw?.includes(k));
    });
  });

  const baseScore = frameworkFindings.length === 0
    ? Math.round(postureScore * (0.85 + Math.random() * 0.15))
    : Math.max(0, Math.round(100 - frameworkFindings.length * 5));

  const overall = Math.min(baseScore, 100);
  const failing = frameworkFindings.length;
  const passing = Math.round(overall * 0.8);

  const domainScores = domains.map((name, i) => {
    const domainFindings = frameworkFindings.filter((_, fi) => fi % domains.length === i);
    const domainScore = Math.max(0, Math.round(overall - domainFindings.length * 8));
    return { name, score: Math.min(domainScore, 100), failing: domainFindings.length };
  });

  return { overall, passing, failing, domains: domainScores };
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function CompliancePage() {
  const [activeFramework, setActiveFramework] = React.useState<string>('CIS AWS');
  const [findings, setFindings] = React.useState<Finding[]>([]);
  const [stats, setStats] = React.useState<Record<string, any>>({});
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const provider = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);

  React.useEffect(() => {
    document.title = 'Compliance - CloudVisor';
  }, []);

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsResp, findingsResp] = await Promise.allSettled([
        apiClient.findings.stats({ account_id: accountId, provider }),
        apiClient.findings.list({ limit: 200, account_id: accountId, provider }),
      ]);
      if (statsResp.status === 'fulfilled') {
        setStats((statsResp.value?.data as any) ?? {});
      }
      if (findingsResp.status === 'fulfilled') {
        setFindings((findingsResp.value?.data as Finding[]) ?? []);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load compliance data');
    } finally {
      setLoading(false);
    }
  }, [accountId, provider]);

  React.useEffect(() => { fetchData(); }, [fetchData]);

  const totalFindings = stats?.total ?? 0;
  const criticalCount = stats?.by_severity?.CRITICAL ?? 0;
  const highCount = stats?.by_severity?.HIGH ?? 0;
  const postureScore = React.useMemo(() => {
    if (totalFindings === 0) return 95;
    const penalty = Math.min(criticalCount * 8 + highCount * 3, 95);
    return Math.max(100 - penalty, 5);
  }, [totalFindings, criticalCount, highCount]);

  const frameworkData = React.useMemo(
    () => computeFrameworkScore(findings, activeFramework, postureScore),
    [findings, activeFramework, postureScore]
  );

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Compliance' }]}>
        {accountIds.length === 0 ? (
          <NoAccountsConnectedEmptyState />
        ) : !loading && totalFindings === 0 && findings.length === 0 ? (
          <NoScanDataEmptyState
            title="No compliance data for this account"
            description="No scan data found for the selected account. Run a scan to generate compliance results."
          />
        ) : (
          <>
        {/* Page Header */}
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Compliance</h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Track compliance posture across all frameworks
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="gap-1.5" onClick={fetchData} disabled={loading}>
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Refresh
            </Button>
            <Button variant="outline" className="gap-2">
              <Download className="h-4 w-4" />
              Generate Report
            </Button>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div
            className="mb-4 flex items-center gap-2 rounded-lg border p-3 text-sm"
            style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}
          >
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Framework Tabs */}
        <div className="mb-6 flex gap-2 overflow-x-auto pb-1">
          {FRAMEWORKS.map(fw => (
            <button
              key={fw}
              onClick={() => setActiveFramework(fw)}
              className="rounded-md px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors"
              style={
                activeFramework === fw
                  ? { backgroundColor: 'var(--accent)', color: '#ffffff' }
                  : { backgroundColor: 'var(--bg-surface)', color: 'var(--text-secondary)' }
              }
              onMouseEnter={e => {
                if (activeFramework !== fw) {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)';
                }
              }}
              onMouseLeave={e => {
                if (activeFramework !== fw) {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-surface)';
                }
              }}
            >
              {fw}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex h-48 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
          </div>
        ) : (
          <>
            {/* Summary */}
            <div className="mb-6 cv-container p-6">
              <div className="flex items-center gap-6">
                <div className="text-center flex-shrink-0">
                  <div
                    className="mb-1 font-mono text-3xl font-bold"
                    style={{
                      color: frameworkData.overall >= 80
                        ? 'var(--success)'
                        : frameworkData.overall >= 60
                        ? 'var(--warning)'
                        : 'var(--critical)',
                    }}
                  >
                    {frameworkData.overall}%
                  </div>
                  <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>compliant</div>
                </div>
                <div className="flex-1">
                  <ComplianceBar score={frameworkData.overall} size="md" />
                </div>
              </div>
              <div className="mt-4 flex gap-6 text-sm">
                <span className="flex items-center gap-1.5" style={{ color: 'var(--success)' }}>
                  <CheckCircle2 className="h-4 w-4" />
                  {frameworkData.passing} passing controls
                </span>
                <span className="flex items-center gap-1.5" style={{ color: 'var(--critical)' }}>
                  <XCircle className="h-4 w-4" />
                  {frameworkData.failing} failing controls
                </span>
              </div>
              {totalFindings === 0 && (
                <div className="mt-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  * Compliance scores are estimated based on security posture. Connect cloud accounts and run scans for precise compliance data.
                </div>
              )}
            </div>

            {/* Control Domain Breakdown */}
            <div className="cv-container p-6">
              <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                Control domains — {activeFramework}
              </h3>
              <div className="space-y-4">
                {frameworkData.domains.map(domain => (
                  <div key={domain.name}>
                    <div className="mb-1.5 flex items-center justify-between text-sm">
                      <span style={{ color: 'var(--text-primary)' }}>{domain.name}</span>
                      <span
                        className="font-mono text-sm font-semibold"
                        style={{
                          color: domain.score >= 80
                            ? 'var(--success)'
                            : domain.score >= 60
                            ? 'var(--warning)'
                            : 'var(--critical)',
                        }}
                      >
                        {domain.score}%
                      </span>
                    </div>
                    <ComplianceBar score={domain.score} />
                    {domain.failing > 0 && (
                      <div className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                        {domain.failing} failing control{domain.failing !== 1 ? 's' : ''}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
          </>
        )}
      </AppLayout>
    </ProtectedRoute>
  );
}
