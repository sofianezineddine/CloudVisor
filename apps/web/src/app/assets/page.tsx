'use client';

import * as React from 'react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Filter, Globe, Server, Database, Shield, Cloud, RefreshCw, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import ProviderBadge from '@/components/ui/provider-badge';
import { cn } from '@/lib/utils';
import { graphAPI, GraphAsset } from '@/lib/api/graph';
import { connectorAPI } from '@/lib/api/connector';
import { useResourceTypeCatalog } from '@/hooks/use-connector';
import { useScopeStore } from '@/stores/scope';
import { useAuth } from '@/hooks/use-auth';

// ─── Asset Explorer Page (UI Spec Page 3) ────────────────────────────────────

export default function AssetsPage() {
  const [search, setSearch] = useState('');
  const [provider, setProvider] = useState<string | undefined>();
  const [resourceType, setResourceType] = useState<string | undefined>();
  const [cursor, setCursor] = useState<string | undefined>();
  const [cursorHistory, setCursorHistory] = useState<(string | undefined)[]>([undefined]);
  const [page, setPage] = useState(1);
  const limit = 50;

  const scopeAccountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const scopeProvider = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
  const { user } = useAuth();
  const orgId = user?.organization_id;

  const effectiveProvider = provider || (!scopeAccountId ? scopeProvider : undefined);

  // Fetch assets from graph service
  const { data: assetsData, isLoading, refetch } = useQuery({
    queryKey: ['graph', 'assets', orgId, effectiveProvider, resourceType, search, cursor],
    queryFn: async () => {
      if (search.length > 0) {
        const result = await graphAPI.searchAssets({
          q: search,
          org_id: orgId,
          provider: effectiveProvider,
          limit,
        });
        return { assets: result.hits, total: result.total, next_cursor: undefined };
      }
      const result = await graphAPI.listAssets({
        org_id: orgId,
        provider: effectiveProvider,
        resource_type: resourceType,
        limit,
        cursor,
      });
      return { assets: result.assets, total: result.total, next_cursor: (result as any).next_cursor };
    },
    staleTime: 30_000,
  });

  // Fetch summary stats
  const { data: stats } = useQuery({
    queryKey: ['graph', 'stats', orgId],
    queryFn: () => graphAPI.getStats(orgId),
    staleTime: 60_000,
  });

  // Resource type catalog for filter dropdown
  const { data: catalog } = useResourceTypeCatalog();

  const assets = assetsData?.assets ?? [];
  const total = assetsData?.total ?? 0;
  const nextCursor = assetsData?.next_cursor;
  const hasPrev = page > 1;
  const hasNext = !!nextCursor;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-[var(--text-primary)]">Asset Inventory</h1>
          <p className="text-body text-[var(--text-secondary)]">
            {total.toLocaleString()} resources across {Object.keys(stats?.by_provider ?? {}).length} providers
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Provider summary cards */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          {Object.entries(stats.by_provider).map(([prov, count]) => (
            <button
              key={prov}
              onClick={() => setProvider(provider === prov ? undefined : prov)}
              className={cn(
                "p-4 rounded-2xl border transition-colors text-left",
                provider === prov
                  ? "border-[var(--accent)] bg-[var(--accent-dim)]"
                  : "border-[var(--border-default)] bg-[var(--bg-surface)] hover:bg-[var(--bg-elevated)]"
              )}
            >
              <ProviderBadge provider={prov as any} size="sm" />
              <p className="text-h3 font-mono mt-2">{count.toLocaleString()}</p>
              <p className="text-small text-[var(--text-secondary)]">resources</p>
            </button>
          ))}
        </div>
      )}

      {/* Search + filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-tertiary)]" />
          <Input
            placeholder="Search by name, ID, or tags..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setCursor(undefined); setCursorHistory([undefined]); setPage(1); }}
            className="pl-10"
          />
        </div>
        {catalog && (
          <select
            value={resourceType ?? ''}
            onChange={(e) => { setResourceType(e.target.value || undefined); setCursor(undefined); setCursorHistory([undefined]); setPage(1); }}
            className="h-8 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 text-sm"
          >
            <option value="">All types</option>
            {Object.entries(catalog.providers).map(([prov, data]) =>
              data.resource_types.map(rt => (
                <option key={`${prov}-${rt.service_key}`} value={rt.resource_type}>
                  {prov.toUpperCase()}: {rt.resource_type}
                </option>
              ))
            )}
          </select>
        )}
      </div>

      {/* Assets table */}
      <div className="border border-[var(--border-default)] rounded-2xl bg-[var(--bg-surface)] overflow-hidden">
        <div className="px-5 py-3 border-b border-[var(--border-faint)] flex items-center justify-between">
          <span className="text-h5">Resources ({total.toLocaleString()})</span>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-[var(--text-secondary)]">Loading assets...</div>
        ) : assets.length === 0 ? (
          <div className="p-8 text-center">
            <Cloud className="w-8 h-8 mx-auto text-[var(--text-tertiary)] mb-2" />
            <p className="text-h4 text-[var(--text-primary)]">No assets found</p>
            <p className="text-small text-[var(--text-secondary)]">
              {search ? 'Try a different search term' : 'Connect a cloud account to discover resources'}
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-faint)] text-left">
                <th className="px-5 py-2 text-small font-semibold text-[var(--text-secondary)]">Name</th>
                <th className="px-5 py-2 text-small font-semibold text-[var(--text-secondary)]">Type</th>
                <th className="px-5 py-2 text-small font-semibold text-[var(--text-secondary)]">Provider</th>
                <th className="px-5 py-2 text-small font-semibold text-[var(--text-secondary)]">Region</th>
                <th className="px-5 py-2 text-small font-semibold text-[var(--text-secondary)]">Risk</th>
                <th className="px-5 py-2 text-small font-semibold text-[var(--text-secondary)]">Findings</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset: GraphAsset) => (
                <tr
                  key={asset.id}
                  className="border-b border-[var(--border-faint)] hover:bg-[var(--bg-elevated)] cursor-pointer transition-colors"
                >
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      {asset.is_public && <Globe className="w-3.5 h-3.5 text-[var(--warning)]" />}
                      <span className="text-body font-medium truncate max-w-[240px]">{asset.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <span className="text-small font-mono text-[var(--text-secondary)]">
                      {asset.resource_type.split('::').pop()}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <ProviderBadge provider={asset.provider as any} size="xs" />
                  </td>
                  <td className="px-5 py-3 text-small text-[var(--text-secondary)]">{asset.region}</td>
                  <td className="px-5 py-3">
                    <span className={cn(
                      "inline-flex items-center px-2 py-0.5 rounded text-xsmall font-mono font-semibold",
                      asset.risk_score >= 80 ? "bg-[var(--critical-bg)] text-[var(--critical)]" :
                      asset.risk_score >= 50 ? "bg-[var(--high-bg)] text-[var(--high)]" :
                      asset.risk_score >= 20 ? "bg-[var(--medium-bg)] text-[var(--medium)]" :
                      "bg-[var(--low-bg)] text-[var(--low)]"
                    )}>
                      {asset.risk_score}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-small font-mono">
                    {asset.open_findings_count > 0 ? (
                      <span className="text-[var(--critical)]">{asset.open_findings_count}</span>
                    ) : (
                      <span className="text-[var(--text-tertiary)]">0</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {(hasPrev || hasNext) && (
          <div className="px-5 py-3 border-t border-[var(--border-faint)] flex items-center justify-between">
            <span className="text-small text-[var(--text-secondary)]">
              Page {page} · {total.toLocaleString()} total resources
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!hasPrev}
                onClick={() => {
                  const prev = cursorHistory[page - 2];
                  setCursor(prev);
                  setPage(p => p - 1);
                }}
              >
                Previous
              </Button>
              <span className="text-small text-[var(--text-secondary)]">
                {page}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={!hasNext}
                onClick={() => {
                  if (nextCursor) {
                    setCursorHistory(h => [...h, nextCursor]);
                    setCursor(nextCursor);
                    setPage(p => p + 1);
                  }
                }}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
