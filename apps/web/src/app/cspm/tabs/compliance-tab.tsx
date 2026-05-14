'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import {
  Shield, ChevronDown, ChevronUp, AlertTriangle,
} from 'lucide-react';
import {
  useCSPMCompliance, useCSPMFramework, useCSPMScans, useCSPMFindings,
} from '@/hooks/use-cspm';

const COMPLIANCE_FRAMEWORKS = ['CIS-AWS', 'SOC2', 'PCI-DSS', 'HIPAA', 'NIST-800-53', 'ISO27001', 'GDPR'];

function postureColor(score: number): string {
  if (score >= 80) return 'var(--success)';
  if (score >= 60) return 'var(--warning)';
  return 'var(--critical)';
}

function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded', className)} style={{ backgroundColor: 'var(--bg-elevated)' }} />;
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-4 flex items-center gap-2 rounded border p-3 text-sm"
      style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-bg)', color: 'var(--critical)' }}>
      <AlertTriangle className="h-4 w-4 flex-shrink-0" />
      {message}
    </div>
  );
}

// AWS Console table cell style
const cellStyle: React.CSSProperties = {
  padding: '8px 12px',
  borderBottom: '1px solid var(--border-default)',
  borderRight: '1px solid var(--border-default)',
  fontSize: '13px',
  color: 'var(--text-primary)',
  verticalAlign: 'middle',
};

const headerCellStyle: React.CSSProperties = {
  ...cellStyle,
  fontWeight: 700,
  fontSize: '12px',
  color: 'var(--text-secondary)',
  backgroundColor: 'var(--bg-elevated)',
  whiteSpace: 'nowrap',
};

const tableStyle: React.CSSProperties = {
  borderCollapse: 'collapse',
  width: '100%',
  border: '1px solid var(--border-default)',
};

function downloadControlCSV(ctrl: { id?: string; control_id?: string; title: string; status: string; finding_count?: number }) {
  const ctrlId = ctrl.id ?? ctrl.control_id ?? 'unknown';
  const rows = [
    'resource_name,account,region,status,last_checked',
    `"${ctrl.title}","—","—","${ctrl.status}","${new Date().toISOString()}"`,
  ];
  const csv = rows.join('\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `${ctrlId.replace(/[^a-z0-9]/gi, '_')}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function getDomainPrefix(controlId: string | undefined): string {
  if (!controlId) return 'Other';
  const m = controlId.match(/^([A-Za-z]*\d+)/);
  return m ? m[1] : controlId.split('.')[0] || controlId;
}

export function ComplianceTab() {
  const [activeFramework, setActiveFramework] = React.useState(COMPLIANCE_FRAMEWORKS[0]);
  const [expandedDomains, setExpandedDomains] = React.useState<Set<string>>(new Set());
  const { data: scansData, isLoading: scansLoading } = useCSPMScans();
  const { data: complianceData, isLoading: listLoading, error: listError } = useCSPMCompliance();
  const { data: frameworkData, isLoading: fwLoading, error: fwError } = useCSPMFramework(activeFramework);
  // Fetch real findings to compute compliance when policy service returns mock data
  const { data: findingsData } = useCSPMFindings({ status: 'open', page_size: 500 });

  const scans = Array.isArray(scansData) ? scansData : [];
  const hasScans = scans.length > 0;

  const frameworks = complianceData?.frameworks ?? [];
  const summary = frameworks.find(f => f.framework === activeFramework);
  const rawControls = frameworkData?.controls ?? summary?.controls ?? [];

  // Detect if the policy service is returning mock/placeholder data.
  // A sign of mock data: all controls pass AND there are open findings.
  const openFindings = findingsData?.items ?? [];
  const allControlsPass = rawControls.length > 0 && rawControls.every(c => c.status === 'pass');
  const hasMockData = allControlsPass && openFindings.length > 0;

  // When mock data is detected, recompute control status from real findings.
  const controls = React.useMemo(() => {
    if (!hasMockData) return rawControls;
    // Map open finding rule_ids to failing controls
    const failingRuleIds = new Set(openFindings.map(f => f.rule_id));
    return rawControls.map(ctrl => {
      const ctrlId = (ctrl as any).id ?? ctrl.control_id ?? ctrl.rule_id ?? '';
      const isFailing = failingRuleIds.has(ctrlId);
      const findingCount = openFindings.filter(f => f.rule_id === ctrlId).length;
      return {
        ...ctrl,
        status: isFailing ? 'fail' as const : 'pass' as const,
        finding_count: findingCount,
      };
    });
  }, [rawControls, hasMockData, openFindings]);

  // Group controls by domain
  const domainGroups = React.useMemo(() => {
    const map = new Map<string, typeof controls>();
    for (const ctrl of controls) {
      const ctrlId = (ctrl as any).id ?? ctrl.control_id ?? '';
      const domain = getDomainPrefix(ctrlId);
      if (!map.has(domain)) map.set(domain, []);
      map.get(domain)!.push(ctrl);
    }
    return Array.from(map.entries()).map(([domain, ctrls]) => {
      const passing = ctrls.filter(c => c.status === 'pass').length;
      const failing = ctrls.filter(c => c.status === 'fail').length;
      const pct = ctrls.length > 0 ? Math.round((passing / ctrls.length) * 100) : 0;
      return { domain, controls: ctrls, passing, failing, total: ctrls.length, pct };
    });
  }, [controls]);

  function toggleDomain(domain: string) {
    setExpandedDomains(prev => {
      const next = new Set(prev);
      if (next.has(domain)) next.delete(domain); else next.add(domain);
      return next;
    });
  }

  if (!scansLoading && !hasScans) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full"
          style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <Shield className="h-7 w-7" style={{ color: 'var(--text-tertiary)' }} />
        </div>
        <div>
          <div className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
            No compliance data for this account
          </div>
          <div className="text-xs max-w-xs" style={{ color: 'var(--text-secondary)' }}>
            Run a scan first to generate compliance results for this account.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {(listError || fwError) && <ErrorBanner message="Failed to load compliance data" />}

      {/* Framework selector */}
      <div className="mb-4 flex flex-wrap border-b" style={{ borderColor: 'var(--border-default)' }}>
        {COMPLIANCE_FRAMEWORKS.map(fw => {
          const fwData = frameworks.find(f => f.framework === fw);
          return (
            <button key={fw} onClick={() => { setActiveFramework(fw); setExpandedDomains(new Set()); }}
              className="px-4 py-2.5 text-sm transition-colors flex-shrink-0"
              style={{
                color: activeFramework === fw ? 'var(--text-primary)' : 'var(--text-link)',
                fontWeight: activeFramework === fw ? 700 : 400,
                borderBottom: activeFramework === fw ? '2px solid var(--aws-orange)' : '2px solid transparent',
                marginBottom: '-1px',
                backgroundColor: 'transparent',
              }}>
              {fw}
              {fwData && (
                <span className="ml-1.5 text-xs" style={{ color: postureColor(fwData.percentage) }}>
                  {fwData.percentage}%
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Summary bar */}
      {(listLoading || fwLoading) ? (
        <Skeleton className="h-16 mb-4" />
      ) : (summary || frameworkData) ? (() => {
        const d = frameworkData ?? summary!;
        // Recompute stats from real controls if mock data was detected
        const effectivePassing = hasMockData
          ? controls.filter(c => c.status === 'pass').length
          : d.passing;
        const effectiveFailing = hasMockData
          ? controls.filter(c => c.status === 'fail').length
          : d.failing;
        const effectiveTotal = controls.length || d.total_controls;
        const effectivePct = effectiveTotal > 0
          ? Math.round((effectivePassing / effectiveTotal) * 100)
          : d.percentage;
        return (
          <div className="mb-4 flex items-center gap-6 p-4 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <div>
              <div className="font-mono text-2xl font-bold" style={{ color: postureColor(effectivePct) }}>{effectivePct}%</div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{d.display_name || d.framework}</div>
            </div>
            <div className="flex-1 h-2 overflow-hidden rounded-full" style={{ backgroundColor: 'var(--border-default)' }}>
              <div className="h-full rounded-full" style={{ width: `${effectivePct}%`, backgroundColor: postureColor(effectivePct) }} />
            </div>
            <div className="flex gap-4 text-sm">
              <span style={{ color: 'var(--success)' }}>{effectivePassing} passing</span>
              <span style={{ color: 'var(--critical)' }}>{effectiveFailing} failing</span>
              <span style={{ color: 'var(--text-tertiary)' }}>{d.not_applicable} N/A</span>
            </div>
          </div>
        );
      })() : null}

      {/* Controls list — grouped by domain */}
      {(listLoading || fwLoading) ? (
        <div className="space-y-2">{[1,2,3,4,5].map(i => <Skeleton key={i} className="h-10" />)}</div>
      ) : domainGroups.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
          No control data available for {activeFramework}
        </div>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              {['Control ID', 'Title', 'Status', 'Findings', 'Download'].map(h => (
                <th key={h} style={headerCellStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {domainGroups.map(group => (
              <React.Fragment key={group.domain}>
                <tr
                  className="cursor-pointer"
                  onClick={() => toggleDomain(group.domain)}
                  style={{ backgroundColor: 'var(--bg-elevated)' }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--border-faint)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}>
                  <td style={{ ...cellStyle, fontWeight: 700 }} colSpan={2}>
                    <div className="flex items-center gap-2">
                      {expandedDomains.has(group.domain)
                        ? <ChevronUp className="h-3.5 w-3.5 flex-shrink-0" style={{ color: 'var(--text-secondary)' }} />
                        : <ChevronDown className="h-3.5 w-3.5 flex-shrink-0" style={{ color: 'var(--text-secondary)' }} />}
                      <span className="font-mono text-xs font-bold" style={{ color: 'var(--text-primary)' }}>Domain {group.domain}</span>
                      <div className="flex-1 h-1.5 overflow-hidden rounded-full ml-2" style={{ backgroundColor: 'var(--border-default)', maxWidth: '80px' }}>
                        <div className="h-full rounded-full" style={{ width: `${group.pct}%`, backgroundColor: postureColor(group.pct) }} />
                      </div>
                      <span className="text-xs font-semibold" style={{ color: postureColor(group.pct) }}>{group.pct}%</span>
                    </div>
                  </td>
                  <td style={cellStyle}>
                    <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{group.passing}/{group.total} passing</span>
                  </td>
                  <td style={cellStyle}>
                    {group.failing > 0 && <span className="text-xs font-semibold" style={{ color: 'var(--critical)' }}>{group.failing} failing</span>}
                  </td>
                  <td style={cellStyle} />
                </tr>
                {expandedDomains.has(group.domain) && group.controls.map(ctrl => {
                  const ctrlId = (ctrl as any).id ?? ctrl.control_id ?? '—';
                  return (
                  <tr key={ctrlId}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                    <td style={{ ...cellStyle, paddingLeft: '28px' }}><span className="font-mono text-xs">{ctrlId}</span></td>
                    <td style={{ ...cellStyle, maxWidth: '400px' }}>
                      <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{ctrl.title}</span>
                    </td>
                    <td style={cellStyle}>
                      <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold"
                        style={{
                          backgroundColor: ctrl.status === 'pass' ? 'var(--success-bg)' : ctrl.status === 'fail' ? 'var(--critical-bg)' : 'var(--bg-elevated)',
                          color: ctrl.status === 'pass' ? 'var(--success)' : ctrl.status === 'fail' ? 'var(--critical)' : 'var(--text-tertiary)',
                          border: `1px solid ${ctrl.status === 'pass' ? 'var(--low-border)' : ctrl.status === 'fail' ? 'var(--critical-border)' : 'var(--border-default)'}`,
                        }}>
                        {ctrl.status === 'pass' ? 'PASS' : ctrl.status === 'fail' ? 'FAIL' : 'N/A'}
                      </span>
                    </td>
                    <td style={cellStyle}>
                      {(ctrl.finding_count ?? 0) > 0 ? (
                        <span className="text-sm font-semibold" style={{ color: 'var(--critical)' }}>{ctrl.finding_count}</span>
                      ) : (
                        <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>0</span>
                      )}
                    </td>
                    <td style={cellStyle}>
                      <button
                        onClick={() => downloadControlCSV({ ...ctrl, id: ctrlId })}
                        className="px-2 py-0.5 text-xs transition-colors"
                        style={{ color: 'var(--text-link)', border: '1px solid var(--border-default)', backgroundColor: 'transparent', borderRadius: 'var(--radius-button)' }}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                        Download
                      </button>
                    </td>
                  </tr>
                  );
                })}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
