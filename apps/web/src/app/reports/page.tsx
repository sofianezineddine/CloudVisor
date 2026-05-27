'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { Button } from '@/components/ui/button';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText, Plus, Download, Loader2, AlertTriangle, Clock,
  CheckCircle2, XCircle, RefreshCw, X,
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8080';

function getToken() {
  if (typeof window === 'undefined') return null;
  return null /* token in HttpOnly cookie */;
}

async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null as T;
  return res.json();
}

const REPORT_TYPES = [
  { value: 'findings_export', label: 'Findings Export', description: 'All findings with details' },
  { value: 'compliance_summary', label: 'Compliance Summary', description: 'Framework compliance posture' },
  { value: 'executive_summary', label: 'Executive Summary', description: 'High-level risk overview for leadership' },
  { value: 'asset_inventory', label: 'Asset Inventory', description: 'Complete cloud resource inventory' },
] as const;

const FRAMEWORKS = [
  'CIS-AWS', 'CIS-Azure', 'CIS-GCP', 'SOC2', 'PCI-DSS',
  'HIPAA', 'ISO-27001', 'NIST-800-53', 'GDPR',
] as const;

const FORMATS = [
  { value: 'pdf', label: 'PDF', description: 'Formatted for auditors' },
  { value: 'csv', label: 'CSV', description: 'Raw data export' },
  { value: 'json', label: 'JSON', description: 'Machine-readable' },
] as const;

interface Report {
  id: string;
  report_type: string;
  framework?: string;
  format: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  download_url?: string;
  created_at: string;
  completed_at?: string;
  requested_by?: string;
  file_size?: number;
}

/* ─── Status badge (pill shape per §2.7) ──────────────────────────────────── */
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; bg: string; icon: React.ReactNode }> = {
    pending:    { color: 'var(--warning)',  bg: 'var(--warning-dim)',  icon: <Clock className="h-3 w-3" /> },
    processing: { color: 'var(--accent)',   bg: 'var(--accent-dim)',   icon: <Loader2 className="h-3 w-3 animate-spin" /> },
    completed:  { color: 'var(--success)',  bg: 'var(--success-dim)',  icon: <CheckCircle2 className="h-3 w-3" /> },
    failed:     { color: 'var(--critical)', bg: 'var(--critical-dim)', icon: <XCircle className="h-3 w-3" /> },
  };
  const c = config[status] || config.pending;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium"
      style={{ color: c.color, backgroundColor: c.bg, borderRadius: '99px' }}
    >
      {c.icon}
      {status}
    </span>
  );
}

/* ─── Generate Report Form (Card per §2.8) ────────────────────────────────── */
function GenerateReportForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [reportType, setReportType] = React.useState('findings_export');
  const [framework, setFramework] = React.useState('');
  const [format, setFormat] = React.useState('pdf');
  const [dateFrom, setDateFrom] = React.useState('');
  const [dateTo, setDateTo] = React.useState('');

  const mutation = useMutation({
    mutationFn: (data: any) => apiFetch('/v1/reports', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      onClose();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      report_type: reportType,
      framework: reportType === 'compliance_summary' ? framework : undefined,
      format,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    });
  };

  /* Input style per §2.6: height 32px, bg raised, border, radius-md, text-sm */
  const inputStyle: React.CSSProperties = {
    height: '32px',
    backgroundColor: 'var(--bg-elevated)',
    border: '1px solid var(--border-default)',
    borderRadius: '4px',
    color: 'var(--text-primary)',
    fontSize: '13px',
    padding: '0 8px',
    width: '100%',
  };

  const selectStyle: React.CSSProperties = {
    ...inputStyle,
    appearance: 'auto' as any,
  };

  return (
    /* Card: bg surface, border, radius-lg, padding space-6, shadow-sm (§2.8) */
    <div
      style={{
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--border-default)',
        borderRadius: '8px',
        padding: '24px',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '24px',
      }}
    >
      <div className="flex items-center justify-between" style={{ marginBottom: '16px' }}>
        <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>
          Generate New Report
        </h3>
        <button
          onClick={onClose}
          style={{ color: 'var(--text-link)', fontSize: '13px', background: 'none', border: 'none', cursor: 'pointer' }}
        >
          Cancel
        </button>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Report Type */}
        <div>
          <label style={{ display: 'block', fontSize: '11px', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Report Type
          </label>
          <select value={reportType} onChange={e => setReportType(e.target.value)} style={selectStyle}>
            {REPORT_TYPES.map(rt => (
              <option key={rt.value} value={rt.value}>{rt.label} — {rt.description}</option>
            ))}
          </select>
        </div>

        {/* Framework (only for compliance reports) */}
        {reportType === 'compliance_summary' && (
          <div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Compliance Framework
            </label>
            <select value={framework} onChange={e => setFramework(e.target.value)} style={selectStyle}>
              <option value="">All frameworks</option>
              {FRAMEWORKS.map(fw => (
                <option key={fw} value={fw}>{fw}</option>
              ))}
            </select>
          </div>
        )}

        {/* Format */}
        <div>
          <label style={{ display: 'block', fontSize: '11px', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Output Format
          </label>
          <div style={{ display: 'flex', gap: '12px' }}>
            {FORMATS.map(f => (
              <label key={f.value} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="format"
                  value={f.value}
                  checked={format === f.value}
                  onChange={() => setFormat(f.value)}
                  style={{ width: '14px', height: '14px' }}
                />
                <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)' }}>{f.label}</span>
                <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>({f.description})</span>
              </label>
            ))}
          </div>
        </div>

        {/* Date Range */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              From Date (optional)
            </label>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              To Date (optional)
            </label>
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={inputStyle} />
          </div>
        </div>

        {mutation.isError && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', padding: '8px 12px', borderRadius: '4px', color: 'var(--critical)', backgroundColor: 'var(--critical-dim)' }}>
            <AlertTriangle className="h-3.5 w-3.5" />
            {mutation.error?.message || 'Failed to generate report'}
          </div>
        )}

        {/* Primary button per §2.4: height 32px, bg primary, white text, radius-md */}
        <button
          type="submit"
          disabled={mutation.isPending}
          style={{
            height: '32px',
            padding: '0 16px',
            borderRadius: '4px',
            border: 'none',
            backgroundColor: mutation.isPending ? 'var(--btn-primary-bg)' : 'var(--btn-primary-bg)',
            color: 'var(--btn-primary-text)',
            fontSize: '13px',
            fontWeight: 500,
            cursor: mutation.isPending ? 'not-allowed' : 'pointer',
            opacity: mutation.isPending ? 0.4 : 1,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            alignSelf: 'flex-start',
            transition: '150ms ease',
          }}
          onMouseEnter={e => { if (!mutation.isPending) (e.currentTarget.style.backgroundColor = 'var(--btn-primary-hover)'); }}
          onMouseLeave={e => { (e.currentTarget.style.backgroundColor = 'var(--btn-primary-bg)'); }}
        >
          {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
          Generate Report
        </button>
      </form>
    </div>
  );
}

/* ─── Reports Content ──────────────────────────────────────────────────────── */
function ReportsContent() {
  const [showForm, setShowForm] = React.useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reports'],
    queryFn: () => apiFetch<any>('/v1/reports?limit=50'),
    refetchInterval: 10000,
  });

  const reports: Report[] = data?.data || [];

  React.useEffect(() => {
    document.title = 'Reports - CloudVisor';
  }, []);

  return (
    <>
      {/* Page header per §2.9: flex row, title left, actions right, mb space-6 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          {/* Page title: text-xl, font-semibold, color-text-primary */}
          <h1 style={{ fontSize: '22px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Reports</h1>
          {/* Page subtitle: text-sm, color-text-secondary */}
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
            Generate compliance reports, findings exports, and executive summaries
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Secondary button per §2.4 */}
          <button
            onClick={() => refetch()}
            style={{
              height: '32px', padding: '0 16px', borderRadius: '4px',
              border: '1px solid var(--border-default)', backgroundColor: 'transparent',
              color: 'var(--text-primary)', fontSize: '13px', fontWeight: 500,
              cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px',
              transition: '150ms ease',
            }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
          {/* Primary button per §2.4 */}
          <button
            onClick={() => setShowForm(v => !v)}
            style={{
              height: '32px', padding: '0 16px', borderRadius: '4px',
              border: 'none', backgroundColor: 'var(--btn-primary-bg)',
              color: 'var(--btn-primary-text)', fontSize: '13px', fontWeight: 500,
              cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px',
              transition: '150ms ease',
            }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--btn-primary-hover)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--btn-primary-bg)')}
          >
            {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showForm ? 'Cancel' : 'Generate Report'}
          </button>
        </div>
      </div>

      {showForm && <GenerateReportForm onClose={() => setShowForm(false)} />}

      {isLoading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 0' }}>
          <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
        </div>
      ) : isError ? (
        /* Empty state per §2.5: centered icon + message */
        <div
          style={{
            backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)',
            borderRadius: '8px', padding: '48px', display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: '12px', textAlign: 'center',
          }}
        >
          <AlertTriangle className="h-8 w-8" style={{ color: 'var(--warning)' }} />
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Could not load reports</p>
        </div>
      ) : reports.length === 0 ? (
        /* Empty state per §2.5 */
        <div
          style={{
            backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)',
            borderRadius: '8px', padding: '48px', display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: '12px', textAlign: 'center',
          }}
        >
          <FileText className="h-10 w-10" style={{ color: 'var(--text-tertiary)' }} />
          <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>No reports generated yet</h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '320px' }}>
            Generate compliance reports, findings exports, or executive summaries for your organization.
          </p>
          <button
            onClick={() => setShowForm(true)}
            style={{
              height: '32px', padding: '0 16px', borderRadius: '4px', marginTop: '8px',
              border: 'none', backgroundColor: 'var(--btn-primary-bg)',
              color: 'var(--btn-primary-text)', fontSize: '13px', fontWeight: 500,
              cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px',
              transition: '150ms ease',
            }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--btn-primary-hover)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--btn-primary-bg)')}
          >
            <Plus className="h-4 w-4" />
            Generate Report
          </button>
        </div>
      ) : (
        /* Table per §2.5: bg surface, outer border + radius-lg, header bg raised */
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: '8px',
            overflow: 'hidden',
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            {/* Header: bg raised, text-xs uppercase, color-text-secondary, font-semibold */}
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-elevated)' }}>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Type</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Format</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Status</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Created</th>
                <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Actions</th>
              </tr>
            </thead>
            {/* Body: text-sm, color-text-primary, bottom border, row hover */}
            <tbody>
              {reports.map((report) => (
                <tr
                  key={report.id}
                  style={{ borderTop: '1px solid var(--border-faint)', transition: '150ms ease' }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  {/* Cell padding: space-3 space-4 (12px 16px) */}
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: 'var(--text-primary)' }}>
                    <div style={{ fontWeight: 500 }}>{report.report_type.replace(/_/g, ' ')}</div>
                    {report.framework && (
                      <div style={{ fontSize: '11px', marginTop: '2px', color: 'var(--text-tertiary)' }}>{report.framework}</div>
                    )}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    {/* Neutral badge per §2.7 */}
                    <span style={{
                      fontSize: '11px', fontWeight: 500, padding: '2px 8px', borderRadius: '99px',
                      backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)',
                      textTransform: 'uppercase',
                    }}>
                      {report.format}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <StatusBadge status={report.status} />
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '11px', color: 'var(--text-tertiary)' }}>
                    {new Date(report.created_at).toLocaleDateString('en-US', {
                      month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
                    })}
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    {report.status === 'completed' && report.download_url && (
                      <a
                        href={report.download_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: '4px',
                          fontSize: '11px', fontWeight: 500, padding: '2px 8px', borderRadius: '99px',
                          color: 'var(--accent)', backgroundColor: 'var(--accent-dim)',
                          textDecoration: 'none', transition: '150ms ease',
                        }}
                      >
                        <Download className="h-3 w-3" />
                        Download
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export default function ReportsPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <ReportsContent />
      </AppLayout>
    </ProtectedRoute>
  );
}
