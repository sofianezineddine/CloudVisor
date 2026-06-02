'use client';

import * as React from 'react';
import dynamic from 'next/dynamic';
import ProviderBadge from '@/components/ui/provider-badge';
import {
  Search, RefreshCw, Loader2, Globe, ChevronLeft, ChevronRight,
  ChevronDown, X, ArrowUp, ArrowDown, ArrowUpDown, Download, Share2, Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { connectorAPI, DiscoveredResource } from '@/lib/api/connector';
import { graphAPI, GraphAsset } from '@/lib/api/graph';
import apiClient from '@/lib/api/apiClient';
import { useScopeStore } from '@/stores/scope';

const AssetGraph = dynamic(
  () => import('@/components/ui/asset-graph').then(m => ({ default: m.AssetGraph })),
  { ssr: false, loading: () => <div className="flex h-full items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-blue-500" /></div> }
);

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CATEGORIES: { id: string; label: string; patterns: string[] }[] = [
  { id: 'iam',        label: 'IAM & Identity', patterns: ['iam', 'identity', 'user', 'role', 'policy', 'group', 'permission'] },
  { id: 'compute',    label: 'Compute',         patterns: ['ec2', 'instance', 'vm', 'virtualmachine', 'compute', 'server'] },
  { id: 'storage',    label: 'Storage',         patterns: ['s3', 'bucket', 'storage', 'blob', 'disk', 'volume', 'efs', 'object'] },
  { id: 'network',    label: 'Network',         patterns: ['vpc', 'subnet', 'securitygroup', 'nsg', 'firewall', 'loadbalancer', 'elb', 'gateway', 'route', 'dns', 'cloudfront', 'eip', 'network', 'vnet'] },
  { id: 'database',   label: 'Database',        patterns: ['rds', 'database', 'db', 'sql', 'dynamo', 'cosmos', 'redis', 'elasticache', 'aurora', 'postgres', 'mysql', 'bigquery'] },
  { id: 'serverless', label: 'Serverless',      patterns: ['lambda', 'function', 'serverless', 'cloudrun', 'fargate', 'ecs'] },
  { id: 'kubernetes', label: 'Kubernetes',      patterns: ['eks', 'aks', 'gke', 'oke', 'kubernetes', 'k8s', 'cluster'] },
  { id: 'security',   label: 'Security',        patterns: ['kms', 'key', 'secret', 'vault', 'certificate', 'cloudtrail', 'config'] },
  { id: 'messaging',  label: 'Messaging',       patterns: ['sns', 'sqs', 'queue', 'topic', 'pubsub', 'eventhub', 'kinesis'] },
];

function getCat(rt: string): string {
  const l = rt.toLowerCase().replace(/::/g, '');
  for (const c of CATEGORIES) if (c.patterns.some(p => l.includes(p))) return c.id;
  return 'other';
}

function fmtType(rt: string): string {
  const p = rt.split('::'); const last = p[p.length - 1] || rt;
  return last.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function fmtProvider(p: string): string {
  return { aws: 'AWS', azure: 'Azure', gcp: 'GCP', oci: 'OCI' }[p] ?? p.toUpperCase();
}

function deriveRisk(r: DiscoveredResource & { risk_score?: number; open_findings_count?: number }): number {
  // Use real risk_score from graph service if available
  if (r.risk_score != null && r.risk_score > 0) return r.risk_score;
  // Fallback: derive from basic properties
  let s = 10; if (r.is_public) s += 40; if (r.environment === 'prod') s = Math.round(s * 1.5);
  return Math.min(s, 100);
}

function buildPages(cur: number, tot: number): (number | '…')[] {
  if (tot <= 7) return Array.from({ length: tot }, (_, i) => i + 1);
  if (cur <= 4) return [1, 2, 3, 4, 5, '…', tot];
  if (cur >= tot - 3) return [1, '…', tot - 4, tot - 3, tot - 2, tot - 1, tot];
  return [1, '…', cur - 1, cur, cur + 1, '…', tot];
}

// ─── Components ─────────────────────────────────────────────────────────────

function TypeDropdown({ value, onChange, types }: { value: string; onChange: (v: string) => void; types: string[] }) {
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState('');
  const ref = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h);
  }, []);
  const filtered = types.filter(t => !q || t.toLowerCase().includes(q.toLowerCase()));
  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(o => !o)}
        className="inline-flex items-center gap-2 border rounded px-3 py-1.5 text-sm transition-colors min-w-[160px]"
        style={{ borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
        onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-strong)'}
        onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-default)'}>
        <span className="flex-1 text-left">{value ? fmtType(value) : 'All types'}</span>
        {value && <span onClick={ev => { ev.stopPropagation(); onChange(''); }} style={{ color: "var(--text-tertiary)", cursor: "pointer" }}><X className="h-3 w-3" /></span>}
        <ChevronDown className={cn('h-4 w-4 transition-transform', open && 'rotate-180')} style={{ color: 'var(--accent)' }} />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-64 rounded border shadow-xl" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <div className='p-2' style={{ borderBottom: '1px solid var(--border-faint)' }}>
            <div className="relative">
              <Search className='absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5' style={{ color: 'var(--text-tertiary)' }} />
              <input autoFocus type="text" value={q} onChange={e => setQ(e.target.value)} placeholder="Search types…"
                className='w-full border rounded pl-7 pr-2 py-1 text-xs focus:outline-none'
                style={{ borderColor: 'var(--border-default)' }} />
            </div>
          </div>
          <div className="max-h-60 overflow-y-auto">
            <button onClick={() => { onChange(''); setOpen(false); setQ(''); }}
              className="w-full px-3 py-2 text-left text-sm transition-colors"
              style={{ color: !value ? 'var(--accent)' : 'var(--text-primary)', fontWeight: !value ? 600 : 400 }}>All types</button>
            {filtered.map(t => (
              <button key={t} onClick={() => { onChange(t); setOpen(false); setQ(''); }}
                className="w-full px-3 py-2 text-left text-sm transition-colors"
                style={{ color: value === t ? 'var(--accent)' : 'var(--text-primary)', fontWeight: value === t ? 600 : 400 }}>
                {fmtType(t)}
              </button>
            ))}
            {filtered.length === 0 && <p className='px-3 py-4 text-center text-xs' style={{ color: 'var(--text-tertiary)' }}>No types found</p>}
          </div>
        </div>
      )}
    </div>
  );
}

function AwsIcon({ type, size = 20 }: { type: string; size?: number }) {
  const s = size;
  const icons: Record<string, React.ReactNode> = {
    iamrole: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><path d="M20 8c-3.3 0-6 2.7-6 6 0 2.2 1.2 4.1 3 5.2V22l-5 3v3h16v-3l-5-3v-2.8c1.8-1.1 3-3 3-5.2 0-3.3-2.7-6-6-6z" fill="#DD344C"/></svg>,
    iamuser: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><circle cx="20" cy="15" r="6" fill="#DD344C"/><path d="M8 32c0-6.6 5.4-12 12-12s12 5.4 12 12" stroke="#DD344C" strokeWidth="2.5" strokeLinecap="round"/></svg>,
    iampolicy: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><rect x="10" y="8" width="20" height="24" rx="2" stroke="#DD344C" strokeWidth="2"/><path d="M14 16h12M14 20h12M14 24h8" stroke="#DD344C" strokeWidth="2" strokeLinecap="round"/></svg>,
    ec2: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#ED7100" fillOpacity=".12"/><rect x="8" y="8" width="24" height="24" rx="3" stroke="#ED7100" strokeWidth="2"/><rect x="13" y="13" width="14" height="14" rx="1" fill="#ED7100" fillOpacity=".3"/><path d="M4 16h4M4 24h4M32 16h4M32 24h4M16 4v4M24 4v4M16 32v4M24 32v4" stroke="#ED7100" strokeWidth="2" strokeLinecap="round"/></svg>,
    instance: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#ED7100" fillOpacity=".12"/><rect x="8" y="8" width="24" height="24" rx="3" stroke="#ED7100" strokeWidth="2"/><rect x="13" y="13" width="14" height="14" rx="1" fill="#ED7100" fillOpacity=".3"/></svg>,
    lambdafunction: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#ED7100" fillOpacity=".12"/><path d="M10 30L18 10l4 10 4-6 4 16" stroke="#ED7100" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
    cloudfunction: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#ED7100" fillOpacity=".12"/><path d="M10 30L18 10l4 10 4-6 4 16" stroke="#ED7100" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
    ekscluster: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#ED7100" fillOpacity=".12"/><path d="M20 8l10 5.8v11.4L20 31 10 25.2V13.8L20 8z" stroke="#ED7100" strokeWidth="2"/><circle cx="20" cy="20" r="4" fill="#ED7100"/></svg>,
    vpc: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#8C4FFF" fillOpacity=".12"/><rect x="6" y="6" width="28" height="28" rx="14" stroke="#8C4FFF" strokeWidth="2"/><rect x="12" y="12" width="16" height="16" rx="8" stroke="#8C4FFF" strokeWidth="2"/><circle cx="20" cy="20" r="3" fill="#8C4FFF"/></svg>,
    subnet: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#8C4FFF" fillOpacity=".12"/><rect x="8" y="8" width="24" height="24" rx="4" stroke="#8C4FFF" strokeWidth="2"/><rect x="14" y="14" width="12" height="12" rx="2" stroke="#8C4FFF" strokeWidth="1.5"/></svg>,
    securitygroup: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><path d="M20 8l10 4v8c0 6-4.5 10.5-10 12-5.5-1.5-10-6-10-12v-8l10-4z" stroke="#DD344C" strokeWidth="2"/><path d="M15 20l3 3 7-7" stroke="#DD344C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>,
    networksecuritygroup: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><path d="M20 8l10 4v8c0 6-4.5 10.5-10 12-5.5-1.5-10-6-10-12v-8l10-4z" stroke="#DD344C" strokeWidth="2"/></svg>,
    s3bucket: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#3F8624" fillOpacity=".12"/><ellipse cx="20" cy="13" rx="12" ry="5" stroke="#3F8624" strokeWidth="2"/><path d="M8 13v14c0 2.8 5.4 5 12 5s12-2.2 12-5V13" stroke="#3F8624" strokeWidth="2"/><path d="M8 20c0 2.8 5.4 5 12 5s12-2.2 12-5" stroke="#3F8624" strokeWidth="1.5"/></svg>,
    bucket: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#3F8624" fillOpacity=".12"/><ellipse cx="20" cy="13" rx="12" ry="5" stroke="#3F8624" strokeWidth="2"/><path d="M8 13v14c0 2.8 5.4 5 12 5s12-2.2 12-5V13" stroke="#3F8624" strokeWidth="2"/></svg>,
    storageaccount: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#3F8624" fillOpacity=".12"/><rect x="8" y="14" width="24" height="18" rx="2" stroke="#3F8624" strokeWidth="2"/><path d="M14 14V10a6 6 0 0112 0v4" stroke="#3F8624" strokeWidth="2"/></svg>,
    rdsinstance: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#3F8624" fillOpacity=".12"/><ellipse cx="20" cy="12" rx="12" ry="4" stroke="#3F8624" strokeWidth="2"/><path d="M8 12v16c0 2.2 5.4 4 12 4s12-1.8 12-4V12" stroke="#3F8624" strokeWidth="2"/><path d="M8 20c0 2.2 5.4 4 12 4s12-1.8 12-4" stroke="#3F8624" strokeWidth="1.5"/></svg>,
    dynamodbtable: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#3F8624" fillOpacity=".12"/><path d="M20 8c-6 0-10 2-10 4v16c0 2 4 4 10 4s10-2 10-4V12c0-2-4-4-10-4z" stroke="#3F8624" strokeWidth="2"/><path d="M10 16c0 2 4 4 10 4s10-2 10-4M10 24c0 2 4 4 10 4s10-2 10-4" stroke="#3F8624" strokeWidth="1.5"/></svg>,
    kmskey: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><circle cx="16" cy="18" r="7" stroke="#DD344C" strokeWidth="2"/><path d="M21 22l10 10M27 28l3-3" stroke="#DD344C" strokeWidth="2" strokeLinecap="round"/></svg>,
    keyvault: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><circle cx="16" cy="18" r="7" stroke="#DD344C" strokeWidth="2"/><path d="M21 22l10 10" stroke="#DD344C" strokeWidth="2" strokeLinecap="round"/></svg>,
    snstopic: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#E7157B" fillOpacity=".12"/><path d="M8 14h24v12a2 2 0 01-2 2H10a2 2 0 01-2-2V14z" stroke="#E7157B" strokeWidth="2"/><path d="M8 14l12 9 12-9" stroke="#E7157B" strokeWidth="2" strokeLinecap="round"/></svg>,
    sqsqueue: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#E7157B" fillOpacity=".12"/><rect x="6" y="14" width="28" height="12" rx="6" stroke="#E7157B" strokeWidth="2"/><circle cx="14" cy="20" r="2" fill="#E7157B"/><circle cx="20" cy="20" r="2" fill="#E7157B"/><circle cx="26" cy="20" r="2" fill="#E7157B"/></svg>,
    cloudtrailtrail: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#527FFF" fillOpacity=".12"/><path d="M8 28l7-10 5 6 5-8 7 12" stroke="#527FFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
    default: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#6b7194" fillOpacity=".12"/><rect x="10" y="10" width="20" height="20" rx="4" stroke="#6b7194" strokeWidth="2"/></svg>,
  };
  return <>{icons[type] || icons.default}</>;
}

function getAssetTypeKey(resourceType: string): string {
  return resourceType.split('::').pop()?.toLowerCase().replace(/_/g, '') || 'default';
}

function RegionDropdown({ value, onChange, regions }: { value: string; onChange: (v: string) => void; regions: string[] }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h);
  }, []);
  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(o => !o)}
        className="inline-flex items-center gap-2 border rounded px-3 py-1.5 text-sm transition-colors min-w-[140px]"
        style={{ borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
        onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-strong)'}
        onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-default)'}>
        <span className="flex-1 text-left">{value || 'All regions'}</span>
        {value && <span onClick={ev => { ev.stopPropagation(); onChange(''); }} style={{ color: 'var(--text-tertiary)', cursor: 'pointer' }}><X className="h-3 w-3" /></span>}
        <ChevronDown className={cn('h-4 w-4 transition-transform', open && 'rotate-180')} style={{ color: 'var(--accent)' }} />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-52 rounded border shadow-xl" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <div className="max-h-60 overflow-y-auto py-1">
            <button onClick={() => { onChange(''); setOpen(false); }}
              className="w-full px-3 py-2 text-left text-sm"
              style={{ color: !value ? 'var(--accent)' : 'var(--text-primary)', fontWeight: !value ? 600 : 400 }}>
              All regions
            </button>
            {regions.map(r => (
              <button key={r} onClick={() => { onChange(r); setOpen(false); }}
                className="w-full px-3 py-2 text-left text-sm font-mono"
                style={{ color: value === r ? 'var(--accent)' : 'var(--text-primary)', fontWeight: value === r ? 600 : 400, fontSize: 12 }}>
                {r}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EnvDropdown({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h);
  }, []);
  const envs = ['prod', 'staging', 'dev', 'unknown'];
  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(o => !o)}
        className="inline-flex items-center gap-2 border rounded px-3 py-1.5 text-sm transition-colors min-w-[130px]"
        style={{ borderColor: 'var(--border-default)', color: 'var(--text-primary)', backgroundColor: 'var(--bg-surface)' }}
        onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-strong)'}
        onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-default)'}>
        <span className="flex-1 text-left">{value || 'All envs'}</span>
        {value && <span onClick={ev => { ev.stopPropagation(); onChange(''); }} style={{ color: 'var(--text-tertiary)', cursor: 'pointer' }}><X className="h-3 w-3" /></span>}
        <ChevronDown className={cn('h-4 w-4 transition-transform', open && 'rotate-180')} style={{ color: 'var(--accent)' }} />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-40 rounded border shadow-xl"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
          <div className="py-1">
            <button onClick={() => { onChange(''); setOpen(false); }}
              className="w-full px-3 py-2 text-left text-sm"
              style={{ color: !value ? 'var(--accent)' : 'var(--text-primary)', fontWeight: !value ? 600 : 400 }}>
              All envs
            </button>
            {envs.map(e => (
              <button key={e} onClick={() => { onChange(e); setOpen(false); }}
                className="w-full px-3 py-2 text-left text-sm capitalize"
                style={{ color: value === e ? 'var(--accent)' : 'var(--text-primary)', fontWeight: value === e ? 600 : 400 }}>
                {e}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SortTh({ label, field, sortField, sortDir, onSort, className = '' }: {
  label: string; field: string; sortField: string; sortDir: 'asc' | 'desc';
  onSort: (f: string) => void; className?: string;
}) {
  const active = sortField === field;
  return (
    <th className={`px-3 py-2.5 text-left text-xs font-semibold select-none ${className}`}
      style={{ color: 'var(--text-primary)', backgroundColor: 'var(--bg-elevated)', borderBottom: '2px solid var(--border-default)', whiteSpace: 'nowrap' }}>
      <button onClick={() => onSort(field)} className="inline-flex items-center gap-1 group"
        style={{ color: active ? 'var(--accent)' : 'var(--text-primary)' }}>
        {label}
        <span className="opacity-60 group-hover:opacity-100">
          {active ? (sortDir === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
        </span>
      </button>
    </th>
  );
}

const ALL_COLUMNS = [
  { id: 'name',        label: 'Resource name', required: true  },
  { id: 'type',        label: 'Type',          required: false },
  { id: 'provider',    label: 'Provider',      required: false },
  { id: 'region',      label: 'Region',        required: false },
  { id: 'environment', label: 'Environment',   required: false },
  { id: 'risk_score',  label: 'Risk Score',    required: false },
  { id: 'findings',    label: 'Findings',      required: false },
  { id: 'exposure',    label: 'Exposure',      required: false },
  { id: 'tags',        label: 'Tags',          required: false },
] as const;

type ColumnId = typeof ALL_COLUMNS[number]['id'];

function PreferencesModal({
  perPage,
  visibleCols,
  onConfirm,
  onCancel,
}: {
  perPage: number;
  visibleCols: Set<ColumnId>;
  onConfirm: (perPage: number, cols: Set<ColumnId>) => void;
  onCancel: () => void;
}) {
  const [draftPerPage, setDraftPerPage] = React.useState(perPage);
  const [draftCols, setDraftCols] = React.useState(new Set(visibleCols));

  const toggleCol = (id: ColumnId) => {
    const next = new Set(draftCols);
    if (next.has(id)) next.delete(id); else next.add(id);
    setDraftCols(next);
  };

  const backdropRef = React.useRef<HTMLDivElement>(null);

  const overlay: React.CSSProperties = {
    position: 'fixed', inset: 0, zIndex: 1000,
    backgroundColor: 'rgba(0,0,0,0.5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: 16,
  };
  const modal: React.CSSProperties = {
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 8,
    boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
    width: '100%',
    maxWidth: 600,
    maxHeight: '90vh',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  };

  return (
    <div style={overlay} ref={backdropRef} onClick={e => { if (e.target === backdropRef.current) onCancel(); }}>
      <div style={modal}>
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid var(--border-default)' }}>
          <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Preferences</h2>
          <button onClick={onCancel} className="flex items-center justify-center w-7 h-7 rounded transition-colors" style={{ color: 'var(--text-tertiary)' }}>
            <span style={{ fontSize: 18, lineHeight: 1 }}>×</span>
          </button>
        </div>
        <div className="flex flex-1 overflow-hidden">
          <div className="px-6 py-5 flex-shrink-0" style={{ width: 220, borderRight: '1px solid var(--border-default)' }}>
            <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-secondary)' }}>Page size</p>
            <div className="space-y-2.5">
              {[10, 20, 25, 50, 100].map(n => (
                <label key={n} className="flex items-center gap-2.5 cursor-pointer">
                  <input type="radio" name="pageSize" checked={draftPerPage === n} onChange={() => setDraftPerPage(n)} style={{ accentColor: 'var(--accent)', width: 16, height: 16 }} />
                  <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{n} rows</span>
                </label>
              ))}
            </div>
          </div>
          <div className="px-6 py-5 flex-1 overflow-y-auto">
            <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-secondary)' }}>Select visible columns</p>
            <div className="space-y-0">
              {ALL_COLUMNS.map(col => {
                const on = draftCols.has(col.id);
                return (
                  <div key={col.id} className="flex items-center justify-between py-2.5" style={{ borderBottom: '1px solid var(--border-faint)' }}>
                    <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{col.label}</span>
                    <button onClick={() => !col.required && toggleCol(col.id)} disabled={col.required}
                      style={{
                        width: 36, height: 20, borderRadius: 10, border: 'none',
                        backgroundColor: on ? 'var(--accent)' : 'var(--border-default)',
                        position: 'relative', transition: 'background-color 0.2s', opacity: col.required ? 0.6 : 1,
                      }}>
                      <span style={{ position: 'absolute', top: 2, left: on ? 18 : 2, width: 16, height: 16, borderRadius: '50%', backgroundColor: '#ffffff', transition: 'left 0.2s' }} />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4" style={{ borderTop: '1px solid var(--border-default)' }}>
          <button onClick={onCancel} className="border rounded px-4 py-1.5 text-sm transition-colors" style={{ borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}>Cancel</button>
          <button onClick={() => onConfirm(draftPerPage, draftCols)} className="border rounded px-4 py-1.5 text-sm font-semibold transition-colors" style={{ backgroundColor: 'var(--btn-primary-bg)', color: 'var(--btn-primary-text)' }}>Confirm</button>
        </div>
      </div>
    </div>
  );
}

export function AssetsTab() {
  const [viewMode, setViewMode] = React.useState<'table' | 'graph'>('table');
  const [search, setSearch] = React.useState('');
  const [debSearch, setDebSearch] = React.useState('');
  const [typeFilter, setTypeFilter] = React.useState('');
  const [catFilter, setCatFilter] = React.useState('');
  const [regionFilter, setRegionFilter] = React.useState('');
  const [envFilter, setEnvFilter] = React.useState('');
  const [sortField, setSortField] = React.useState('name');
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('asc');
  const [page, setPage] = React.useState(1);
  const [perPage, setPerPage] = React.useState(25);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [showPrefs, setShowPrefs] = React.useState(false);
  const [visibleCols, setVisibleCols] = React.useState<Set<ColumnId>>(
    new Set(['name', 'type', 'provider', 'region', 'environment', 'risk_score', 'findings', 'exposure'] as ColumnId[])
  );

  const [resources, setResources] = React.useState<DiscoveredResource[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const globalAccountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const globalProvider  = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
  const scopeMode       = useScopeStore(s => s.mode);
  const scopeAccounts   = useScopeStore(s => s.accounts);

  const accountNameMap = React.useMemo(() => {
    const m: Record<string, string> = {};
    for (const a of scopeAccounts) { m[a.account_id] = a.name || a.account_id; }
    return m;
  }, [scopeAccounts]);

  const showAccountCol = scopeMode === 'provider';

  React.useEffect(() => { const t = setTimeout(() => setDebSearch(search), 300); return () => clearTimeout(t); }, [search]);
  React.useEffect(() => { setPage(1); }, [debSearch, typeFilter, catFilter, regionFilter, envFilter, globalAccountId, globalProvider]);

  const fetchResources = React.useCallback(async () => {
    // Get fresh account IDs from store to avoid stale closure issues
    const currentAccountIds = useScopeStore.getState().accountIds;
    
    // Don't fetch if no accounts are connected
    if (currentAccountIds.length === 0) {
      setLoading(false);
      setResources([]);
      return;
    }

    setLoading(true); setError(null);
    try {
      let items: any[] = [];
      
      if (debSearch && debSearch.length >= 2) {
        // Search: try graph service ES-backed search first (has risk scores)
        try {
          const searchResp = await graphAPI.searchAssets({
            q: debSearch,
            provider: globalProvider || undefined,
            limit: 200,
          });
          items = searchResp?.hits ?? [];
        } catch (err) {
          console.warn('Graph search failed, falling back to connector:', err);
          // Fallback to connector search
          try {
            const resp = await connectorAPI.listResources({ 
              account_id: globalAccountId, 
              account_ids: !globalAccountId ? currentAccountIds : undefined,
              provider: !globalAccountId && currentAccountIds.length === 0 ? globalProvider : undefined, 
              search: debSearch, 
              limit: 200, 
              offset: 0 
            });
            items = (resp?.resources as any[]) ?? [];
          } catch (err2) {
            console.warn('Connector search failed, falling back to API client:', err2);
            const searchResp = await apiClient.assets.search(debSearch, { 
              provider: globalProvider || undefined, 
              limit: 200,
            });
            items = (searchResp?.data as any[]) ?? [];
          }
        }
        // Client-side filter by account if in account mode
        if (globalAccountId) {
          items = items.filter((a: any) => a.account_id === globalAccountId);
        } else if (currentAccountIds.length > 0) {
          // Filter to only show resources from accounts in current scope
          items = items.filter((a: any) => currentAccountIds.includes(a.account_id));
        }
      } else {
        // Regular listing: try graph service first (has risk_score + open_findings_count)
        try {
          const graphResp = await graphAPI.listAssets({
            provider: globalProvider || undefined,
            resource_type: typeFilter || undefined,
            limit: 100,
          });
          items = graphResp?.assets ?? [];
          // If graph returned data with risk scores, use it
          if (items.length > 0) {
            console.log(`Fetched ${items.length} assets from graph service`);
          }
        } catch (err) {
          console.warn('Graph listAssets failed, falling back to connector:', err);
          // Fallback: fetch from connector (no risk scores, but complete inventory)
          try {
            let allItems: any[] = [];
            let offset = 0;
            const batchSize = 200;
            let hasMore = true;
            
            while (hasMore && allItems.length < 10000) {
              const resp = await connectorAPI.listResources({ 
                account_id: globalAccountId, 
                account_ids: !globalAccountId ? currentAccountIds : undefined,
                provider: !globalAccountId && currentAccountIds.length === 0 ? globalProvider : undefined, 
                resource_type: typeFilter || undefined, 
                limit: batchSize, 
                offset: offset 
              });
              const batch = (resp?.resources as any[]) ?? [];
              allItems = [...allItems, ...batch];
              hasMore = batch.length === batchSize;
              offset += batchSize;
            }
            items = allItems;
            console.log(`Fetched ${items.length} assets from connector service`);
          } catch (err2) {
            console.warn('Connector listResources failed, falling back to API client:', err2);
            const resp = await apiClient.assets.list({ 
              account_id: globalAccountId, 
              provider: !globalAccountId ? globalProvider : undefined, 
              resource_type: typeFilter || undefined, 
              limit: 200,
            });
            items = (resp?.data as any[]) ?? [];
          }
        }
        // Filter to only show resources from accounts in current scope
        if (currentAccountIds.length > 0 && items.length > 0) {
          items = items.filter((a: any) => currentAccountIds.includes(a.account_id));
        }
      }
      
      setResources(items.map((a: any) => ({
        id: a.id, cloud_resource_id: a.cloud_resource_id ?? a.id, provider: a.provider, account_id: a.account_id,
        organization_id: a.organization_id ?? '', region: a.region ?? 'global', resource_type: a.resource_type,
        name: a.name, tags: a.tags ?? {}, is_public: a.is_public ?? false, environment: a.environment ?? 'unknown',
        first_seen_at: a.first_seen_at ?? null, last_seen_at: a.last_seen_at ?? null,
        // Graph service enrichment fields
        risk_score: a.risk_score ?? 0,
        open_findings_count: a.open_findings_count ?? 0,
        freshness_state: a.freshness_state ?? 'fresh',
      })));
    } catch (e) { 
      console.error('Error fetching resources:', e);
      setError(e instanceof Error ? e.message : 'Failed to load'); 
    }
    finally { setLoading(false); }
  }, [debSearch, typeFilter, globalAccountId, globalProvider]);

  React.useEffect(() => { fetchResources(); }, [fetchResources]);

  const allTypes = React.useMemo(() => Array.from(new Set(resources.map(r => r.resource_type))).sort(), [resources]);
  const allRegions = React.useMemo(() => Array.from(new Set(resources.map(r => r.region).filter(Boolean))).sort(), [resources]);

  const catCounts = React.useMemo(() => {
    const c: Record<string, number> = {};
    for (const r of resources) { const k = getCat(r.resource_type); c[k] = (c[k] ?? 0) + 1; }
    return c;
  }, [resources]);

  const catRiskCounts = React.useMemo(() => {
    const c: Record<string, { critical: number; high: number; total: number }> = {};
    for (const r of resources) {
      const k = getCat(r.resource_type);
      if (!c[k]) c[k] = { critical: 0, high: 0, total: 0 };
      c[k].total++;
      const score = (r as any).risk_score ?? deriveRisk(r);
      if (score >= 70) c[k].critical++;
      else if (score >= 40) c[k].high++;
    }
    return c;
  }, [resources]);

  const filtered = React.useMemo(() => {
    let arr = resources;
    if (catFilter) arr = arr.filter(r => getCat(r.resource_type) === catFilter);
    if (regionFilter) arr = arr.filter(r => r.region === regionFilter);
    if (envFilter) arr = arr.filter(r => r.environment === envFilter);
    return arr;
  }, [resources, catFilter, regionFilter, envFilter]);

  const sorted = React.useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => {
      const m = sortDir === 'asc' ? 1 : -1;
      switch (sortField) {
        case 'type':     return a.resource_type.localeCompare(b.resource_type) * m;
        case 'provider': return a.provider.localeCompare(b.provider) * m;
        case 'region':   return a.region.localeCompare(b.region) * m;
        case 'env':      return a.environment.localeCompare(b.environment) * m;
        case 'risk':     return (deriveRisk(a) - deriveRisk(b)) * m;
        case 'risk_score': return (((a as any).risk_score ?? 0) - ((b as any).risk_score ?? 0)) * m;
        case 'findings': return (((a as any).open_findings_count ?? 0) - ((b as any).open_findings_count ?? 0)) * m;
        default:         return a.name.localeCompare(b.name) * m;
      }
    });
    return arr;
  }, [filtered, sortField, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / perPage));
  const safePage = Math.min(page, totalPages);
  const pageItems = sorted.slice((safePage - 1) * perPage, safePage * perPage);
  const pages = buildPages(safePage, totalPages);

  const toggleSort = (f: string) => { if (sortField === f) setSortDir(d => d === 'asc' ? 'desc' : 'asc'); else { setSortField(f); setSortDir('asc'); } };

  const handleExport = () => {
    const rows = sorted.map(r => [r.name, r.cloud_resource_id, r.resource_type, r.provider, r.region, r.environment, r.is_public ? 'Public' : 'Private'].map(v => `"${v}"`).join(','));
    const csv = ['Name,Resource ID,Type,Provider,Region,Environment,Exposure', ...rows].join('\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = 'assets.csv'; a.click();
  };

  const hasFilters = !!catFilter || !!typeFilter || !!debSearch;

  const awsBtn = "inline-flex items-center gap-1.5 border rounded px-3 py-1.5 text-sm transition-colors select-none";

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-baseline gap-2">
            <h2 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Asset Inventory</h2>
            <span className="text-lg" style={{ color: 'var(--text-secondary)' }}>({loading ? '…' : sorted.length.toLocaleString()})</span>
          </div>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>Cloud assets discovered across your cloud accounts.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchResources} disabled={loading} className="flex items-center justify-center w-8 h-8 rounded-full border border-[var(--accent)] text-[var(--accent)] transition-colors">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </button>
          <button onClick={handleExport} className={awsBtn} style={{ borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}><Download className="h-3.5 w-3.5" /> Export</button>
          <button onClick={() => setViewMode(v => v === 'table' ? 'graph' : 'table')} className={awsBtn} style={{ backgroundColor: 'var(--btn-primary-bg)', color: 'white' }}>
            <Share2 className="h-3.5 w-3.5" /> {viewMode === 'graph' ? 'Table view' : 'Graph view'}
          </button>
        </div>
      </div>

      {viewMode === 'table' && (
        <>
          <div className="flex items-center gap-0 border-b overflow-x-auto scrollbar-hide">
            {[{ id: '', label: 'All resources', count: resources.length }, ...CATEGORIES.map(c => ({ id: c.id, label: c.label, count: catCounts[c.id] ?? 0 })).filter(c => c.count > 0)].map(tab => {
              const active = catFilter === tab.id;
              const riskInfo = tab.id ? catRiskCounts[tab.id] : null;
              return (
                <button key={tab.id} onClick={() => setCatFilter(tab.id)}
                  className="px-4 py-2.5 text-sm border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5"
                  style={{ borderBottomColor: active ? 'var(--accent)' : 'transparent', color: active ? 'var(--accent)' : 'var(--text-secondary)' }}>
                  {tab.label}
                  {tab.count > 0 && <span className="text-xs">({tab.count.toLocaleString()})</span>}
                  {riskInfo && riskInfo.critical > 0 && (
                    <span className="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ backgroundColor: 'var(--critical-bg)', color: 'var(--critical)' }}>
                      {riskInfo.critical}
                    </span>
                  )}
                  {riskInfo && riskInfo.high > 0 && riskInfo.critical === 0 && (
                    <span className="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ backgroundColor: 'var(--high-bg)', color: 'var(--high)' }}>
                      {riskInfo.high}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <div className="relative w-64">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-tertiary)]" />
              <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search" className="w-full border rounded pl-8 pr-8 py-1.5 text-sm focus:outline-none bg-[var(--bg-surface)] text-[var(--text-primary)]" style={{ borderColor: 'var(--border-default)' }} />
              {search && <button onClick={() => setSearch('')} className='absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]'><X className="h-3.5 w-3.5" /></button>}
            </div>
            <TypeDropdown value={typeFilter} onChange={setTypeFilter} types={allTypes} />
            <RegionDropdown value={regionFilter} onChange={setRegionFilter} regions={allRegions} />
            <EnvDropdown value={envFilter} onChange={setEnvFilter} />
            <div className="flex-1" />
            <div className="flex items-center gap-1">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={safePage === 1} className="w-7 h-7 flex items-center justify-center border rounded disabled:opacity-40"><ChevronLeft className="h-4 w-4" /></button>
              {pages.map((p, i) => p === '…' ? <span key={i} className="px-1 text-[var(--text-tertiary)]">…</span> : <button key={i} onClick={() => setPage(p as number)} className={cn("w-7 h-7 text-xs font-medium border rounded", p === safePage ? "bg-[var(--btn-primary-bg)] text-white border-[var(--btn-primary-bg)]" : "text-[var(--text-primary)] border-[var(--border-default)]")}>{p}</button>)}
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={safePage === totalPages} className="w-7 h-7 flex items-center justify-center border rounded disabled:opacity-40"><ChevronRight className="h-4 w-4" /></button>
              <button onClick={() => setShowPrefs(true)} className="w-7 h-7 flex items-center justify-center border rounded ml-1"><Settings className="h-4 w-4" /></button>
            </div>
          </div>
        </>
      )}

      {error && <div className="p-3 rounded border border-[var(--critical)] bg-[var(--critical-dim)] text-[var(--critical)] text-sm">{error}</div>}

      {viewMode === 'graph' ? (
        <div className="rounded-lg overflow-hidden bg-[var(--bg-surface)] -mx-4 sm:-mx-6" style={{ height: 'calc(100vh - 200px)', minHeight: '600px' }}>
          <AssetGraph resources={filtered} loading={loading} onSwitchToTable={() => setViewMode('table')} />
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden bg-[var(--bg-surface)]">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-[var(--bg-elevated)] border-b-2 border-[var(--border-default)]">
                  <th className="px-3 py-2.5 w-10" />
                  <SortTh label="Resource name" field="name" sortField={sortField} sortDir={sortDir} onSort={toggleSort} />
                  {visibleCols.has('type') && <SortTh label="Type" field="type" sortField={sortField} sortDir={sortDir} onSort={toggleSort} />}
                  {visibleCols.has('provider') && <SortTh label="Provider" field="provider" sortField={sortField} sortDir={sortDir} onSort={toggleSort} />}
                  {showAccountCol && <th className="px-3 py-2.5 text-left text-xs font-semibold text-[var(--text-primary)]">Account</th>}
                  {visibleCols.has('region') && <SortTh label="Region" field="region" sortField={sortField} sortDir={sortDir} onSort={toggleSort} />}
                  {visibleCols.has('environment') && <SortTh label="Environment" field="env" sortField={sortField} sortDir={sortDir} onSort={toggleSort} />}
                  {visibleCols.has('risk_score') && <SortTh label="Risk" field="risk_score" sortField={sortField} sortDir={sortDir} onSort={toggleSort} />}
                  {visibleCols.has('findings') && <SortTh label="Findings" field="findings" sortField={sortField} sortDir={sortDir} onSort={toggleSort} />}
                  {visibleCols.has('exposure') && <SortTh label="Exposure" field="risk" sortField={sortField} sortDir={sortDir} onSort={toggleSort} />}
                  {visibleCols.has('tags') && <th className="px-3 py-2.5 text-left text-xs font-semibold text-[var(--text-primary)]">Tags</th>}
                </tr>
              </thead>
              <tbody>
                {loading ? Array.from({ length: 10 }).map((_, i) => <tr key={i} className="border-b border-[var(--border-faint)]"><td colSpan={9} className="px-3 py-4"><div className="h-4 bg-[var(--bg-elevated)] animate-pulse rounded w-full" /></td></tr>) : pageItems.length === 0 ? <tr><td colSpan={9} className="px-6 py-12 text-center text-[var(--text-secondary)]">{scopeAccountIds.length === 0 ? 'No accounts connected.' : 'No resources found.'}</td></tr> : pageItems.map(r => (
                  <tr key={r.id} className="border-b border-[var(--border-faint)] hover:bg-[var(--bg-elevated)] transition-colors">
                    <td className="px-3 py-2.5 w-10"><AwsIcon type={getAssetTypeKey(r.resource_type)} size={24} /></td>
                    <td className="px-3 py-2.5 max-w-[200px]"><div className="font-medium truncate text-[var(--accent)]">{r.name}</div><div className="text-[10px] font-mono text-[var(--text-tertiary)] truncate">{r.cloud_resource_id}</div></td>
                    {visibleCols.has('type') && <td className="px-3 py-2.5 truncate max-w-[150px]">{fmtType(r.resource_type)}</td>}
                    {visibleCols.has('provider') && <td className="px-3 py-2.5">{fmtProvider(r.provider)}</td>}
                    {showAccountCol && <td className="px-3 py-2.5 max-w-[150px] truncate"><div className="text-xs">{accountNameMap[r.account_id] || r.account_id}</div></td>}
                    {visibleCols.has('region') && <td className="px-3 py-2.5">{r.region}</td>}
                    {visibleCols.has('environment') && <td className="px-3 py-2.5">{r.environment}</td>}
                    {visibleCols.has('risk_score') && <td className="px-3 py-2.5">
                      {(() => {
                        const score = (r as any).risk_score ?? deriveRisk(r);
                        const color = score >= 70 ? 'var(--critical)' : score >= 40 ? 'var(--high)' : score >= 20 ? 'var(--medium)' : 'var(--low)';
                        const bg = score >= 70 ? 'var(--critical-bg)' : score >= 40 ? 'var(--high-bg)' : score >= 20 ? 'var(--medium-bg)' : 'var(--low-bg)';
                        return <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold" style={{ color, backgroundColor: bg }}>{score}</span>;
                      })()}
                    </td>}
                    {visibleCols.has('findings') && <td className="px-3 py-2.5">
                      {(() => {
                        const count = (r as any).open_findings_count ?? 0;
                        if (count === 0) return <span style={{ color: 'var(--text-tertiary)' }}>0</span>;
                        return <span className="font-mono font-semibold" style={{ color: count >= 5 ? 'var(--critical)' : count >= 2 ? 'var(--high)' : 'var(--medium)' }}>{count}</span>;
                      })()}
                    </td>}
                    {visibleCols.has('exposure') && <td className="px-3 py-2.5">{r.is_public ? <span className="text-[var(--critical)] flex items-center gap-1 font-medium"><Globe className="h-3 w-3" /> Public</span> : 'None'}</td>}
                    {visibleCols.has('tags') && <td className="px-3 py-2.5 max-w-[150px] truncate"><div className="flex flex-wrap gap-1">{Object.entries(r.tags ?? {}).slice(0, 2).map(([k, v]) => <span key={k} className="text-[10px] border px-1 rounded bg-[var(--bg-elevated)]">{k}:{v}</span>)}</div></td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showPrefs && <PreferencesModal perPage={perPage} visibleCols={visibleCols} onConfirm={(n, c) => { setPerPage(n); setVisibleCols(c); setPage(1); setShowPrefs(false); }} onCancel={() => setShowPrefs(false)} />}
    </div>
  );
}
