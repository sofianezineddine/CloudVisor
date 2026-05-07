'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import {
  Download, CheckCircle2, XCircle, Loader2, AlertTriangle,
  RefreshCw, ChevronRight, ChevronDown, Shield, X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useScopeStore } from '@/stores/scope';
import { NoAccountsConnectedEmptyState } from '@/components/ui/no-accounts-empty-state';
import apiClient from '@/lib/api/apiClient';
import type { CompliancePosture, ComplianceControl } from '@/lib/api/policy';

// ─── All 12 spec frameworks with provider scope mapping ──────────────────────

const FRAMEWORKS: { key: string; label: string; short: string; providers: string[] | null }[] = [
  // Provider-specific CIS benchmarks — only shown when that provider is in scope
  { key: 'CIS-AWS',     label: 'CIS AWS Foundations Benchmark v3.0', short: 'CIS AWS',   providers: ['aws']   },
  { key: 'CIS-Azure',   label: 'CIS Azure Foundations Benchmark',    short: 'CIS Azure', providers: ['azure'] },
  { key: 'CIS-GCP',     label: 'CIS GCP Foundations Benchmark',      short: 'CIS GCP',   providers: ['gcp']   },
  { key: 'CIS-OCI',     label: 'CIS OCI Foundations Benchmark',      short: 'CIS OCI',   providers: ['oci']   },
  // Cross-provider frameworks — always shown regardless of scope
  { key: 'SOC2',        label: 'SOC 2 Type II',                      short: 'SOC 2',     providers: null },
  { key: 'PCI-DSS',     label: 'PCI-DSS v4.0',                       short: 'PCI-DSS',   providers: null },
  { key: 'HIPAA',       label: 'HIPAA',                              short: 'HIPAA',     providers: null },
  { key: 'ISO27001',    label: 'ISO/IEC 27001:2022',                  short: 'ISO 27001', providers: null },
  { key: 'NIST-800-53', label: 'NIST SP 800-53 Rev 5',               short: 'NIST',      providers: null },
  { key: 'GDPR',        label: 'GDPR',                               short: 'GDPR',      providers: null },
  { key: 'FedRAMP',     label: 'FedRAMP',                            short: 'FedRAMP',   providers: null },
  { key: 'CCPA',        label: 'CCPA',                               short: 'CCPA',      providers: null },
];

/** Filter frameworks to those relevant for the current provider scope. */
function getVisibleFrameworks(provider: string | null) {
  if (!provider) return FRAMEWORKS;
  return FRAMEWORKS.filter(fw =>
    fw.providers === null || fw.providers.includes(provider)
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function scoreColor(score: number): string {
  if (score >= 80) return 'var(--success)';
  if (score >= 60) return 'var(--warning)';
  return 'var(--critical)';
}

function ScoreBar({ score, height = 6 }: { score: number; height?: number }) {
  return (
    <div className="w-full overflow-hidden rounded-full" style={{ height, backgroundColor: 'var(--border-default)' }}>
      <div
        className="h-full rounded-full transition-all duration-500 ease-out"
        style={{ width: `${score}%`, backgroundColor: scoreColor(score) }}
      />
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    CRITICAL: { bg: 'rgba(248,81,73,0.12)', text: '#f85149' },
    HIGH:     { bg: 'rgba(249,115,22,0.12)', text: '#f97316' },
    MEDIUM:   { bg: 'rgba(251,191,36,0.12)', text: '#fbbf24' },
    LOW:      { bg: 'rgba(63,185,80,0.12)',  text: '#3fb950' },
  };
  const c = colors[severity?.toUpperCase()] || colors.LOW;
  return (
    <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-semibold"
      style={{ background: c.bg, color: c.text }}>
      {severity}
    </span>
  );
}

// ─── Control drill-down panel ─────────────────────────────────────────────────

function ControlPanel({
  controls,
  onClose,
}: {
  controls: ComplianceControl[];
  onClose: () => void;
}) {
  const passing = controls.filter(c => c.status === 'pass');
  const failing = controls.filter(c => c.status === 'fail');
  const na = controls.filter(c => c.status === 'not_applicable');

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex flex-col shadow-2xl"
      style={{ width: 420, backgroundColor: 'var(--bg-surface)', borderLeft: '1px solid var(--border-default)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border-default)' }}>
        <div>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            Controls ({controls.length})
          </h3>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
            {passing.length} passing · {failing.length} failing · {na.length} N/A
          </p>
        </div>
        <button onClick={onClose} className="rounded p-1 transition-colors"
          style={{ color: 'var(--text-tertiary)' }}
          onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'}
          onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}>
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Controls list */}
      <div className="flex-1 overflow-y-auto">
        {controls.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-2">
            <Shield className="h-8 w-8" style={{ color: 'var(--text-tertiary)' }} />
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No controls mapped</p>
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
            {controls.map(ctrl => (
              <div key={ctrl.id} className="px-5 py-3">
                <div className="flex items-start gap-3">
                  {ctrl.status === 'pass' ? (
                    <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0" style={{ color: 'var(--success)' }} />
                  ) : ctrl.status === 'fail' ? (
                    <XCircle className="h-4 w-4 mt-0.5 flex-shrink-0" style={{ color: 'var(--critical)' }} />
                  ) : (
                    <div className="h-4 w-4 mt-0.5 flex-shrink-0 rounded-full border-2"
                      style={{ borderColor: 'var(--text-tertiary)' }} />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>{ctrl.id}</span>
                      <SeverityBadge severity={ctrl.severity} />
                    </div>
                    <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{ctrl.title}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                      Rule: <span className="font-mono">{ctrl.rule_id}</span>
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Framework card ───────────────────────────────────────────────────────────

function FrameworkCard({
  fw,
  posture,
  active,
  onClick,
}: {
  fw: { key: string; label: string; short: string };
  posture: CompliancePosture | null;
  active: boolean;
  onClick: () => void;
}) {
  const score = posture?.percentage ?? null;

  return (
    <button
      onClick={onClick}
      className="flex-shrink-0 text-left rounded-lg border p-3 transition-all"
      style={{
        width: 160,
        borderColor: active ? 'var(--accent)' : 'var(--border-default)',
        backgroundColor: active ? 'var(--accent-dim)' : 'var(--bg-surface)',
        boxShadow: active ? '0 0 0 1px var(--accent)' : 'none',
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>{fw.short}</span>
        {score !== null ? (
          <span className="text-sm font-bold font-mono ml-1 flex-shrink-0" style={{ color: scoreColor(score) }}>
            {score}%
          </span>
        ) : (
          <span className="text-xs flex-shrink-0" style={{ color: 'var(--text-tertiary)' }}>—</span>
        )}
      </div>
      {score !== null && <ScoreBar score={score} height={4} />}
      {posture && (
        <div className="mt-2 flex gap-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
          <span style={{ color: 'var(--success)' }}>✓ {posture.passing}</span>
          <span style={{ color: posture.failing > 0 ? 'var(--critical)' : 'var(--text-tertiary)' }}>
            ✗ {posture.failing}
          </span>
        </div>
      )}
    </button>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function CompliancePage() {
  const [activeKey, setActiveKey] = React.useState<string>('CIS-AWS');
  const [postures, setPostures] = React.useState<Record<string, CompliancePosture>>({});
  const [loading, setLoading] = React.useState(true);
  const [loadingFramework, setLoadingFramework] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedControls, setSelectedControls] = React.useState<ComplianceControl[] | null>(null);
  const [expandedDomain, setExpandedDomain] = React.useState<string | null>(null);

  const accountIds = useScopeStore(s => s.accountIds);
  const scopeProvider = useScopeStore(s => s.provider); // 'aws' | 'azure' | 'gcp' | 'oci'

  // Frameworks visible for the current provider scope
  const visibleFrameworks = React.useMemo(
    () => getVisibleFrameworks(scopeProvider),
    [scopeProvider]
  );

  // When provider scope changes, reset active framework to the first visible one
  // and clear posture cache (different provider = different data)
  React.useEffect(() => {
    const first = visibleFrameworks[0]?.key;
    if (first) setActiveKey(first);
    setPostures({});
    setExpandedDomain(null);
    setSelectedControls(null);
  }, [scopeProvider]); // eslint-disable-line react-hooks/exhaustive-deps

  React.useEffect(() => { document.title = 'Compliance - CloudVisor'; }, []);

  // Load all frameworks on mount
  const fetchAll = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Use gateway /v1/compliance instead of calling policy service directly
      const resp = await apiClient.compliance.list();
      const frameworks = (resp?.data as any[]) ?? [];
      const map: Record<string, CompliancePosture> = {};
      for (const p of frameworks) {
        map[p.framework] = p;
      }
      setPostures(map);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load compliance data');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => { fetchAll(); }, [fetchAll]);

  // Load a specific framework when tab changes
  const loadFramework = React.useCallback(async (key: string) => {
    if (postures[key]?.controls?.length) return; // already loaded
    setLoadingFramework(true);
    try {
      // Use gateway /v1/compliance/{framework} instead of calling policy service directly
      const resp = await apiClient.compliance.list({ framework: key });
      const posture = (resp?.data as any)?.[0] ?? resp?.data;
      if (posture) {
        setPostures(prev => ({ ...prev, [key]: posture }));
      }
    } catch {
      // non-fatal — keep existing data
    } finally {
      setLoadingFramework(false);
    }
  }, [postures]);

  React.useEffect(() => {
    if (activeKey) loadFramework(activeKey);
  }, [activeKey, loadFramework]);

  const active = postures[activeKey];
  const activeFw = visibleFrameworks.find(f => f.key === activeKey) ?? visibleFrameworks[0];

  // Group controls by severity for the heatmap
  const controlsBySeverity = React.useMemo(() => {
    if (!active?.controls) return {};
    const groups: Record<string, ComplianceControl[]> = {};
    for (const c of active.controls) {
      const sev = c.severity || 'MEDIUM';
      if (!groups[sev]) groups[sev] = [];
      groups[sev].push(c);
    }
    return groups;
  }, [active]);

  const handleExport = () => {
    if (!active) return;
    const rows = active.controls.map(c =>
      [c.id, c.title, c.severity, c.status, c.rule_id].map(v => `"${v}"`).join(',')
    );
    const csv = ['Control ID,Title,Severity,Status,Rule ID', ...rows].join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = `compliance-${activeKey}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Compliance' }]}>
        {accountIds.length === 0 ? (
          <NoAccountsConnectedEmptyState />
        ) : (
          <div className="flex flex-col h-full">
            {/* Page header */}
            <div className="flex items-center justify-between mb-5">
              <div>
                <h1 className="text-2xl font-normal" style={{ color: 'var(--text-primary)' }}>Compliance</h1>
                <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                  Track posture across {visibleFrameworks.length} compliance frameworks
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={fetchAll}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 border rounded px-3 py-1.5 text-sm transition-colors disabled:opacity-50"
                  style={{ borderColor: 'var(--border-default)', color: 'var(--text-primary)', backgroundColor: 'var(--bg-surface)' }}
                >
                  {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                  Refresh
                </button>
                <button
                  onClick={handleExport}
                  disabled={!active}
                  className="inline-flex items-center gap-1.5 border rounded px-3 py-1.5 text-sm transition-colors disabled:opacity-50"
                  style={{ borderColor: 'var(--border-default)', color: 'var(--text-primary)', backgroundColor: 'var(--bg-surface)' }}
                >
                  <Download className="h-3.5 w-3.5" />
                  Export CSV
                </button>
              </div>
            </div>

            {error && (
              <div className="mb-4 flex items-center gap-2 rounded-lg border p-3 text-sm"
                style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}>
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                {error} — showing estimated data
              </div>
            )}

            {/* ── Frameworks row — horizontal scrollable strip ─────────── */}
            <div className="flex-shrink-0 mb-5">
              <p className="text-xs font-semibold uppercase tracking-wider mb-3"
                style={{ color: 'var(--text-tertiary)' }}>Frameworks</p>
              {loading ? (
                <div className="flex items-center gap-3">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-20 w-44 rounded-lg skeleton flex-shrink-0" />
                  ))}
                </div>
              ) : (
                <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: 'none' }}>
                  {visibleFrameworks.map(fw => (
                    <FrameworkCard
                      key={fw.key}
                      fw={fw}
                      posture={postures[fw.key] || null}
                      active={activeKey === fw.key}
                      onClick={() => { setActiveKey(fw.key); setSelectedControls(null); setExpandedDomain(null); }}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* ── Detail panel — fills remaining height ───────────────── */}
            <div className="flex-1 min-h-0 overflow-y-auto">                {loadingFramework ? (
                  <div className="flex items-center justify-center h-48">
                    <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
                  </div>
                ) : active ? (
                  <div className="space-y-4">
                    {/* Summary card */}
                    <div className="rounded-lg border p-5"
                      style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                            {active.display_name || activeFw.label}
                          </h2>
                          <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                            {active.total_controls} controls evaluated
                          </p>
                        </div>
                        <div className="text-right">
                          <div className="text-3xl font-bold font-mono"
                            style={{ color: scoreColor(active.percentage) }}>
                            {active.percentage}%
                          </div>
                          <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>compliant</div>
                        </div>
                      </div>
                      <ScoreBar score={active.percentage} height={8} />
                      <div className="mt-3 flex gap-5 text-sm">
                        <span className="flex items-center gap-1.5" style={{ color: 'var(--success)' }}>
                          <CheckCircle2 className="h-4 w-4" />
                          {active.passing} passing
                        </span>
                        <span className="flex items-center gap-1.5" style={{ color: 'var(--critical)' }}>
                          <XCircle className="h-4 w-4" />
                          {active.failing} failing
                        </span>
                        {active.not_applicable > 0 && (
                          <span className="flex items-center gap-1.5" style={{ color: 'var(--text-tertiary)' }}>
                            {active.not_applicable} N/A
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Controls by severity — spec: heatmap */}
                    {Object.keys(controlsBySeverity).length > 0 && (
                      <div className="rounded-lg border"
                        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
                        <div className="px-5 py-3 border-b" style={{ borderColor: 'var(--border-default)' }}>
                          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                            Controls by severity
                          </h3>
                        </div>
                        <div className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
                          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => {
                            const ctrls = controlsBySeverity[sev] || [];
                            if (!ctrls.length) return null;
                            const failing = ctrls.filter(c => c.status === 'fail');
                            const passing = ctrls.filter(c => c.status === 'pass');
                            const isExpanded = expandedDomain === sev;
                            return (
                              <div key={sev}>
                                <button
                                  className="w-full flex items-center gap-3 px-5 py-3 text-left transition-colors"
                                  style={{ backgroundColor: 'transparent' }}
                                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'}
                                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'}
                                  onClick={() => {
                                    setExpandedDomain(isExpanded ? null : sev);
                                    setSelectedControls(isExpanded ? null : ctrls);
                                  }}
                                >
                                  <SeverityBadge severity={sev} />
                                  <span className="flex-1 text-sm" style={{ color: 'var(--text-primary)' }}>
                                    {ctrls.length} control{ctrls.length !== 1 ? 's' : ''}
                                  </span>
                                  <span className="text-xs" style={{ color: 'var(--success)' }}>
                                    {passing.length} pass
                                  </span>
                                  {failing.length > 0 && (
                                    <span className="text-xs ml-2" style={{ color: 'var(--critical)' }}>
                                      {failing.length} fail
                                    </span>
                                  )}
                                  {isExpanded
                                    ? <ChevronDown className="h-4 w-4 ml-2" style={{ color: 'var(--text-tertiary)' }} />
                                    : <ChevronRight className="h-4 w-4 ml-2" style={{ color: 'var(--text-tertiary)' }} />
                                  }
                                </button>

                                {/* Inline control list on expand */}
                                {isExpanded && (
                                  <div className="border-t" style={{ borderColor: 'var(--border-faint)' }}>
                                    {ctrls.map(ctrl => (
                                      <div key={ctrl.id}
                                        className="flex items-start gap-3 px-8 py-2.5 border-b last:border-0"
                                        style={{ borderColor: 'var(--border-faint)' }}>
                                        {ctrl.status === 'pass'
                                          ? <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0" style={{ color: 'var(--success)' }} />
                                          : ctrl.status === 'fail'
                                          ? <XCircle className="h-4 w-4 mt-0.5 flex-shrink-0" style={{ color: 'var(--critical)' }} />
                                          : <div className="h-4 w-4 mt-0.5 flex-shrink-0 rounded-full border-2" style={{ borderColor: 'var(--text-tertiary)' }} />
                                        }
                                        <div className="flex-1 min-w-0">
                                          <div className="flex items-center gap-2">
                                            <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>{ctrl.id}</span>
                                          </div>
                                          <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{ctrl.title}</p>
                                          <p className="text-xs mt-0.5 font-mono" style={{ color: 'var(--text-tertiary)' }}>{ctrl.rule_id}</p>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Empty state when no controls */}
                    {active.total_controls === 0 && (
                      <div className="rounded-lg border p-10 text-center"
                        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
                        <Shield className="h-10 w-10 mx-auto mb-3" style={{ color: 'var(--text-tertiary)' }} />
                        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                          No controls mapped for {activeFw.label}
                        </p>
                        <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                          Rules with {activeKey} compliance mappings will appear here after a scan.
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-48">
                    <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
                  </div>
                )}
              </div>
          </div>
        )}
      </AppLayout>
    </ProtectedRoute>
  );
}
