'use client';

import * as React from 'react';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { Play, Loader2, FileCode, CheckCircle2, AlertTriangle } from 'lucide-react';
import { SkeletonLoader } from '@/components/cspm/skeleton-loader';
import { ErrorBanner } from '@/components/cspm/error-banner';
import {
  useSubmitIaCScan,
  useIaCResults,
  useIaCWebhooks,
  useCreateIaCWebhook,
  useIaCScanHistory,
} from '@/hooks/use-cspm';

// ─── Styles ───────────────────────────────────────────────────────────────────

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

const sectionBtnStyle = (active: boolean): React.CSSProperties => ({
  padding: '6px 12px',
  fontSize: '12px',
  fontWeight: active ? 600 : 400,
  color: active ? 'var(--accent)' : 'var(--text-secondary)',
  borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
  background: 'none',
  cursor: 'pointer',
});

// ─── Component ────────────────────────────────────────────────────────────────

export function IaCSecurityTab() {
  const [activeSection, setActiveSection] = React.useState<'submit' | 'results' | 'webhooks' | 'history'>('submit');
  const [templateContent, setTemplateContent] = React.useState('');
  const [templateType, setTemplateType] = React.useState<'terraform' | 'cloudformation' | 'kubernetes' | 'helm'>('terraform');
  const [selectedScanId, setSelectedScanId] = React.useState<string | null>(null);
  const [expandedFinding, setExpandedFinding] = React.useState<string | null>(null);
  const [historyPage, setHistoryPage] = React.useState(1);

  // Webhook form state
  const [whProvider, setWhProvider] = React.useState<'github' | 'gitlab' | 'bitbucket'>('github');
  const [whRepo, setWhRepo] = React.useState('');
  const [whMode, setWhMode] = React.useState<'advisory' | 'blocking'>('advisory');
  const [whThreshold, setWhThreshold] = React.useState('HIGH');

  const submitScan = useSubmitIaCScan();
  const { data: resultsData, isLoading: resultsLoading } = useIaCResults(selectedScanId);
  const { data: webhooksData, isLoading: webhooksLoading } = useIaCWebhooks();
  const createWebhook = useCreateIaCWebhook();
  const { data: historyData, isLoading: historyLoading } = useIaCScanHistory({ page: historyPage, page_size: 10 });

  const results = resultsData ?? [];
  const webhooks = webhooksData ?? [];
  const historyItems = historyData?.items ?? [];
  const historyTotal = historyData?.total ?? 0;
  const historyTotalPages = Math.ceil(historyTotal / 10);

  const handleSubmitScan = () => {
    if (!templateContent.trim()) return;
    submitScan.mutate(
      { template_content: templateContent, template_type: templateType },
      {
        onSuccess: (data: any) => {
          setSelectedScanId(data?.id ?? null);
          setActiveSection('results');
        },
        // onError is handled by submitScan.error below — no throw needed
      }
    );
  };

  const handleCreateWebhook = () => {
    if (!whRepo.trim()) return;
    createWebhook.mutate({
      git_provider: whProvider,
      repository: whRepo,
      enforcement_mode: whMode,
      severity_threshold: whThreshold,
    }, {
      onSuccess: () => {
        setWhRepo('');
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Section Navigation */}
      <div className="flex gap-1" style={{ borderBottom: '1px solid var(--border-default)' }}>
        {(['submit', 'results', 'webhooks', 'history'] as const).map(section => (
          <button key={section} style={sectionBtnStyle(activeSection === section)} onClick={() => setActiveSection(section)}>
            {section === 'submit' ? 'Scan Template' : section === 'results' ? 'Results' : section === 'webhooks' ? 'Webhooks' : 'History'}
          </button>
        ))}
      </div>

      {/* Submit Section */}
      {activeSection === 'submit' && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Submit IaC Template for Scanning</h3>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>Template Type:</label>
              <select
                value={templateType}
                onChange={e => setTemplateType(e.target.value as any)}
                className="rounded border px-2 py-1 text-xs"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
              >
                <option value="terraform">Terraform</option>
                <option value="cloudformation">CloudFormation</option>
                <option value="kubernetes">Kubernetes</option>
                <option value="helm">Helm</option>
              </select>
            </div>
            <textarea
              value={templateContent}
              onChange={e => setTemplateContent(e.target.value)}
              placeholder="Paste your IaC template content here..."
              className="w-full rounded border p-3 font-mono text-sm"
              style={{
                borderColor: 'var(--border-default)',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                minHeight: '200px',
                resize: 'vertical',
              }}
            />
            <div className="flex items-center gap-3">
              <Button
                onClick={handleSubmitScan}
                disabled={submitScan.isPending || !templateContent.trim()}
                className="gap-2"
              >
                {submitScan.isPending
                  ? <Loader2 className="h-4 w-4 animate-spin" />
                  : <Play className="h-4 w-4" />}
                {submitScan.isPending ? 'Scanning…' : 'Submit Scan'}
              </Button>
              {submitScan.isError && (
                <span className="text-xs" style={{ color: 'var(--critical)' }}>
                  Scan failed: {(submitScan.error as Error)?.message?.includes('server error')
                    ? 'The IaC scanner service is unavailable. Please ensure the CSPM backend is running.'
                    : ((submitScan.error as Error)?.message ?? 'Unknown error')}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Results Section */}
      {activeSection === 'results' && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Scan Results</h3>
          {!selectedScanId ? (
            <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              Submit a scan or select one from history to view results
            </div>
          ) : resultsLoading ? (
            <SkeletonLoader variant="table" rows={5} columns={6} />
          ) : results.length === 0 ? (
            <div className="flex h-16 items-center justify-center text-sm gap-2" style={{ color: 'var(--text-tertiary)' }}>
              <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
              No findings — template is clean
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={headerCellStyle}>Severity</th>
                    <th style={headerCellStyle}>File Path</th>
                    <th style={headerCellStyle}>Line</th>
                    <th style={headerCellStyle}>Resource</th>
                    <th style={headerCellStyle}>Rule ID</th>
                    <th style={headerCellStyle}>Title</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((finding: any) => (
                    <React.Fragment key={finding.id}>
                      <tr
                        style={{ cursor: 'pointer' }}
                        onClick={() => setExpandedFinding(expandedFinding === finding.id ? null : finding.id)}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                        <td style={cellStyle}><SeverityBadge severity={finding.severity} size="sm" /></td>
                        <td style={{ ...cellStyle, maxWidth: '150px' }}>
                          <div className="truncate text-xs font-mono">{finding.file_path}</div>
                        </td>
                        <td style={cellStyle}><span className="text-xs font-mono">{finding.line_number ?? '—'}</span></td>
                        <td style={{ ...cellStyle, maxWidth: '140px' }}>
                          <div className="truncate text-xs">{finding.resource_identifier}</div>
                        </td>
                        <td style={cellStyle}><span className="text-xs font-mono">{finding.rule_id}</span></td>
                        <td style={{ ...cellStyle, maxWidth: '200px' }}>
                          <div className="truncate text-xs">{finding.title}</div>
                        </td>
                      </tr>
                      {expandedFinding === finding.id && (finding.description || finding.remediation) && (
                        <tr>
                          <td colSpan={6} style={{ ...cellStyle, backgroundColor: 'var(--bg-elevated)', padding: '12px 16px' }}>
                            {finding.description && (
                              <div className="mb-2">
                                <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>Description: </span>
                                <span className="text-xs" style={{ color: 'var(--text-primary)' }}>{finding.description}</span>
                              </div>
                            )}
                            {finding.remediation && (
                              <div>
                                <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>Remediation: </span>
                                <span className="text-xs" style={{ color: 'var(--success)' }}>{finding.remediation}</span>
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Webhooks Section */}
      {activeSection === 'webhooks' && (
        <div className="space-y-4">
          <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Webhook Configuration</h3>
            {webhooksLoading ? (
              <SkeletonLoader variant="table" rows={3} columns={5} />
            ) : webhooks.length === 0 ? (
              <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
                No webhooks configured
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={headerCellStyle}>Provider</th>
                      <th style={headerCellStyle}>Repository</th>
                      <th style={headerCellStyle}>Mode</th>
                      <th style={headerCellStyle}>Threshold</th>
                      <th style={headerCellStyle}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {webhooks.map((wh: any) => (
                      <tr key={wh.id}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                        <td style={cellStyle}><span className="text-xs uppercase">{wh.git_provider}</span></td>
                        <td style={cellStyle}><span className="text-xs">{wh.repository}</span></td>
                        <td style={cellStyle}>
                          <span className="text-xs" style={{ color: wh.enforcement_mode === 'blocking' ? 'var(--critical)' : 'var(--text-secondary)' }}>
                            {wh.enforcement_mode}
                          </span>
                        </td>
                        <td style={cellStyle}><span className="text-xs">{wh.severity_threshold}</span></td>
                        <td style={cellStyle}>
                          {wh.is_active ? (
                            <span className="text-xs" style={{ color: 'var(--success)' }}>● Active</span>
                          ) : (
                            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>○ Inactive</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Create Webhook Form */}
          <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Create Webhook</h3>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Provider</label>
                <select value={whProvider} onChange={e => setWhProvider(e.target.value as any)}
                  className="w-full rounded border px-2 py-1 text-xs"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                  <option value="github">GitHub</option>
                  <option value="gitlab">GitLab</option>
                  <option value="bitbucket">Bitbucket</option>
                </select>
              </div>
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Repository</label>
                <input value={whRepo} onChange={e => setWhRepo(e.target.value)}
                  placeholder="org/repo"
                  className="w-full rounded border px-2 py-1 text-xs"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
              </div>
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Mode</label>
                <select value={whMode} onChange={e => setWhMode(e.target.value as any)}
                  className="w-full rounded border px-2 py-1 text-xs"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                  <option value="advisory">Advisory</option>
                  <option value="blocking">Blocking</option>
                </select>
              </div>
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Threshold</label>
                <select value={whThreshold} onChange={e => setWhThreshold(e.target.value)}
                  className="w-full rounded border px-2 py-1 text-xs"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                  <option value="CRITICAL">Critical</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>
              </div>
            </div>
            <div className="mt-3">
              <Button onClick={handleCreateWebhook} disabled={createWebhook.isPending || !whRepo.trim()} size="sm" className="gap-2">
                {createWebhook.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                Create Webhook
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* History Section */}
      {activeSection === 'history' && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Scan History</h3>
          {historyLoading ? (
            <SkeletonLoader variant="table" rows={5} columns={6} />
          ) : historyItems.length === 0 ? (
            <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No scan history available
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={headerCellStyle}>Status</th>
                      <th style={headerCellStyle}>Source</th>
                      <th style={headerCellStyle}>Repository</th>
                      <th style={headerCellStyle}>Type</th>
                      <th style={headerCellStyle}>Findings</th>
                      <th style={headerCellStyle}>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historyItems.map((scan: any) => (
                      <tr key={scan.id}
                        style={{ cursor: 'pointer' }}
                        onClick={() => { setSelectedScanId(scan.id); setActiveSection('results'); }}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                        <td style={cellStyle}>
                          {scan.passed === true ? (
                            <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--success)' }} />
                          ) : scan.passed === false ? (
                            <AlertTriangle className="h-4 w-4" style={{ color: 'var(--critical)' }} />
                          ) : (
                            <Loader2 className="h-4 w-4 animate-spin" style={{ color: 'var(--text-tertiary)' }} />
                          )}
                        </td>
                        <td style={cellStyle}><span className="text-xs">{scan.source_type}</span></td>
                        <td style={{ ...cellStyle, maxWidth: '160px' }}>
                          <div className="truncate text-xs">{scan.repository ?? '—'}</div>
                        </td>
                        <td style={cellStyle}><span className="text-xs">{scan.template_type}</span></td>
                        <td style={cellStyle}>
                          <span className="text-xs font-mono">
                            {scan.total_findings ?? 0}
                            {scan.critical_count > 0 && (
                              <span style={{ color: 'var(--critical)' }}> ({scan.critical_count} crit)</span>
                            )}
                          </span>
                        </td>
                        <td style={cellStyle}>
                          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                            {scan.started_at ? new Date(scan.started_at).toLocaleDateString() : '—'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {historyTotalPages > 1 && (
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    Page {historyPage} of {historyTotalPages}
                  </span>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setHistoryPage(p => Math.max(1, p - 1))} disabled={historyPage <= 1}>
                      Previous
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setHistoryPage(p => Math.min(historyTotalPages, p + 1))} disabled={historyPage >= historyTotalPages}>
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
