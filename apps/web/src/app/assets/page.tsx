'use client';

import * as React from 'react';
import dynamic from 'next/dynamic';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { RiskScore } from '@/components/ui/risk-score';
import ProviderBadge from '@/components/ui/provider-badge';
import { Button } from '@/components/ui/button';
import {
  Search, Table2, LayoutGrid, Download, ArrowUpDown,
  RefreshCw, Loader2, Globe, ChevronLeft, ChevronRight,
  ChevronDown, X, SlidersHorizontal,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { connectorAPI, DiscoveredResource, ResourceSummary, CloudAccount } from '@/lib/api/connector';
import { useScopeStore } from '@/stores/scope';
import { NoAccountsConnectedEmptyState } from '@/components/ui/no-accounts-empty-state';
import { NoScanDataEmptyState } from '@/components/ui/no-scan-empty-state';

const AssetGraph = dynamic(
  () => import('@/components/ui/asset-graph').then(m => ({ default: m.AssetGraph })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin" style={{ color: 'var(--accent)' }} />
      </div>
    ),
  }
);

// ─── Resource category taxonomy ───────────────────────────────────────────────

const CATEGORIES: {
  id: string;
  label: string;
  icon: string;
  color: string;
  patterns: string[];
}[] = [
  { id: 'iam', label: 'IAM & Identity', icon: '🔑', color: 'text-orange-400', patterns: ['iam', 'identity', 'user', 'role', 'policy', 'group', 'permission', 'sso', 'saml'] },
  { id: 'compute', label: 'Compute', icon: '⚙️', color: 'text-purple-400', patterns: ['ec2', 'instance', 'vm', 'virtualmachine', 'compute', 'server', 'host', 'node'] },
  { id: 'storage', label: 'Storage', icon: '🗄️', color: 'text-cyan-400', patterns: ['s3', 'bucket', 'storage', 'blob', 'disk', 'volume', 'efs', 'fsx', 'gcs', 'object'] },
  { id: 'network', label: 'Network', icon: '🌐', color: 'text-blue-400', patterns: ['vpc', 'subnet', 'securitygroup', 'nsg', 'firewall', 'loadbalancer', 'elb', 'alb', 'nlb', 'gateway', 'route', 'dns', 'cdn', 'cloudfront', 'waf', 'eip', 'ip', 'network', 'vnet', 'peering'] },
  { id: 'database', label: 'Database', icon: '🗃️', color: 'text-green-400', patterns: ['rds', 'database', 'db', 'sql', 'dynamo', 'cosmos', 'mongo', 'redis', 'elasticache', 'aurora', 'postgres', 'mysql', 'bigquery', 'datastore', 'spanner'] },
  { id: 'serverless', label: 'Serverless', icon: '⚡', color: 'text-yellow-400', patterns: ['lambda', 'function', 'serverless', 'cloudrun', 'appengine', 'fargate', 'ecs', 'step'] },
  { id: 'kubernetes', label: 'Kubernetes', icon: '☸️', color: 'text-indigo-400', patterns: ['eks', 'aks', 'gke', 'oke', 'kubernetes', 'k8s', 'cluster', 'nodegroup', 'pod', 'container'] },
  { id: 'security', label: 'Security', icon: '🛡️', color: 'text-red-400', patterns: ['kms', 'key', 'secret', 'vault', 'certificate', 'acm', 'hsm', 'guardduty', 'shield', 'waf', 'cloudtrail', 'config', 'securityhub'] },
  { id: 'messaging', label: 'Messaging', icon: '📨', color: 'text-pink-400', patterns: ['sns', 'sqs', 'queue', 'topic', 'pubsub', 'eventbus', 'eventhub', 'servicebus', 'kinesis', 'stream', 'notification'] },
];

function getCategoryForResource(resourceType: string): string {
  const lower = resourceType.toLowerCase().replace(/::/g, '');
  for (const cat of CATEGORIES) {
    if (cat.patterns.some(p => lower.includes(p))) return cat.id;
  }
  return 'other';
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatResourceType(rt: string): string {
  const parts = rt.split('::');
  const last = parts[parts.length - 1] || rt;
  return last.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function deriveRisk(r: DiscoveredResource): number {
  let score = 10;
  if (r.is_public) score += 40;
  if (r.environment === 'prod') score = Math.round(score * 1.5);
  return Math.min(score, 100);
}

const ENV_STYLE_MAP: Record<string, React.CSSProperties> = {
  prod: { backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' },
  staging: { backgroundColor: 'var(--medium-dim)', color: 'var(--medium)' },
  dev: { backgroundColor: 'var(--low-dim)', color: 'var(--low)' },
  unknown: { backgroundColor: 'var(--info-dim)', color: 'var(--info)' },
};

const PAGE_SIZE = 50;

// ─── Active filter chip ───────────────────────────────────────────────────────

function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium"
      style={{ borderColor: 'var(--accent)', backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }}
    >
      {label}
      <button
        onClick={onRemove}
        className="ml-0.5 rounded-full p-0.5 transition-colors"
        onMouseEnter={e => {
          (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--accent)';
          (e.currentTarget as HTMLButtonElement).style.color = '#ffffff';
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
          (e.currentTarget as HTMLButtonElement).style.color = 'var(--accent)';
        }}
      >
        <X className="h-2.5 w-2.5" />
      </button>
    </span>
  );
}

// ─── Category filter panel ────────────────────────────────────────────────────

function CategoryPanel({
  selected,
  counts,
  onChange,
}: {
  selected: Set<string>;
  counts: Record<string, number>;
  onChange: (cats: Set<string>) => void;
}) {
  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(next);
  };

  const otherCount = counts['other'] ?? 0;

  return (
    <div className="flex flex-wrap gap-1.5">
      {CATEGORIES.map((cat) => {
        const count = counts[cat.id] ?? 0;
        if (count === 0) return null;
        const active = selected.has(cat.id);
        return (
          <button
            key={cat.id}
            onClick={() => toggle(cat.id)}
            className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all"
            style={
              active
                ? { borderColor: 'var(--accent)', backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }
                : { borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-secondary)' }
            }
            onMouseEnter={e => {
              if (!active) {
                (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-strong)';
                (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)';
              }
            }}
            onMouseLeave={e => {
              if (!active) {
                (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-default)';
                (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)';
              }
            }}
          >
            <span>{cat.icon}</span>
            <span>{cat.label}</span>
            <span
              className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
              style={
                active
                  ? { backgroundColor: 'var(--accent)', color: '#ffffff' }
                  : { backgroundColor: 'var(--bg-elevated)', color: 'var(--text-tertiary)' }
              }
            >
              {count}
            </span>
          </button>
        );
      })}
      {otherCount > 0 && (
        <button
          onClick={() => toggle('other')}
          className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all"
          style={
            selected.has('other')
              ? { borderColor: 'var(--accent)', backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }
              : { borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-secondary)' }
          }
          onMouseEnter={e => {
            if (!selected.has('other')) {
              (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-strong)';
              (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)';
            }
          }}
          onMouseLeave={e => {
            if (!selected.has('other')) {
              (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-default)';
              (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)';
            }
          }}
        >
          <span>📦</span>
          <span>Other</span>
          <span
            className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
            style={
              selected.has('other')
                ? { backgroundColor: 'var(--accent)', color: '#ffffff' }
                : { backgroundColor: 'var(--bg-elevated)', color: 'var(--text-tertiary)' }
            }
          >
            {otherCount}
          </span>
        </button>
      )}
    </div>
  );
}

// ─── Account selector ─────────────────────────────────────────────────────────

function AccountSelector({
  accounts,
  selected,
  onChange,
}: {
  accounts: CloudAccount[];
  selected: Set<string>;
  onChange: (ids: Set<string>) => void;
}) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(next);
  };

  const allSelected = selected.size === 0;
  const label = allSelected
    ? 'All Accounts'
    : selected.size === 1
    ? accounts.find(a => selected.has(a.id))?.name ?? '1 account'
    : `${selected.size} accounts`;

  const byProvider: Record<string, CloudAccount[]> = {};
  for (const acc of accounts) {
    if (!byProvider[acc.provider]) byProvider[acc.provider] = [];
    byProvider[acc.provider].push(acc);
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors"
        style={
          open || !allSelected
            ? { borderColor: 'var(--accent)', backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }
            : { borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }
        }
        onMouseEnter={e => {
          if (!open && allSelected) {
            (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)';
          }
        }}
        onMouseLeave={e => {
          if (!open && allSelected) {
            (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-surface)';
          }
        }}
      >
        <span className="font-medium">{label}</span>
        {!allSelected && (
          <span
            onClick={(e) => { e.stopPropagation(); onChange(new Set()); }}
            className="rounded-full p-0.5 transition-colors"
            onMouseEnter={e => {
              (e.currentTarget as HTMLSpanElement).style.backgroundColor = 'var(--accent)';
              (e.currentTarget as HTMLSpanElement).style.color = '#ffffff';
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLSpanElement).style.backgroundColor = 'transparent';
              (e.currentTarget as HTMLSpanElement).style.color = 'var(--accent)';
            }}
          >
            <X className="h-3 w-3" />
          </span>
        )}
        <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div
          className="absolute left-0 top-full z-50 mt-1.5 w-72 rounded-lg border shadow-xl"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-overlay)' }}
        >
          {/* All accounts option */}
          <div className="border-b p-2" style={{ borderColor: 'var(--border-faint)' }}>
            <button
              onClick={() => { onChange(new Set()); setOpen(false); }}
              className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors"
              style={
                allSelected
                  ? { backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }
                  : { color: 'var(--text-primary)' }
              }
              onMouseEnter={e => {
                if (!allSelected) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)';
              }}
              onMouseLeave={e => {
                if (!allSelected) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
              }}
            >
              <span
                className="flex h-5 w-5 items-center justify-center rounded border text-[10px]"
                style={{ borderColor: 'var(--border-default)' }}
              >
                {allSelected ? '✓' : ''}
              </span>
              <span className="font-medium">All Accounts</span>
              <span className="ml-auto text-xs" style={{ color: 'var(--text-tertiary)' }}>{accounts.length} total</span>
            </button>
          </div>

          {/* Grouped by provider */}
          <div className="max-h-64 overflow-y-auto p-2">
            {Object.entries(byProvider).map(([provider, accs]) => (
              <div key={provider} className="mb-2">
                <div className="mb-1 px-2">
                  <ProviderBadge provider={provider as any} size="sm" />
                </div>
                {accs.map(acc => {
                  const isSelected = selected.has(acc.id);
                  return (
                    <button
                      key={acc.id}
                      onClick={() => toggle(acc.id)}
                      className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors"
                      style={
                        isSelected
                          ? { backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }
                          : { color: 'var(--text-primary)' }
                      }
                      onMouseEnter={e => {
                        if (!isSelected) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)';
                      }}
                      onMouseLeave={e => {
                        if (!isSelected) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
                      }}
                    >
                      <span
                        className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded border text-[10px]"
                        style={
                          isSelected
                            ? { borderColor: 'var(--accent)', backgroundColor: 'var(--accent)', color: '#ffffff' }
                            : { borderColor: 'var(--border-default)' }
                        }
                      >
                        {isSelected ? '✓' : ''}
                      </span>
                      <div className="flex-1 min-w-0 text-left">
                        <div className="truncate font-medium">{acc.name}</div>
                        <div className="truncate text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>{acc.account_id}</div>
                      </div>
                      <span
                        className="flex-shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
                        style={
                          acc.status === 'active'
                            ? { backgroundColor: 'var(--success-dim)', color: 'var(--success)' }
                            : { backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }
                        }
                      >
                        {acc.resource_count}
                      </span>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AssetsPage() {
  const [viewMode, setViewMode] = React.useState<'table' | 'graph'>('table');
  const [searchQuery, setSearchQuery] = React.useState('');
  const [debouncedSearch, setDebouncedSearch] = React.useState('');
  const [selectedAccounts, setSelectedAccounts] = React.useState<Set<string>>(new Set());
  const [selectedCategories, setSelectedCategories] = React.useState<Set<string>>(new Set());
  const [envFilter, setEnvFilter] = React.useState('');
  const [publicFilter, setPublicFilter] = React.useState<boolean | undefined>(undefined);
  const [showCategoryPanel, setShowCategoryPanel] = React.useState(true);
  const [sortField, setSortField] = React.useState<'name' | 'risk' | 'region'>('name');
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('asc');
  const [offset, setOffset] = React.useState(0);

  const [allResources, setAllResources] = React.useState<DiscoveredResource[]>([]);
  const [accounts, setAccounts] = React.useState<CloudAccount[]>([]);
  const [summary, setSummary] = React.useState<ResourceSummary | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Global scope — used when no local account filter is selected
  const globalScopeMode = useScopeStore(s => s.mode);
  const globalAccountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const globalProvider = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
  const globalAccountIds = useScopeStore(s => s.accountIds);

  React.useEffect(() => {
    document.title = 'Assets - CloudVisor';
  }, []);

  React.useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  React.useEffect(() => { setOffset(0); }, [debouncedSearch, selectedAccounts, selectedCategories, envFilter, publicFilter]);
  // Reset when global scope changes
  React.useEffect(() => { setOffset(0); setAllResources([]); }, [globalAccountId, globalProvider]);

  React.useEffect(() => {
    connectorAPI.listAccounts().then(r => setAccounts(r.accounts)).catch(() => {});
    connectorAPI.getResourcesSummary().then(setSummary).catch(() => {});
  }, []);

  const fetchResources = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (selectedAccounts.size === 0) {
        // No local filter — use global scope (account_id or provider from header selector)
        const resp = await connectorAPI.listResources({
          account_id: globalAccountId,
          provider: !globalAccountId ? globalProvider : undefined,
          search: debouncedSearch || undefined,
          environment: envFilter || undefined,
          is_public: publicFilter,
          limit: 500,
          offset: 0,
        });
        setAllResources(resp.resources);
      } else {
        const cloudAccountIds = Array.from(selectedAccounts)
          .map(uuid => accountsRef.current.find(a => a.id === uuid)?.account_id)
          .filter((id): id is string => Boolean(id));

        if (cloudAccountIds.length === 0) {
          const resp = await connectorAPI.listResources({
            search: debouncedSearch || undefined,
            environment: envFilter || undefined,
            is_public: publicFilter,
            limit: 500,
            offset: 0,
          });
          setAllResources(resp.resources);
        } else {
          const results = await Promise.all(
            cloudAccountIds.map(cloudId =>
              connectorAPI.listResources({
                account_id: cloudId,
                search: debouncedSearch || undefined,
                environment: envFilter || undefined,
                is_public: publicFilter,
                limit: 500,
                offset: 0,
              }).catch(() => ({ resources: [] as DiscoveredResource[], total: 0, offset: 0, limit: 500 }))
            )
          );
          setAllResources(results.flatMap(r => r.resources));
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load assets');
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch, selectedAccounts, envFilter, publicFilter, globalAccountId, globalProvider]);

  const accountsRef = React.useRef<CloudAccount[]>([]);
  React.useEffect(() => { accountsRef.current = accounts; }, [accounts]);

  React.useEffect(() => { fetchResources(); }, [fetchResources]);

  React.useEffect(() => {
    if (accounts.length > 0 && selectedAccounts.size > 0) {
      fetchResources();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accounts]);

  const filteredResources = React.useMemo(() => {
    if (selectedCategories.size === 0) return allResources;
    return allResources.filter(r => selectedCategories.has(getCategoryForResource(r.resource_type)));
  }, [allResources, selectedCategories]);

  const categoryCounts = React.useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of allResources) {
      const cat = getCategoryForResource(r.resource_type);
      counts[cat] = (counts[cat] ?? 0) + 1;
    }
    return counts;
  }, [allResources]);

  const sorted = React.useMemo(() => {
    const arr = [...filteredResources];
    arr.sort((a, b) => {
      const mult = sortDir === 'asc' ? 1 : -1;
      if (sortField === 'risk') return (deriveRisk(a) - deriveRisk(b)) * mult;
      if (sortField === 'region') return a.region.localeCompare(b.region) * mult;
      return a.name.localeCompare(b.name) * mult;
    });
    return arr;
  }, [filteredResources, sortField, sortDir]);

  const toggleSort = (field: typeof sortField) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  const paginated = sorted.slice(offset, offset + PAGE_SIZE);
  const total = sorted.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const activeFilters: { label: string; clear: () => void }[] = [];
  if (envFilter) activeFilters.push({ label: `Env: ${envFilter}`, clear: () => setEnvFilter('') });
  if (publicFilter === true) activeFilters.push({ label: 'Public only', clear: () => setPublicFilter(undefined) });
  if (publicFilter === false) activeFilters.push({ label: 'Private only', clear: () => setPublicFilter(undefined) });
  Array.from(selectedCategories).forEach(cat => {
    const cfg = CATEGORIES.find(c => c.id === cat);
    activeFilters.push({
      label: `${cfg?.icon ?? '📦'} ${cfg?.label ?? cat}`,
      clear: () => setSelectedCategories(prev => { const n = new Set(prev); n.delete(cat); return n; }),
    });
  });

  const hasActiveFilters = activeFilters.length > 0 || selectedAccounts.size > 0;

  const scopeAccountIds = useScopeStore(s => s.accountIds);

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Assets' }]}>
        {scopeAccountIds.length === 0 ? (
          <NoAccountsConnectedEmptyState />
        ) : !loading && allResources.length === 0 && !hasActiveFilters && !debouncedSearch ? (
          <NoScanDataEmptyState
            title="No assets found for this account"
            description="No resources have been discovered yet. Run a scan to populate the asset inventory."
          />
        ) : (
        <>
        {/* ── Page Header ──────────────────────────────────────────────────── */}
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Asset inventory</h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {loading
                ? 'Loading…'
                : `${filteredResources.length.toLocaleString()} of ${allResources.length.toLocaleString()} resources`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="flex rounded-md border overflow-hidden"
              style={{ borderColor: 'var(--border-default)' }}
            >
              {(['table', 'graph'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors"
                  style={
                    viewMode === mode
                      ? { backgroundColor: 'var(--accent)', color: '#ffffff' }
                      : { backgroundColor: 'var(--bg-surface)', color: 'var(--text-secondary)' }
                  }
                  onMouseEnter={e => {
                    if (viewMode !== mode) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)';
                  }}
                  onMouseLeave={e => {
                    if (viewMode !== mode) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-surface)';
                  }}
                >
                  {mode === 'table' ? <Table2 className="h-3.5 w-3.5" /> : <LayoutGrid className="h-3.5 w-3.5" />}
                  {mode.charAt(0).toUpperCase() + mode.slice(1)}
                </button>
              ))}
            </div>
            <Button variant="outline" size="sm" className="gap-1.5" onClick={fetchResources} disabled={loading}>
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Refresh
            </Button>
          </div>
        </div>

        {/* ── Row 1: Account selector + search + env/exposure filters ─────── */}
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <AccountSelector accounts={accounts} selected={selectedAccounts} onChange={setSelectedAccounts} />

          <div className="relative flex-1 min-w-[180px] max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: 'var(--text-tertiary)' }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name…"
              className="w-full rounded-md border pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-1"
              style={{
                borderColor: 'var(--border-default)',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-primary)',
              }}
            />
          </div>

          <select
            value={envFilter}
            onChange={(e) => setEnvFilter(e.target.value)}
            className="rounded-md border px-3 py-2 text-sm focus:outline-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
          >
            <option value="">All environments</option>
            <option value="prod">Production</option>
            <option value="staging">Staging</option>
            <option value="dev">Dev</option>
            <option value="unknown">Unknown</option>
          </select>

          <select
            value={publicFilter === undefined ? '' : String(publicFilter)}
            onChange={(e) => setPublicFilter(e.target.value === '' ? undefined : e.target.value === 'true')}
            className="rounded-md border px-3 py-2 text-sm focus:outline-none"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
          >
            <option value="">All exposure</option>
            <option value="true">Public only</option>
            <option value="false">Private only</option>
          </select>

          <button
            onClick={() => setShowCategoryPanel(v => !v)}
            className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm font-medium transition-colors"
            style={
              showCategoryPanel
                ? { borderColor: 'var(--accent)', backgroundColor: 'var(--accent-dim)', color: 'var(--accent)' }
                : { borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-secondary)' }
            }
            onMouseEnter={e => {
              if (!showCategoryPanel) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-elevated)';
            }}
            onMouseLeave={e => {
              if (!showCategoryPanel) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--bg-surface)';
            }}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Categories
            {selectedCategories.size > 0 && (
              <span
                className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold text-white"
                style={{ backgroundColor: 'var(--accent)' }}
              >
                {selectedCategories.size}
              </span>
            )}
          </button>

          <Button variant="outline" size="sm" className="gap-1.5 ml-auto">
            <Download className="h-3.5 w-3.5" />
            Export
          </Button>
        </div>

        {/* ── Row 2: Category pills ─────────────────────────────────────────── */}
        {showCategoryPanel && (
          <div
            className="mb-3 rounded-lg border p-3"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                Filter by category
              </span>
              {selectedCategories.size > 0 && (
                <button
                  onClick={() => setSelectedCategories(new Set())}
                  className="text-xs hover:underline"
                  style={{ color: 'var(--accent)' }}
                >
                  Clear all
                </button>
              )}
            </div>
            <CategoryPanel selected={selectedCategories} counts={categoryCounts} onChange={setSelectedCategories} />
          </div>
        )}

        {/* ── Active filter chips ───────────────────────────────────────────── */}
        {hasActiveFilters && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Active filters:</span>
            {activeFilters.map((f, i) => (
              <FilterChip key={i} label={f.label} onRemove={f.clear} />
            ))}
            <button
              onClick={() => {
                setSelectedAccounts(new Set());
                setSelectedCategories(new Set());
                setEnvFilter('');
                setPublicFilter(undefined);
                setSearchQuery('');
              }}
              className="text-xs transition-colors"
              style={{ color: 'var(--text-tertiary)' }}
              onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.color = 'var(--critical)')}
              onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.color = 'var(--text-tertiary)')}
            >
              Clear all
            </button>
          </div>
        )}

        {/* ── Error ────────────────────────────────────────────────────────── */}
        {error && (
          <div
            className="mb-4 rounded-lg border p-3 text-sm"
            style={{ borderColor: 'var(--critical)', backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }}
          >
            {error}
          </div>
        )}

        {/* ── Table / Graph ─────────────────────────────────────────────────── */}
        {viewMode === 'table' ? (
          <div className="cv-container overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b" style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                      <button onClick={() => toggleSort('name')} className="flex items-center gap-1" style={{ color: 'inherit' }}
                        onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)')}
                        onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)')}
                      >
                        Name <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Category</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Provider</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider hidden lg:table-cell" style={{ color: 'var(--text-secondary)' }}>
                      <button onClick={() => toggleSort('region')} className="flex items-center gap-1" style={{ color: 'inherit' }}
                        onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)')}
                        onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)')}
                      >
                        Region <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider hidden md:table-cell" style={{ color: 'var(--text-secondary)' }}>Env</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider hidden md:table-cell" style={{ color: 'var(--text-secondary)' }}>Exposure</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                      <button onClick={() => toggleSort('risk')} className="flex items-center gap-1" style={{ color: 'inherit' }}
                        onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)')}
                        onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)')}
                      >
                        Risk <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: 'var(--border-faint)' }}>
                  {loading ? (
                    Array.from({ length: 8 }).map((_, i) => (
                      <tr key={i}>
                        {Array.from({ length: 8 }).map((_, j) => (
                          <td key={j} className="px-4 py-3">
                            <div className="h-4 rounded skeleton" style={{ width: `${55 + (i * j) % 40}%` }} />
                          </td>
                        ))}
                      </tr>
                    ))
                  ) : paginated.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-16 text-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
                        {hasActiveFilters || debouncedSearch
                          ? 'No resources match your filters.'
                          : 'No resources discovered yet. Connect a cloud account and run a sync.'}
                      </td>
                    </tr>
                  ) : (
                    paginated.map((asset) => {
                      const catId = getCategoryForResource(asset.resource_type);
                      const cat = CATEGORIES.find(c => c.id === catId);
                      return (
                        <tr
                          key={asset.id}
                          className="transition-colors cursor-pointer"
                          onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                          onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                        >
                          <td className="px-4 py-3">
                            <div className="text-sm font-medium truncate max-w-[180px]" style={{ color: 'var(--text-primary)' }} title={asset.name}>
                              {asset.name}
                            </div>
                            <div className="text-xs font-mono truncate max-w-[180px]" style={{ color: 'var(--text-tertiary)' }} title={asset.cloud_resource_id}>
                              {asset.cloud_resource_id}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center gap-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                              <span>{cat?.icon ?? '📦'}</span>
                              <span className="hidden sm:inline">{cat?.label ?? 'Other'}</span>
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
                            {formatResourceType(asset.resource_type)}
                          </td>
                          <td className="px-4 py-3">
                            <ProviderBadge provider={asset.provider} size="sm" />
                          </td>
                          <td className="px-4 py-3 text-sm hidden lg:table-cell" style={{ color: 'var(--text-tertiary)' }}>
                            {asset.region}
                          </td>
                          <td className="px-4 py-3 hidden md:table-cell">
                            <span
                              className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase"
                              style={ENV_STYLE_MAP[asset.environment] ?? ENV_STYLE_MAP.unknown}
                            >
                              {asset.environment}
                            </span>
                          </td>
                          <td className="px-4 py-3 hidden md:table-cell">
                            {asset.is_public ? (
                              <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--critical)' }}>
                                <Globe className="h-3 w-3" /> Public
                              </span>
                            ) : (
                              <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Private</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <RiskScore score={deriveRisk(asset)} size="sm" />
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {total > PAGE_SIZE && (
              <div
                className="flex items-center justify-between border-t px-4 py-3"
                style={{ borderColor: 'var(--border-faint)' }}
              >
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total.toLocaleString()}
                </p>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" disabled={currentPage === 1} onClick={() => setOffset(o => Math.max(0, o - PAGE_SIZE))} className="h-7 px-2.5 text-xs">
                    <ChevronLeft className="h-3 w-3" />
                  </Button>
                  <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Page {currentPage} of {totalPages}</span>
                  <Button variant="outline" size="sm" disabled={currentPage === totalPages} onClick={() => setOffset(o => o + PAGE_SIZE)} className="h-7 px-2.5 text-xs">
                    <ChevronRight className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="cv-container overflow-hidden" style={{ height: 'calc(100vh - 260px)', minHeight: 520 }}>
            <AssetGraph resources={filteredResources} loading={loading} />
          </div>
        )}
        </>
        )}
      </AppLayout>
    </ProtectedRoute>
  );
}
