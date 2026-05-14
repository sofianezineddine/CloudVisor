'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import {
  Shield, X, Loader2, AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useCSPMReports, useCSPMReport, useCreateReport,
} from '@/hooks/use-cspm';
import { cspmAPI } from '@/lib/api/cspm';

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005';

/** Download a report file with the auth token attached. */
async function downloadReportWithAuth(reportId: string, filename: string) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  const url = `${API_BASE}/v1/cspm/reports/${reportId}/download`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    throw new Error(`Download failed: ${res.status} ${res.statusText}`);
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(objectUrl);
}

const COMPLIANCE_FRAMEWORKS = ['CIS-AWS', 'SOC2', 'PCI-DSS', 'HIPAA', 'NIST-800-53', 'ISO27001', 'GDPR'];

function timeAgo(isoDate: string | null | undefined): string {
  if (!isoDate) return '—';
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
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

export function ReportsTab() {
  const { data: reports, isLoading, error } = useCSPMReports();
  const createReport = useCreateReport();
  const [showModal, setShowModal] = React.useState(false);
  const [reportType, setReportType] = React.useState('findings_export');
  const [framework, setFramework] = React.useState('CIS-AWS');
  const [format, setFormat] = React.useState('csv');
  const [pollingId, setPollingId] = React.useState<string | null>(null);
  const { data: polledReport } = useCSPMReport(pollingId);
  const [downloadingId, setDownloadingId] = React.useState<string | null>(null);
  const [downloadError, setDownloadError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (polledReport && (polledReport as any).status === 'ready') setPollingId(null);
  }, [polledReport]);

  const items = Array.isArray(reports) ? reports : [];

  async function handleCreate() {
    const payload: Parameters<typeof cspmAPI.createReport>[0] = {
      report_type: reportType,
      format,
      ...(reportType === 'compliance' ? { framework } : {}),
    };
    const result = await createReport.mutateAsync(payload);
    setShowModal(false);
    setPollingId((result as any).id);
  }

  function statusStyle(status: string): React.CSSProperties {
    if (status === 'ready') return { color: 'var(--success)', backgroundColor: 'var(--success-bg)', border: '1px solid var(--low-border)' };
    if (status === 'generating') return { color: 'var(--warning)', backgroundColor: 'var(--medium-bg)', border: '1px solid var(--medium-border)' };
    if (status === 'failed') return { color: 'var(--critical)', backgroundColor: 'var(--critical-bg)', border: '1px solid var(--critical-border)' };
    return { color: 'var(--text-secondary)', backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' };
  }

  return (
    <div>
      {error && <ErrorBanner message="Failed to load reports" />}
      {downloadError && <ErrorBanner message={downloadError} />}
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{items.length} reports</span>
        <Button onClick={() => setShowModal(true)} className="gap-2 h-8 px-3 text-sm">
          <Shield className="h-3.5 w-3.5" />
          Generate Report
        </Button>
      </div>
      {isLoading ? (
        <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-10" />)}</div>
      ) : items.length === 0 ? (
        <div className="flex h-40 flex-col items-center justify-center gap-3 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <Shield className="h-8 w-8" style={{ color: 'var(--text-tertiary)' }} />
          <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>No reports yet</div>
          <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Generate your first compliance or posture report</div>
          <Button onClick={() => setShowModal(true)} className="h-8 px-3 text-sm">Generate Report</Button>
        </div>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              {['Type', 'Framework', 'Format', 'Status', 'Created', 'Size', 'Download'].map(h => (
                <th key={h} style={headerCellStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(report => (
              <tr key={report.id}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                <td style={cellStyle}><span className="text-sm capitalize" style={{ color: 'var(--text-primary)' }}>{report.report_type.replace('_', ' ')}</span></td>
                <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{report.framework || ''}</span></td>
                <td style={cellStyle}><span className="text-xs uppercase" style={{ color: 'var(--text-secondary)' }}>{report.format}</span></td>
                <td style={cellStyle}>
                  <span className="rounded px-2 py-0.5 text-xs font-semibold capitalize" style={statusStyle(report.status)}>
                    {report.status}
                  </span>
                </td>
                <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{timeAgo(report.created_at)}</span></td>
                <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{report.file_size_bytes ? `${Math.round(report.file_size_bytes / 1024)}KB` : ''}</span></td>
                <td style={cellStyle}>
                  {report.status === 'ready' ? (
                    <button
                      onClick={async () => {
                        setDownloadError(null);
                        setDownloadingId(report.id);
                        try {
                          const filename = `cloudvisor-${report.report_type}-${report.id.slice(0, 8)}.${report.format}`;
                          await downloadReportWithAuth(report.id, filename);
                        } catch (e: unknown) {
                          setDownloadError(e instanceof Error ? e.message : 'Download failed');
                        } finally {
                          setDownloadingId(null);
                        }
                      }}
                      disabled={downloadingId === report.id}
                      className="rounded px-2 py-0.5 text-xs flex items-center gap-1"
                      style={{ color: 'var(--text-link)', border: '1px solid var(--border-default)', backgroundColor: 'transparent', cursor: 'pointer' }}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      {downloadingId === report.id ? (
                        <><Loader2 className="h-3 w-3 animate-spin" /> Downloading…</>
                      ) : 'Download'}
                    </button>
                  ) : <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}></span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="w-full max-w-md rounded-lg" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)' }}>
            <div className="flex items-center justify-between border-b px-6 py-4" style={{ borderColor: 'var(--border-default)' }}>
              <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Generate Report</h2>
              <button onClick={() => setShowModal(false)} style={{ color: 'var(--text-tertiary)' }}><X className="h-4 w-4" /></button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Report Type</label>
                <select value={reportType} onChange={e => setReportType(e.target.value)}
                  className="w-full rounded border px-3 py-2 text-sm"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                  <option value="findings_export">Findings Export</option>
                  <option value="posture">Posture Report</option>
                  <option value="compliance">Compliance Report</option>
                </select>
              </div>
              {reportType === 'compliance' && (
                <div>
                  <label className="block text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Framework</label>
                  <select value={framework} onChange={e => setFramework(e.target.value)}
                    className="w-full rounded border px-3 py-2 text-sm"
                    style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                    {COMPLIANCE_FRAMEWORKS.map(fw => <option key={fw} value={fw}>{fw}</option>)}
                  </select>
                </div>
              )}
              <div>
                <label className="block text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Format</label>
                <select value={format} onChange={e => setFormat(e.target.value)}
                  className="w-full rounded border px-3 py-2 text-sm"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                  <option value="csv">CSV</option>
                </select>
                <p className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>PDF export coming soon</p>
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t px-6 py-4" style={{ borderColor: 'var(--border-default)' }}>
              <Button onClick={() => setShowModal(false)} className="h-8 px-3 text-sm">Cancel</Button>
              <Button onClick={handleCreate} disabled={createReport.isPending} className="h-8 px-3 text-sm gap-2">
                {createReport.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                Generate
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
