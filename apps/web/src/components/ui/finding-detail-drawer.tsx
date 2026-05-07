'use client';

import * as React from 'react';
import { DetailDrawer } from './detail-drawer';
import { SeverityBadge } from './severity-badge';
import { StatusBadge } from './status-badge';
import { Button } from './button';
import {
  Clock, Server, Tag, CheckCircle2, AlertTriangle,
  Loader2, ChevronRight, Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import apiClient, { Finding } from '@/lib/api/apiClient';

// ─── Types ────────────────────────────────────────────────────────────────────

interface FindingHistoryEntry {
  from_status: string | null;
  to_status: string;
  changed_by: string;
  changed_at: string;
  note?: string;
}

interface FindingDetail extends Finding {
  history?: FindingHistoryEntry[];
}

// ─── State machine ────────────────────────────────────────────────────────────

const VALID_TRANSITIONS: Record<string, string[]> = {
  open:          ['in_progress', 'resolved', 'suppressed', 'accepted_risk'],
  in_progress:   ['resolved', 'suppressed', 'accepted_risk'],
  resolved:      ['open'],
  suppressed:    ['open'],
  accepted_risk: ['open'],
};

const ACTION_LABELS: Record<string, string> = {
  in_progress:   'Mark In Progress',
  resolved:      'Resolve',
  suppressed:    'Suppress',
  accepted_risk: 'Accept Risk',
  open:          'Reopen',
};

const ACTION_VARIANT: Record<string, 'default' | 'outline' | 'ghost'> = {
  resolved:      'default',
  in_progress:   'outline',
  suppressed:    'outline',
  accepted_risk: 'outline',
  open:          'outline',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(isoDate).toLocaleDateString();
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

function parseRemediationSteps(remediation: string | null): string[] {
  if (!remediation) return [];
  // Try to split on numbered steps like "1. " or "\n1. "
  const numbered = remediation.split(/\n?\d+\.\s+/).filter(Boolean);
  if (numbered.length > 1) return numbered;
  // Fall back to newline split
  return remediation.split('\n').filter(s => s.trim().length > 0);
}

// ─── Section wrapper ──────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
        {title}
      </h3>
      {children}
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface FindingDetailDrawerProps {
  findingId: string | null;
  onClose: () => void;
  onStatusChange?: (id: string, newStatus: string) => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function FindingDetailDrawer({
  findingId,
  onClose,
  onStatusChange,
}: FindingDetailDrawerProps) {
  const [finding, setFinding] = React.useState<FindingDetail | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [actionLoading, setActionLoading] = React.useState<string | null>(null);

  // Fetch finding detail when drawer opens
  React.useEffect(() => {
    if (!findingId) {
      setFinding(null);
      return;
    }
    setLoading(true);
    setError(null);
    apiClient.findings.get(findingId)
      .then(res => setFinding(res?.data as FindingDetail ?? null)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load finding')
      .finally(() => setLoading(false);
  }, [findingId]);

  const handleAction = async (targetStatus: string) => {
    if (!finding) return;
    setActionLoading(targetStatus);
    try {
      await apiClient.findings.update(finding.id, { status: targetStatus });
      // Optimistically update local state
      setFinding(prev => prev ? { ...prev, status: targetStatus as Finding['status'] } : null);
      onStatusChange?.(finding.id, targetStatus);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update finding');
    } finally {
      setActionLoading(null);
    }
  };

  const validActions = finding ? (VALID_TRANSITIONS[finding.status] ?? []) : [];
  const complianceItems = finding?.compliance_mapping ?? [];
  const remediationSteps = parseRemediationSteps(finding?.remediation ?? null);

  return (
    <DetailDrawer
      isOpen={!!findingId}
      onClose={onClose}
      title={finding?.title ?? 'Finding Detail'}
      subtitle={finding ? `${finding.provider?.toUpperCase() ?? ''} · ${finding.resource_type ?? ''}` : undefined}
      width={640}
    >
      {loading && (
        <div className="flex h-48 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--accent)]" />
        </div>
      )}

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-[var(--critical)] bg-[var(--critical-dim)] p-3 text-sm text-[var(--critical)]">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-xs underline">Dismiss</button>
        </div>
      )}

      {finding && !loading && (
        <>
          {/* ── Header badges + age ─────────────────────────────────────── */}
          <div className="mb-5 flex flex-wrap items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <StatusBadge status={finding.status as any} />
            <span className="flex items-center gap-1 text-xs text-[var(--text-tertiary)]">
              <Clock className="h-3 w-3" />
              {timeAgo(finding.first_seen_at)}
            </span>
          </div>

          {/* ── Quick actions ───────────────────────────────────────────── */}
          {validActions.length > 0 && (
            <div className="mb-5 flex flex-wrap gap-2">
              {validActions.map(target => (
                <Button
                  key={target}
                  variant={ACTION_VARIANT[target] ?? 'outline'}
                  size="sm"
                  className="text-xs"
                  disabled={!!actionLoading}
                  onClick={() => handleAction(target)}
                >
                  {actionLoading === target ? (
                    <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                  ) : null}
                  {ACTION_LABELS[target] ?? target}
                </Button>
              )}
            </div>
          )}

          {/* ── Impact statement ────────────────────────────────────────── */}
          {finding.description && (
            <div className="mb-5 rounded-md border-l-4 border-[var(--warning)] bg-[var(--warning-dim)] px-4 py-3">
              <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--warning)]">
                <AlertTriangle className="h-3 w-3" />
                Why this matters
              </div>
              <p className="text-sm text-[var(--text-primary)]">{finding.description}</p>
            </div>
          )}

          {/* ── Resource card ────────────────────────────────────────────── */}
          <Section title="Affected Resource">
            <div className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-elevated)] p-4">
              <div className="mb-3 flex items-center gap-2">
                <Server className="h-4 w-4 text-[var(--text-secondary)]" />
                <span className="font-medium text-[var(--text-primary)]">
                  {finding.resource_name || finding.resource_id}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {[
                  { label: 'Type', value: finding.resource_type },
                  { label: 'Provider', value: finding.provider?.toUpperCase() },
                  { label: 'Account', value: finding.account_id },
                  { label: 'Region', value: finding.region },
                ].filter(r => r.value).map(row => (
                  <div key={row.label}>
                    <span className="text-[var(--text-tertiary)]">{row.label}: </span>
                    <span className="font-mono text-[var(--text-secondary)]">{row.value}</span>
                  </div>
                )}
              </div>
              {finding.tags && Object.keys(finding.tags).length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {Object.entries(finding.tags).slice(0, 6).map(([k, v]) => (
                    <span key={k} className="flex items-center gap-1 rounded-full bg-[var(--bg-surface)] border border-[var(--border-faint)] px-2 py-0.5 text-[10px] text-[var(--text-tertiary)]">
                      <Tag className="h-2.5 w-2.5" />
                      {k}={v}
                    </span>
                  )}
                </div>
              )}
            </div>
          </Section>

          {/* ── Remediation ──────────────────────────────────────────────── */}
          {remediationSteps.length > 0 && (
            <Section title="Remediation Steps">
              <ol className="space-y-2">
                {remediationSteps.map((step, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-[var(--text-primary)]">
                    <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-[var(--accent-dim)] text-[10px] font-bold text-[var(--accent)]">
                      {i + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                )}
              </ol>
            </Section>
          )}

          {/* ── Compliance impact ────────────────────────────────────────── */}
          {complianceItems.length > 0 && (
            <Section title="Compliance Impact">
              <div className="flex flex-wrap gap-2">
                {complianceItems.map((item, i) => {
                  const label = typeof item === 'string'
                    ? item
                    : `${(item as any).framework} ${(item as any).control ?? ''}`.trim();
                  return (
                    <span
                      key={i}
                      className="flex items-center gap-1 rounded-full border border-[var(--border-default)] bg-[var(--bg-elevated)] px-2.5 py-1 text-xs font-medium text-[var(--text-secondary)]"
                    >
                      <Shield className="h-3 w-3 text-[var(--accent)]" />
                      {label}
                    </span>
                  );
                })}
              </div>
            </Section>
          )}

          {/* ── Timeline ─────────────────────────────────────────────────── */}
          <Section title="Timeline">
            <div className="space-y-3">
              {/* Always show first_seen */}
              <div className="flex items-start gap-3">
                <div className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-[var(--success)]" />
                <div>
                  <div className="text-sm text-[var(--text-primary)]">Finding detected</div>
                  <div className="text-xs text-[var(--text-tertiary)]">{formatDate(finding.first_seen_at)}</div>
                </div>
              </div>

              {/* History entries */}
              {(finding.history ?? []).map((entry, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-[var(--accent)]" />
                  <div>
                    <div className="flex items-center gap-1.5 text-sm text-[var(--text-primary)]">
                      <span className="capitalize">{entry.from_status ?? 'open'}</span>
                      <ChevronRight className="h-3 w-3 text-[var(--text-tertiary)]" />
                      <span className="capitalize">{entry.to_status}</span>
                    </div>
                    <div className="text-xs text-[var(--text-tertiary)]">
                      {entry.changed_by} · {formatDate(entry.changed_at)}
                    </div>
                    {entry.note && (
                      <div className="mt-1 text-xs text-[var(--text-secondary)]">{entry.note}</div>
                    )}
                  </div>
                </div>
              )}

              {/* Current status */}
              <div className="flex items-start gap-3">
                <div className={cn(
                  'mt-1 h-2 w-2 flex-shrink-0 rounded-full',
                  finding.status === 'open' ? 'bg-[var(--critical)]' :
                  finding.status === 'resolved' ? 'bg-[var(--success)]' :
                  'bg-[var(--medium)]'
                )} />
                <div>
                  <div className="text-sm text-[var(--text-primary)] capitalize">
                    Currently {finding.status.replace('_', ' ')}
                  </div>
                  <div className="text-xs text-[var(--text-tertiary)]">
                    Last seen {timeAgo(finding.last_seen_at)}
                  </div>
                </div>
              </div>
            </div>
          </Section>
        </>
      )}
    </DetailDrawer>
  );
}
