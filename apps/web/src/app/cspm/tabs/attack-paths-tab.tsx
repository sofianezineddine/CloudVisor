'use client';

import * as React from 'react';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { Play, Loader2, Network, AlertTriangle } from 'lucide-react';
import { GraphView } from '@/components/cspm/graph-view';
import { SkeletonLoader } from '@/components/cspm/skeleton-loader';
import { ErrorBanner } from '@/components/cspm/error-banner';
import {
  useAttackPaths,
  useAttackPathDetail,
  useBlastRadius,
  useToxicCombinations,
  useTriggerAttackPathAnalysis,
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
  cursor: 'pointer',
};

const tableStyle: React.CSSProperties = {
  borderCollapse: 'collapse',
  width: '100%',
  border: '1px solid var(--border-default)',
};

// ─── Component ────────────────────────────────────────────────────────────────

export function AttackPathsTab() {
  const [selectedPathId, setSelectedPathId] = React.useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = React.useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = React.useState<string | null>(null);
  const [lateralMovementFilter, setLateralMovementFilter] = React.useState<boolean | null>(null);
  const [sortField, setSortField] = React.useState<'severity' | 'path_hops' | 'blast_radius_count'>('severity');
  const [sortDirection, setSortDirection] = React.useState<'desc' | 'asc'>('desc');
  const [page, setPage] = React.useState(1);
  const [expandedToxic, setExpandedToxic] = React.useState<string | null>(null);
  const pageSize = 10;

  const triggerAnalysis = useTriggerAttackPathAnalysis();
  const [runSuccess, setRunSuccess] = React.useState(false);
  const [runError, setRunError] = React.useState<string | null>(null);

  const { data: pathsData, isLoading: pathsLoading, error: pathsError } = useAttackPaths({
    severity: severityFilter ?? undefined,
    is_lateral_movement: lateralMovementFilter ?? undefined,
    page,
    page_size: pageSize,
    sort_by: sortField,
    sort_dir: sortDirection,
  });
  const { data: pathDetail, isLoading: detailLoading } = useAttackPathDetail(selectedPathId);
  const { data: blastRadiusData, isLoading: blastLoading } = useBlastRadius(selectedNodeId);
  const { data: toxicData, isLoading: toxicLoading } = useToxicCombinations();

  const paths = pathsData?.items ?? [];
  const totalPaths = pathsData?.total ?? 0;
  const totalPages = Math.ceil(totalPaths / pageSize);
  const toxicCombinations = toxicData ?? [];

  // Sort helper for severity
  const severityOrder: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };

  const sortedPaths = React.useMemo(() => {
    return [...paths].sort((a, b) => {
      let aVal: number, bVal: number;
      if (sortField === 'severity') {
        aVal = severityOrder[a.severity] ?? 0;
        bVal = severityOrder[b.severity] ?? 0;
      } else {
        aVal = a[sortField] ?? 0;
        bVal = b[sortField] ?? 0;
      }
      return sortDirection === 'desc' ? bVal - aVal : aVal - bVal;
    });
  }, [paths, sortField, sortDirection]);

  const handleSort = (field: 'severity' | 'path_hops' | 'blast_radius_count') => {
    if (sortField === field) {
      setSortDirection(d => d === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Build graph for selected path detail
  const graphNodes = React.useMemo(() => {
    if (!pathDetail?.path_nodes) return [];
    return pathDetail.path_nodes.map((n: any, i: number) => ({
      id: n.id,
      label: n.resource_name || n.id,
      type: i === 0 ? 'entry' as const : i === pathDetail.path_nodes.length - 1 ? 'target' as const : 'intermediate' as const,
      metadata: { resource_type: n.resource_type, is_internet_exposed: n.is_internet_exposed },
    }));
  }, [pathDetail]);

  const graphEdges = React.useMemo(() => {
    if (!pathDetail?.path_edges) return [];
    return pathDetail.path_edges.map((e: any, i: number) => ({
      id: `edge-${i}`,
      source: e.source,
      target: e.target,
      label: e.relationship_type,
      relationship: e.relationship_type,
    }));
  }, [pathDetail]);

  const handleNodeClick = (node: any) => {
    setSelectedNodeId(node.id);
  };

  return (
    <div className="space-y-6">
      {pathsError && <ErrorBanner message="Failed to load attack paths data" />}
      {runError && <ErrorBanner message={runError} />}
      {runSuccess && (
        <div className="flex items-center gap-2 rounded border p-3 text-sm"
          style={{ borderColor: 'var(--success)', backgroundColor: 'var(--success-bg, rgba(34,197,94,0.08))', color: 'var(--success)' }}>
          ✓ Attack path analysis started — results will appear below once complete.
          <button onClick={() => setRunSuccess(false)} className="ml-auto text-xs" style={{ color: 'var(--success)' }}>✕</button>
        </div>
      )}

      {/* Run Attack Path Analysis button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <select
            value={severityFilter ?? ''}
            onChange={e => { setSeverityFilter(e.target.value || null); setPage(1); }}
            className="rounded border px-2 py-1 text-xs"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
          <select
            value={lateralMovementFilter === null ? '' : lateralMovementFilter ? 'true' : 'false'}
            onChange={e => { setLateralMovementFilter(e.target.value === '' ? null : e.target.value === 'true'); setPage(1); }}
            className="rounded border px-2 py-1 text-xs"
            style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
          >
            <option value="">All Paths</option>
            <option value="true">Lateral Movement</option>
            <option value="false">No Lateral Movement</option>
          </select>
        </div>
        <Button
          onClick={() => {
            setRunSuccess(false);
            setRunError(null);
            triggerAnalysis.mutate(undefined, {
              onSuccess: () => setRunSuccess(true),
              onError: (e: unknown) => setRunError(e instanceof Error ? e.message : 'Attack path analysis failed to start'),
            });
          }}
          disabled={triggerAnalysis.isPending}
          className="gap-2"
        >
          {triggerAnalysis.isPending
            ? <Loader2 className="h-4 w-4 animate-spin" />
            : <Play className="h-4 w-4" />}
          {triggerAnalysis.isPending ? 'Analyzing…' : 'Run Attack Path Analysis'}
        </Button>
      </div>

      {/* Path List Table */}
      <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Attack Paths</h3>
        {pathsLoading ? (
          <SkeletonLoader variant="table" rows={5} columns={7} />
        ) : sortedPaths.length === 0 ? (
          <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
            No attack paths found
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={headerCellStyle} onClick={() => handleSort('severity')}>
                      Severity {sortField === 'severity' ? (sortDirection === 'desc' ? '↓' : '↑') : ''}
                    </th>
                    <th style={{ ...headerCellStyle, cursor: 'default' }}>Entry Resource</th>
                    <th style={{ ...headerCellStyle, cursor: 'default' }}>Target Resource</th>
                    <th style={headerCellStyle} onClick={() => handleSort('path_hops')}>
                      Hops {sortField === 'path_hops' ? (sortDirection === 'desc' ? '↓' : '↑') : ''}
                    </th>
                    <th style={{ ...headerCellStyle, cursor: 'default' }}>MITRE Technique</th>
                    <th style={{ ...headerCellStyle, cursor: 'default' }}>Lateral Movement</th>
                    <th style={headerCellStyle} onClick={() => handleSort('blast_radius_count')}>
                      Blast Radius {sortField === 'blast_radius_count' ? (sortDirection === 'desc' ? '↓' : '↑') : ''}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedPaths.map(path => (
                    <tr key={path.id}
                      style={{ backgroundColor: selectedPathId === path.id ? 'var(--bg-elevated)' : 'transparent', cursor: 'pointer' }}
                      onClick={() => setSelectedPathId(selectedPathId === path.id ? null : path.id)}
                      onMouseEnter={e => { if (selectedPathId !== path.id) e.currentTarget.style.backgroundColor = 'var(--bg-elevated)'; }}
                      onMouseLeave={e => { if (selectedPathId !== path.id) e.currentTarget.style.backgroundColor = 'transparent'; }}>
                      <td style={cellStyle}><SeverityBadge severity={path.severity} size="sm" /></td>
                      <td style={{ ...cellStyle, maxWidth: '160px' }}>
                        <div className="truncate text-xs">{path.entry_resource_name || path.entry_resource_id}</div>
                      </td>
                      <td style={{ ...cellStyle, maxWidth: '160px' }}>
                        <div className="truncate text-xs">{path.target_resource_name || path.target_resource_id}</div>
                      </td>
                      <td style={cellStyle}><span className="text-xs font-mono">{path.path_hops}</span></td>
                      <td style={cellStyle}>
                        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                          {path.mitre_technique_name || path.mitre_technique_id || '—'}
                        </span>
                      </td>
                      <td style={cellStyle}>
                        {path.is_lateral_movement ? (
                          <span className="text-xs font-semibold" style={{ color: 'var(--warning)' }}>⚠ Yes</span>
                        ) : (
                          <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>No</span>
                        )}
                      </td>
                      <td style={cellStyle}>
                        <span className="font-mono text-xs font-semibold" style={{ color: path.blast_radius_count > 10 ? 'var(--critical)' : 'var(--text-primary)' }}>
                          {path.blast_radius_count}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  Page {page} of {totalPages} ({totalPaths} total)
                </span>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>
                    Previous
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Path Detail Panel */}
      {selectedPathId && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            Path Detail
          </h3>
          {detailLoading ? (
            <SkeletonLoader variant="graph" />
          ) : graphNodes.length > 0 ? (
            <GraphView
              nodes={graphNodes}
              edges={graphEdges}
              direction="LR"
              height="350px"
              onNodeClick={handleNodeClick}
            />
          ) : (
            <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No path detail available
            </div>
          )}
        </div>
      )}

      {/* Blast Radius Panel */}
      {selectedNodeId && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
              Blast Radius — {selectedNodeId}
            </h3>
            <button onClick={() => setSelectedNodeId(null)} className="text-xs" style={{ color: 'var(--text-tertiary)' }}>✕ Close</button>
          </div>
          {blastLoading ? (
            <SkeletonLoader variant="table" rows={3} columns={3} />
          ) : blastRadiusData ? (
            <>
              <div className="mb-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
                <span className="font-mono font-semibold" style={{ color: 'var(--critical)' }}>{blastRadiusData.reachable_count}</span> reachable resources
              </div>
              {blastRadiusData.reachable_resources?.length > 0 && (
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={headerCellStyle}>Resource ID</th>
                      <th style={headerCellStyle}>Name</th>
                      <th style={headerCellStyle}>Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {blastRadiusData.reachable_resources.map((r: any) => (
                      <tr key={r.resource_id}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                        <td style={cellStyle}><span className="text-xs font-mono">{r.resource_id}</span></td>
                        <td style={cellStyle}><span className="text-xs">{r.resource_name}</span></td>
                        <td style={cellStyle}><span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.resource_type}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          ) : (
            <div className="text-sm" style={{ color: 'var(--text-tertiary)' }}>No blast radius data</div>
          )}
        </div>
      )}

      {/* Toxic Combinations */}
      <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
        <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Toxic Combinations</h3>
        {toxicLoading ? (
          <SkeletonLoader variant="table" rows={3} columns={4} />
        ) : toxicCombinations.length === 0 ? (
          <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
            No toxic combinations detected
          </div>
        ) : (
          <div className="space-y-2">
            {toxicCombinations.map(tc => (
              <div key={tc.id} className="rounded border p-3" style={{ borderColor: 'var(--border-default)' }}>
                <div className="flex items-center justify-between cursor-pointer"
                  onClick={() => setExpandedToxic(expandedToxic === tc.id ? null : tc.id)}>
                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={tc.elevated_severity} size="sm" />
                    <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{tc.description}</span>
                  </div>
                  <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    {expandedToxic === tc.id ? '▼' : '▶'} {tc.component_details?.length ?? 0} components
                  </span>
                </div>
                {expandedToxic === tc.id && tc.component_details && (
                  <div className="mt-3 pl-4 space-y-1" style={{ borderLeft: '2px solid var(--border-default)' }}>
                    {tc.component_details.map((cd: any, i: number) => (
                      <div key={i} className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                        <SeverityBadge severity={cd.severity} size="sm" />
                        <span>{cd.rule_id}: {cd.description}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
