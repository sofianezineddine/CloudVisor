'use client';

import * as React from 'react';
import dynamic from 'next/dynamic';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import ProviderBadge from '@/components/ui/provider-badge';
import {
  Search, RefreshCw, Loader2, Globe, ChevronLeft, ChevronRight,
  ChevronDown, X, ArrowUp, ArrowDown, ArrowUpDown, Download, Share2, Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { connectorAPI, DiscoveredResource } from '@/lib/api/connector';
import apiClient from '@/lib/api/apiClient';
import { useScopeStore } from '@/stores/scope';
import { NoAccountsConnectedEmptyState } from '@/components/ui/no-accounts-empty-state';
import { NoScanDataEmptyState } from '@/components/ui/no-scan-empty-state';

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

function deriveRisk(r: DiscoveredResource): number {
  let s = 10; if (r.is_public) s += 40; if (r.environment === 'prod') s = Math.round(s * 1.5);
  return Math.min(s, 100);
}

function buildPages(cur: number, tot: number): (number | '…')[] {
  if (tot <= 7) return Array.from({ length: tot }, (_, i) => i + 1);
  if (cur <= 4) return [1, 2, 3, 4, 5, '…', tot];
  if (cur >= tot - 3) return [1, '…', tot - 4, tot - 3, tot - 2, tot - 1, tot];
  return [1, '…', cur - 1, cur, cur + 1, '…', tot];
}

// ─── AWS-style "Filter by Type" dropdown ─────────────────────────────────────

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

// ─── AWS-style SVG icon components ───────────────────────────────────────────

function AwsIcon({ type, size = 20 }: { type: string; size?: number }) {
  const s = size;
  const icons: Record<string, React.ReactNode> = {
    // IAM
    iamrole: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><path d="M20 8c-3.3 0-6 2.7-6 6 0 2.2 1.2 4.1 3 5.2V22l-5 3v3h16v-3l-5-3v-2.8c1.8-1.1 3-3 3-5.2 0-3.3-2.7-6-6-6z" fill="#DD344C"/></svg>,
    iamuser: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><circle cx="20" cy="15" r="6" fill="#DD344C"/><path d="M8 32c0-6.6 5.4-12 12-12s12 5.4 12 12" stroke="#DD344C" strokeWidth="2.5" strokeLinecap="round"/></svg>,
    iampolicy: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><rect x="10" y="8" width="20" height="24" rx="2" stroke="#DD344C" strokeWidth="2"/><path d="M14 16h12M14 20h12M14 24h8" stroke="#DD344C" strokeWidth="2" strokeLinecap="round"/></svg>,
    // Compute
    ec2: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#ED7100" fillOpacity=".12"/><rect x="8" y="8" width="24" height="24" rx="3" stroke="#ED7100" strokeWidth="2"/><rect x="13" y="13" width="14" height="14" rx="1" fill="#ED7100" fillOpacity=".3"/><path d="M4 16h4M4 24h4M32 16h4M32 24h4M16 4v4M24 4v4M16 32v4M24 32v4" stroke="#ED7100" strokeWidth="2" strokeLinecap="round"/></svg>,
    instance: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#ED7100" fillOpacity=".12"/><rect x="8" y="8" width="24" height="24" rx="3" stroke="#ED7100" strokeWidth="2"/><rect x="13" y="13" width="14" height="14" rx="1" fill="#ED7100" fillOpacity=".3"/></svg>,
    lambdafunction: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#ED7100" fillOpacity=".12"/><path d="M10 30L18 10l4 10 4-6 4 16" stroke="#ED7100" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
    cloudfunction: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#ED7100" fillOpacity=".12"/><path d="M10 30L18 10l4 10 4-6 4 16" stroke="#ED7100" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
    // Kubernetes
    ekscluster: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#ED7100" fillOpacity=".12"/><path d="M20 8l10 5.8v11.4L20 31 10 25.2V13.8L20 8z" stroke="#ED7100" strokeWidth="2"/><circle cx="20" cy="20" r="4" fill="#ED7100"/></svg>,
    // Network
    vpc: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#8C4FFF" fillOpacity=".12"/><rect x="6" y="6" width="28" height="28" rx="14" stroke="#8C4FFF" strokeWidth="2"/><rect x="12" y="12" width="16" height="16" rx="8" stroke="#8C4FFF" strokeWidth="2"/><circle cx="20" cy="20" r="3" fill="#8C4FFF"/></svg>,
    subnet: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#8C4FFF" fillOpacity=".12"/><rect x="8" y="8" width="24" height="24" rx="4" stroke="#8C4FFF" strokeWidth="2"/><rect x="14" y="14" width="12" height="12" rx="2" stroke="#8C4FFF" strokeWidth="1.5"/></svg>,
    securitygroup: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><path d="M20 8l10 4v8c0 6-4.5 10.5-10 12-5.5-1.5-10-6-10-12v-8l10-4z" stroke="#DD344C" strokeWidth="2"/><path d="M15 20l3 3 7-7" stroke="#DD344C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>,
    networksecuritygroup: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><path d="M20 8l10 4v8c0 6-4.5 10.5-10 12-5.5-1.5-10-6-10-12v-8l10-4z" stroke="#DD344C" strokeWidth="2"/></svg>,
    // Storage
    s3bucket: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#3F8624" fillOpacity=".12"/><ellipse cx="20" cy="13" rx="12" ry="5" stroke="#3F8624" strokeWidth="2"/><path d="M8 13v14c0 2.8 5.4 5 12 5s12-2.2 12-5V13" stroke="#3F8624" strokeWidth="2"/><path d="M8 20c0 2.8 5.4 5 12 5s12-2.2 12-5" stroke="#3F8624" strokeWidth="1.5"/></svg>,
    bucket: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#3F8624" fillOpacity=".12"/><ellipse cx="20" cy="13" rx="12" ry="5" stroke="#3F8624" strokeWidth="2"/><path d="M8 13v14c0 2.8 5.4 5 12 5s12-2.2 12-5V13" stroke="#3F8624" strokeWidth="2"/></svg>,
    storageaccount: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#3F8624" fillOpacity=".12"/><rect x="8" y="14" width="24" height="18" rx="2" stroke="#3F8624" strokeWidth="2"/><path d="M14 14V10a6 6 0 0112 0v4" stroke="#3F8624" strokeWidth="2"/></svg>,
    // Database
    rdsinstance: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#3F8624" fillOpacity=".12"/><ellipse cx="20" cy="12" rx="12" ry="4" stroke="#3F8624" strokeWidth="2"/><path d="M8 12v16c0 2.2 5.4 4 12 4s12-1.8 12-4V12" stroke="#3F8624" strokeWidth="2"/><path d="M8 20c0 2.2 5.4 4 12 4s12-1.8 12-4" stroke="#3F8624" strokeWidth="1.5"/></svg>,
    dynamodbtable: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#3F8624" fillOpacity=".12"/><path d="M20 8c-6 0-10 2-10 4v16c0 2 4 4 10 4s10-2 10-4V12c0-2-4-4-10-4z" stroke="#3F8624" strokeWidth="2"/><path d="M10 16c0 2 4 4 10 4s10-2 10-4M10 24c0 2 4 4 10 4s10-2 10-4" stroke="#3F8624" strokeWidth="1.5"/></svg>,
    // Security
    kmskey: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><circle cx="16" cy="18" r="7" stroke="#DD344C" strokeWidth="2"/><path d="M21 22l10 10M27 28l3-3" stroke="#DD344C" strokeWidth="2" strokeLinecap="round"/></svg>,
    keyvault: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#DD344C" fillOpacity=".12"/><circle cx="16" cy="18" r="7" stroke="#DD344C" strokeWidth="2"/><path d="M21 22l10 10" stroke="#DD344C" strokeWidth="2" strokeLinecap="round"/></svg>,
    // Messaging
    snstopic: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#E7157B" fillOpacity=".12"/><path d="M8 14h24v12a2 2 0 01-2 2H10a2 2 0 01-2-2V14z" stroke="#E7157B" strokeWidth="2"/><path d="M8 14l12 9 12-9" stroke="#E7157B" strokeWidth="2" strokeLinecap="round"/></svg>,
    sqsqueue: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#E7157B" fillOpacity=".12"/><rect x="6" y="14" width="28" height="12" rx="6" stroke="#E7157B" strokeWidth="2"/><circle cx="14" cy="20" r="2" fill="#E7157B"/><circle cx="20" cy="20" r="2" fill="#E7157B"/><circle cx="26" cy="20" r="2" fill="#E7157B"/></svg>,
    // Logging / Monitoring
    cloudtrailtrail: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#527FFF" fillOpacity=".12"/><path d="M8 28l7-10 5 6 5-8 7 12" stroke="#527FFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
    // Default
    default: <svg width={s} height={s} viewBox="0 0 40 40" fill="none"><rect width="40" height="40" rx="8" fill="#6b7194" fillOpacity=".12"/><rect x="10" y="10" width="20" height="20" rx="4" stroke="#6b7194" strokeWidth="2"/></svg>,
  };
  return <>{icons[type] || icons.default}</>;
}

const ASSET_TYPE_COLORS: Record<string, string> = {
  iamrole: '#DD344C', iamuser: '#DD344C', iampolicy: '#DD344C',
  ec2: '#ED7100', instance: '#ED7100', lambdafunction: '#ED7100', cloudfunction: '#ED7100',
  ekscluster: '#ED7100', akscluster: '#ED7100', gkecluster: '#ED7100',
  vpc: '#8C4FFF', subnet: '#8C4FFF', securitygroup: '#DD344C', networksecuritygroup: '#DD344C',
  s3bucket: '#3F8624', bucket: '#3F8624', storageaccount: '#3F8624',
  rdsinstance: '#3F8624', dynamodbtable: '#3F8624',
  kmskey: '#DD344C', keyvault: '#DD344C',
  snstopic: '#E7157B', sqsqueue: '#E7157B',
  cloudtrailtrail: '#527FFF',
};

function getAssetTypeKey(resourceType: string): string {
  return resourceType.split('::').pop()?.toLowerCase().replace(/_/g, '') || 'default';
}

// ─── Region dropdown ──────────────────────────────────────────────────────────

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

// ─── Environment dropdown ─────────────────────────────────────────────────────

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

// ─── Sort header cell ─────────────────────────────────────────────────────────

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
        {active && <span className="ml-0.5 text-blue-500">▲</span>}
      </button>
    </th>
  );
}

// ─── Column definitions ───────────────────────────────────────────────────────

const ALL_COLUMNS = [
  { id: 'name',        label: 'Resource name', required: true  },
  { id: 'type',        label: 'Type',          required: false },
  { id: 'provider',    label: 'Provider',      required: false },
  { id: 'region',      label: 'Region',        required: false },
  { id: 'environment', label: 'Environment',   required: false },
  { id: 'exposure',    label: 'Exposure',      required: false },
  { id: 'tags',        label: 'Tags',          required: false },
] as const;

type ColumnId = typeof ALL_COLUMNS[number]['id'];

// ─── Preferences modal ────────────────────────────────────────────────────────

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

  // Close on backdrop click
  const backdropRef = React.useRef<HTMLDivElement>(null);

  // Overlay styles
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
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid var(--border-default)' }}>
          <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Preferences</h2>
          <button
            onClick={onCancel}
            className="flex items-center justify-center w-7 h-7 rounded transition-colors"
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)'}
            onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent'}
          >
            {/* × close icon */}
            <span style={{ fontSize: 18, lineHeight: 1 }}>×</span>
          </button>
        </div>

        {/* Body — two columns like AWS */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left: Page size */}
          <div className="px-6 py-5 flex-shrink-0" style={{ width: 220, borderRight: '1px solid var(--border-default)' }}>
            <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-secondary)' }}>
              Page size
            </p>
            <div className="space-y-2.5">
              {[10, 20, 25, 50, 100].map(n => (
                <label key={n} className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="radio"
                    name="pageSize"
                    checked={draftPerPage === n}
                    onChange={() => setDraftPerPage(n)}
                    style={{ accentColor: 'var(--accent)', width: 16, height: 16, cursor: 'pointer' }}
                  />
                  <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{n} rows</span>
                </label>
              ))}
            </div>

            {/* Wrap lines — like AWS */}
            <div className="mt-5 pt-4" style={{ borderTop: '1px solid var(--border-faint)' }}>
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  style={{ accentColor: 'var(--accent)', width: 16, height: 16, marginTop: 2, cursor: 'pointer' }}
                />
                <div>
                  <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Wrap lines</p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                    Select to see all the text and wrap the lines
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Right: Visible columns */}
          <div className="px-6 py-5 flex-1 overflow-y-auto">
            <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-secondary)' }}>
              Select visible columns
            </p>
            <div className="space-y-0">
              {ALL_COLUMNS.map(col => {
                const on = draftCols.has(col.id);
                return (
                  <div
                    key={col.id}
                    className="flex items-center justify-between py-2.5"
                    style={{ borderBottom: '1px solid var(--border-faint)' }}
                  >
                    <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{col.label}</span>
                    {/* AWS-style toggle switch */}
                    <button
                      onClick={() => !col.required && toggleCol(col.id)}
                      disabled={col.required}
                      title={col.required ? 'This column is always visible' : undefined}
                      style={{
                        width: 36, height: 20,
                        borderRadius: 10,
                        border: 'none',
                        cursor: col.required ? 'not-allowed' : 'pointer',
                        backgroundColor: on ? 'var(--accent)' : 'var(--border-default)',
                        position: 'relative',
                        transition: 'background-color 0.2s',
                        flexShrink: 0,
                        opacity: col.required ? 0.6 : 1,
                      }}
                    >
                      <span style={{
                        position: 'absolute',
                        top: 2, left: on ? 18 : 2,
                        width: 16, height: 16,
                        borderRadius: '50%',
                        backgroundColor: '#ffffff',
                        transition: 'left 0.2s',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                      }} />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4" style={{ borderTop: '1px solid var(--border-default)' }}>
          <button
            onClick={onCancel}
            className="border rounded px-4 py-1.5 text-sm font-normal transition-colors"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)'}
            onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-surface)'}
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(draftPerPage, draftCols)}
            className="border rounded px-4 py-1.5 text-sm font-semibold transition-colors"
            style={{ borderColor: '#e07b00', backgroundColor: '#ec7211', color: '#ffffff' }}
            onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#cc6600'}
            onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#ec7211'}
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AssetsPage() {
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
    new Set(['name', 'type', 'provider', 'region', 'environment', 'exposure', 'tags'] as ColumnId[])
  );

  const [resources, setResources] = React.useState<DiscoveredResource[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const globalAccountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const globalProvider  = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
  const scopeAccountIds = useScopeStore(s => s.accountIds);
  const scopeMode       = useScopeStore(s => s.mode);
  const scopeAccounts   = useScopeStore(s => s.accounts);

  // Build account_id → name lookup for the "Account" column
  const accountNameMap = React.useMemo(() => {
    const m: Record<string, string> = {};
    for (const a of scopeAccounts) {
      m[a.account_id] = a.name || a.account_id;
    }
    return m;
  }, [scopeAccounts]);

  // Show Account column only when viewing all accounts under a provider
  const showAccountCol = scopeMode === 'provider';

  React.useEffect(() => { document.title = 'Asset Inventory - CloudVisor'; }, []);
  React.useEffect(() => { const t = setTimeout(() => setDebSearch(search), 300); return () => clearTimeout(t); }, [search]);
  React.useEffect(() => { setPage(1); }, [debSearch, typeFilter, catFilter, regionFilter, envFilter, globalAccountId, globalProvider]);

  const fetchResources = React.useCallback(async () => {
    setLoading(true); setError(null);
    try {
      // Use the API gateway (/v1/assets) instead of calling the connector directly
      const resp = await apiClient.assets.list({
        account_id: globalAccountId,
        provider: !globalAccountId ? globalProvider : undefined,
        search: debSearch || undefined,
        resource_type: typeFilter || undefined,
        limit: 500, offset: 0,
      });
      // Gateway returns { data: [...], total, meta }; connector returned { resources: [...] }
      const items = (resp?.data as any[]) ?? [];
      // Map gateway asset shape to DiscoveredResource shape for compatibility
      setResources(items.map((a: any) => ({
        id: a.id,
        cloud_resource_id: a.cloud_resource_id ?? a.id,
        provider: a.provider,
        account_id: a.account_id,
        organization_id: a.organization_id ?? '',
        region: a.region ?? 'global',
        resource_type: a.resource_type,
        name: a.name,
        tags: a.tags ?? {},
        is_public: a.is_public ?? false,
        environment: a.environment ?? 'unknown',
        first_seen_at: a.first_seen_at ?? null,
        last_seen_at: a.last_seen_at ?? null,
      })));
    } catch (e) { setError(e instanceof Error ? e.message : 'Failed to load'); }
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
  const toggleRow = (id: string) => { const n = new Set(selected); n.has(id) ? n.delete(id) : n.add(id); setSelected(n); };
  const allChecked = pageItems.length > 0 && pageItems.every(r => selected.has(r.id));
  const toggleAll = () => {
    const n = new Set(selected);
    if (allChecked) pageItems.forEach(r => n.delete(r.id)); else pageItems.forEach(r => n.add(r.id));
    setSelected(n);
  };

  const handleExport = () => {
    const rows = sorted.map(r => [r.name, r.cloud_resource_id, r.resource_type, r.provider, r.region, r.environment, r.is_public ? 'Public' : 'Private'].map(v => `"${v}"`).join(','));
    const csv = ['Name,Resource ID,Type,Provider,Region,Environment,Exposure', ...rows].join('\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = 'assets.csv'; a.click();
  };

  const hasFilters = !!catFilter || !!typeFilter || !!debSearch;

  // ── AWS-style button styles ──────────────────────────────────────────────────
  const awsBtn = "inline-flex items-center gap-1.5 border rounded px-3 py-1.5 text-sm font-normal transition-colors select-none";
  const awsBtnStyle: React.CSSProperties = { borderColor: 'var(--border-default)', color: 'var(--text-primary)', backgroundColor: 'var(--bg-surface)' };
  const awsBtnHover = (e: React.MouseEvent) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-strong)'; (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'; };
  const awsBtnLeave = (e: React.MouseEvent) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-default)'; (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-surface)'; };

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Asset Inventory' }]}>
        {scopeAccountIds.length === 0 ? <NoAccountsConnectedEmptyState /> :
         !loading && resources.length === 0 && !hasFilters ? (
          <NoScanDataEmptyState title="No assets found" description="No resources discovered yet. Connect a cloud account and run a sync." />
        ) : (
          /* ── Full-viewport fixed container — scrollbar spans full height ── */
          <div style={{
            position: 'fixed',
            top: 104,
            left: 0,
            right: 0,
            bottom: 28,
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: 'var(--bg-base)',
            zIndex: 10,
            overflowY: viewMode === 'graph' ? 'hidden' : 'scroll',
            overflowX: 'hidden',
          }}>

            {/* ── Page title row — sticky at top ─────────────────────── */}
            <div className="flex-shrink-0 flex items-start justify-between gap-4"
              style={{ padding: '16px 24px 12px', backgroundColor: 'var(--bg-surface)', borderBottom: '1px solid var(--border-default)', position: 'sticky', top: 0, zIndex: 8, display: viewMode === 'graph' ? 'none' : 'flex' }}>
              <div>
                <div className="flex items-baseline gap-2">
                  <h1 className="text-2xl font-normal" style={{ color: 'var(--text-primary)' }}>
                    Asset Inventory
                  </h1>
                  <span className="text-xl font-normal" style={{ color: 'var(--text-primary)' }}>
                    ({loading ? '…' : sorted.length.toLocaleString()})
                  </span>
                  <button className="text-xs font-normal" style={{ color: 'var(--accent)' }}>Info</button>
                </div>
                <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                  A resource is a cloud asset discovered by CloudVisor across your cloud account.
                </p>
              </div>

              {/* Action buttons — top right */}
              <div className="flex items-center gap-2 flex-shrink-0 pt-1">
                <button onClick={fetchResources} disabled={loading} title="Refresh"
                  className="flex items-center justify-center w-8 h-8 rounded-full border transition-colors disabled:opacity-50"
                  style={{ borderColor: 'var(--accent)', color: 'var(--accent)', backgroundColor: 'var(--bg-surface)' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--accent-dim)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-surface)'; }}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                </button>
                <button onClick={handleExport} className={awsBtn} style={awsBtnStyle} onMouseEnter={awsBtnHover} onMouseLeave={awsBtnLeave}>
                  <Download className="h-3.5 w-3.5" /> Export
                </button>
                <button onClick={() => setViewMode(v => v === 'table' ? 'graph' : 'table')}
                  className="inline-flex items-center gap-1.5 border rounded px-3 py-1.5 text-sm font-normal transition-colors"
                  style={{ 
                    borderColor: '#e07b00', 
                    backgroundColor: viewMode === 'table' ? '#ec7211' : '#e07b00', 
                    color: '#ffffff' 
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.backgroundColor = '#cc6600'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.backgroundColor = viewMode === 'table' ? '#ec7211' : '#e07b00'; }}>
                  <Share2 className="h-3.5 w-3.5" />
                  {viewMode === 'graph' ? 'Table view' : 'Graph view'}
                </button>
              </div>
            </div>

            {/* ── Category filter tabs — sticky ───────────────────────── */}
            <div className="flex-shrink-0 flex items-center gap-0 border-b overflow-x-auto"
              style={{ borderColor: 'var(--border-default)', scrollbarWidth: 'none', backgroundColor: 'var(--bg-surface)', paddingLeft: 24, paddingRight: 24, position: 'sticky', top: 80, zIndex: 7, display: viewMode === 'graph' ? 'none' : 'flex' }}>
              {[{ id: '', label: 'All resources', count: resources.length }, ...CATEGORIES.map(c => ({ id: c.id, label: c.label, count: catCounts[c.id] ?? 0 })).filter(c => c.count > 0)].map(tab => {
                const active = catFilter === tab.id;
                return (
                  <button key={tab.id} onClick={() => setCatFilter(tab.id)}
                    className="flex-shrink-0 px-4 py-2.5 text-sm font-normal border-b-2 transition-colors whitespace-nowrap"
                    style={{ borderBottomColor: active ? 'var(--accent)' : 'transparent', color: active ? 'var(--accent)' : 'var(--text-secondary)', backgroundColor: 'transparent' }}
                    onMouseEnter={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)'; }}
                    onMouseLeave={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)'; }}>
                    {tab.label}
                    {tab.count > 0 && <span className="ml-1.5 text-xs" style={{ color: active ? 'var(--accent)' : 'var(--text-tertiary)' }}>({tab.count.toLocaleString()})</span>}
                  </button>
                );
              })}
            </div>

            {/* ── Search + Filter + Pagination — sticky ───────────────── */}
            <div className="flex-shrink-0 flex items-center gap-3 flex-wrap"
              style={{ padding: '10px 24px', borderBottom: '1px solid var(--border-faint)', backgroundColor: 'var(--bg-surface)', position: 'sticky', top: 122, zIndex: 6, display: viewMode === 'graph' ? 'none' : 'flex' }}>
              <div className="relative" style={{ width: 280 }}>
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: 'var(--text-tertiary)' }} />
                <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search"
                  className="w-full border rounded pl-8 pr-8 py-1.5 text-sm focus:outline-none"
                  style={{ borderColor: 'var(--border-default)', color: 'var(--text-primary)', backgroundColor: 'var(--bg-surface)' }} />
                {search && (
                  <button onClick={() => setSearch('')} className='absolute right-2.5 top-1/2 -translate-y-1/2' style={{ color: 'var(--text-tertiary)' }}>
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm" style={{ color: 'var(--text-primary)' }}>Filter by Type</span>
                <TypeDropdown value={typeFilter} onChange={setTypeFilter} types={allTypes} />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm" style={{ color: 'var(--text-primary)' }}>Region</span>
                <RegionDropdown value={regionFilter} onChange={setRegionFilter} regions={allRegions} />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm" style={{ color: 'var(--text-primary)' }}>Env</span>
                <EnvDropdown value={envFilter} onChange={setEnvFilter} />
              </div>
              <div className="flex-1" />
              <div className="flex items-center gap-1">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={safePage === 1}
                  className="flex items-center justify-center w-7 h-7 rounded border text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
                  onMouseEnter={e => { if (safePage !== 1) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-surface)'; }}>
                  <ChevronLeft className="h-4 w-4" />
                </button>
                {pages.map((p, i) =>
                  p === '…' ? (
                    <span key={`e${i}`} className="w-7 text-center text-sm" style={{ color: 'var(--text-tertiary)' }}>…</span>
                  ) : (
                    <button key={p} onClick={() => setPage(p as number)}
                      className="flex items-center justify-center w-7 h-7 rounded border text-sm font-medium transition-colors"
                      style={p === safePage
                        ? { borderColor: 'var(--accent)', backgroundColor: 'var(--accent)', color: '#ffffff' }
                        : { borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
                      onMouseEnter={e => { if (p !== safePage) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                      onMouseLeave={e => { if (p !== safePage) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-surface)'; }}>
                      {p}
                    </button>
                  )
                )}
                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={safePage === totalPages}
                  className="flex items-center justify-center w-7 h-7 rounded border text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
                  onMouseEnter={e => { if (safePage !== totalPages) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-surface)'; }}>
                  <ChevronRight className="h-4 w-4" />
                </button>
                <button className="flex items-center justify-center w-7 h-7 rounded border text-sm transition-colors ml-1"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
                  onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)'}
                  onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-surface)'}
                  onClick={() => setShowPrefs(true)} title="Preferences">
                  <Settings className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* ── Error ─────────────────────────────────────────────────── */}
            {error && (
              <div className="flex-shrink-0 mx-6 mt-3 rounded border p-3 text-sm" style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}>
                {error}
              </div>
            )}

            {/* ── Graph view ────────────────────────────────────────────── */}
            {viewMode === 'graph' ? (
              <div style={{ flex: '1 1 0%', minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <AssetGraph
                  resources={filtered}
                  loading={loading}
                  onSwitchToTable={() => setViewMode('table')}
                />
              </div>
            ) : (
              /* ── Table: single table, thead sticky, tbody scrolls ─── */
              <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: 'var(--bg-surface)' }}>

                {/* Scrollable table container */}
                <div className="flex-1 overflow-auto" style={{ minHeight: 0 }}>
                  <table className="w-full border-collapse" style={{ fontSize: 14, minWidth: 800 }}>
                    <thead>
                      <tr style={{ backgroundColor: 'var(--bg-elevated)', position: 'sticky', top: 0, zIndex: 5 }}>
                        <th className="px-3 py-2.5 w-10" style={{ backgroundColor: 'var(--bg-elevated)', borderBottom: '2px solid var(--border-default)' }} />
                        <SortTh label="Resource name" field="name" sortField={sortField} sortDir={sortDir} onSort={toggleSort} />
                        {visibleCols.has('type') && <SortTh label="Type" field="type" sortField={sortField} sortDir={sortDir} onSort={toggleSort} />}
                        {visibleCols.has('provider') && <SortTh label="Provider" field="provider" sortField={sortField} sortDir={sortDir} onSort={toggleSort} />}
                        {showAccountCol && (
                          <th className="px-3 py-2.5 text-left text-xs font-semibold"
                            style={{ color: 'var(--text-primary)', backgroundColor: 'var(--bg-elevated)', borderBottom: '2px solid var(--border-default)', whiteSpace: 'nowrap' }}>
                            Account
                          </th>
                        )}
                        {visibleCols.has('region') && <SortTh label="Region" field="region" sortField={sortField} sortDir={sortDir} onSort={toggleSort} className="hidden lg:table-cell" />}
                        {visibleCols.has('environment') && <SortTh label="Environment" field="env" sortField={sortField} sortDir={sortDir} onSort={toggleSort} className="hidden md:table-cell" />}
                        {visibleCols.has('exposure') && <SortTh label="Exposure" field="risk" sortField={sortField} sortDir={sortDir} onSort={toggleSort} className="hidden md:table-cell" />}
                        {visibleCols.has('tags') && (
                          <th className="px-3 py-2.5 text-left text-xs font-semibold hidden xl:table-cell"
                            style={{ color: 'var(--text-primary)', backgroundColor: 'var(--bg-elevated)', borderBottom: '2px solid var(--border-default)' }}>
                            Tags
                          </th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {loading ? (
                        Array.from({ length: 20 }).map((_, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid var(--border-faint)' }}>
                            {[10, 10, 200, 130, 80, 100, 90, 80, 160].map((w, j) => (
                              <td key={j} className="px-3 py-2.5">
                                <div className="h-4 rounded skeleton" style={{ width: w + (i * j % 30) }} />
                              </td>
                            ))}
                          </tr>
                        ))
                      ) : pageItems.length === 0 ? (
                        <tr>
                          <td colSpan={9} className="px-6 py-16 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
                            {hasFilters ? 'No resources match your filters.' : 'No resources discovered yet.'}
                          </td>
                        </tr>
                      ) : (
                        pageItems.map(r => {
                          const isSelected = selected.has(r.id);
                          const tagEntries = Object.entries(r.tags ?? {}).slice(0, 2);
                          return (
                            <tr key={r.id}
                              style={{ borderBottom: '1px solid var(--border-faint)', backgroundColor: 'transparent' }}
                              onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'var(--bg-elevated)'; }}
                              onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'transparent'; }}>
                              {/* Asset type icon */}
                              <td className="px-3 py-2.5 w-10">
                                <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0">
                                  <AwsIcon type={getAssetTypeKey(r.resource_type)} size={28} />
                                </span>
                              </td>
                              <td className="px-3 py-2.5" style={{ maxWidth: 260 }}>
                                <div className="font-normal truncate cursor-pointer hover:underline"
                                  style={{ color: 'var(--accent)' }} title={r.name}>{r.name}</div>
                                <div className="font-mono truncate mt-0.5"
                                  style={{ color: 'var(--text-tertiary)', fontSize: 11 }} title={r.cloud_resource_id}>{r.cloud_resource_id}</div>
                              </td>
                              {visibleCols.has('type') && (
                                <td className="px-3 py-2.5" style={{ color: 'var(--text-primary)', maxWidth: 160 }}>
                                  <div className="truncate" title={r.resource_type}>{fmtType(r.resource_type)}</div>
                                </td>
                              )}
                              {visibleCols.has('provider') && (
                                <td className="px-3 py-2.5" style={{ color: 'var(--text-primary)' }}>{fmtProvider(r.provider)}</td>
                              )}
                              {/* Account column — only when viewing all accounts under a provider */}
                              {showAccountCol && (
                                <td className="px-3 py-2.5" style={{ maxWidth: 180 }}>
                                  <div className="flex flex-col">
                                    <span className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}
                                      title={accountNameMap[r.account_id] || r.account_id}>
                                      {accountNameMap[r.account_id] || r.account_id}
                                    </span>
                                    {accountNameMap[r.account_id] && accountNameMap[r.account_id] !== r.account_id && (
                                      <span className="text-xs font-mono truncate mt-0.5" style={{ color: 'var(--text-tertiary)', fontSize: 10 }}
                                        title={r.account_id}>
                                        {r.account_id}
                                      </span>
                                    )}
                                  </div>
                                </td>
                              )}
                              {visibleCols.has('region') && (
                                <td className="px-3 py-2.5 hidden lg:table-cell" style={{ color: 'var(--text-primary)', fontSize: 13 }}>{r.region}</td>
                              )}
                              {visibleCols.has('environment') && (
                                <td className="px-3 py-2.5 hidden md:table-cell" style={{ color: 'var(--text-primary)' }}>
                                  {r.environment === 'unknown' ? '—' : r.environment}
                                </td>
                              )}
                              {visibleCols.has('exposure') && (
                                <td className="px-3 py-2.5 hidden md:table-cell">
                                  {r.is_public ? (
                                    <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: 'var(--critical)' }}>
                                      <Globe className="h-3 w-3" /> Public
                                    </span>
                                  ) : (
                                    <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>None</span>
                                  )}
                                </td>
                              )}
                              {visibleCols.has('tags') && (
                                <td className="px-3 py-2.5 hidden xl:table-cell" style={{ maxWidth: 220 }}>
                                  {tagEntries.length > 0 ? (
                                    <div className="flex flex-wrap gap-1">
                                      {tagEntries.map(([k, v]) => (
                                        <span key={k} className="inline-flex items-center rounded px-1.5 py-0.5 text-xs"
                                          style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)', border: '1px solid var(--border-default)' }}>
                                          {k}: {v}
                                        </span>
                                      ))}
                                      {Object.keys(r.tags ?? {}).length > 2 && (
                                        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>+{Object.keys(r.tags).length - 2}</span>
                                      )}
                                    </div>
                                  ) : (
                                    <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>—</span>
                                  )}
                                </td>
                              )}
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ── Preferences modal ─────────────────────────────────────── */}
            {showPrefs && (
              <PreferencesModal
                perPage={perPage}
                visibleCols={visibleCols}
                onConfirm={(newPerPage, newCols) => {
                  setPerPage(newPerPage);
                  setVisibleCols(newCols);
                  setPage(1);
                  setShowPrefs(false);
                }}
                onCancel={() => setShowPrefs(false)}
              />
            )}
          </div>
        )}
      </AppLayout>
    </ProtectedRoute>
  );
}
