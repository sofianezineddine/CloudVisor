'use client';

import * as React from 'react';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { Loader2, GitBranch, Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { SkeletonLoader } from '@/components/cspm/skeleton-loader';
import { ErrorBanner } from '@/components/cspm/error-banner';
import {
  useDriftEvents,
  useDriftBaselines,
  useSetDriftBaseline,
  useAnomalyFindings,
  useCorrelatedAlerts,
  useUpdateAlertStatus,
  useCorrelationRules,
  useCreateCorrelationRule,
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

export function DriftDetectionTab() {
  const [activeSection, setActiveSection] = React.useState<'events' | 'baselines' | 'anomalies' | 'alerts' | 'rules'>('events');
  const [eventsPage, setEventsPage] = React.useState(1);
  const [securityRelevanceFilter, setSecurityRelevanceFilter] = React.useState<boolean | null>(null);
  const [alertStatusFilter, setAlertStatusFilter] = React.useState<string | null>(null);
  const [expandedBaseline, setExpandedBaseline] = React.useState<string | null>(null);
  const [expandedAnomaly, setExpandedAnomaly] = React.useState<string | null>(null);
  const [baselineResourceId, setBaselineResourceId] = React.useState('');

  // Correlation rule form
  const [ruleName, setRuleName] = React.useState('');
  const [ruleGroupBy, setRuleGroupBy] = React.useState('');
  const [ruleEventTypes, setRuleEventTypes] = React.useState('');
  const [ruleTimeWindow, setRuleTimeWindow] = React.useState('300');
  const [ruleMinEvents, setRuleMinEvents] = React.useState('3');

  const { data: eventsData, isLoading: eventsLoading, error: eventsError } = useDriftEvents({
    is_security_relevant: securityRelevanceFilter ?? undefined,
    page: eventsPage,
    page_size: 10,
  });
  const { data: baselinesData, isLoading: baselinesLoading } = useDriftBaselines({});
  const setBaseline = useSetDriftBaseline();
  const { data: anomaliesData, isLoading: anomaliesLoading } = useAnomalyFindings({});
  const { data: alertsData, isLoading: alertsLoading } = useCorrelatedAlerts({
    status: alertStatusFilter ?? undefined,
  });
  const updateAlertStatus = useUpdateAlertStatus();
  const { data: rulesData, isLoading: rulesLoading } = useCorrelationRules();
  const createRule = useCreateCorrelationRule();

  const events = eventsData?.items ?? [];
  const eventsTotal = eventsData?.total ?? 0;
  const eventsTotalPages = Math.ceil(eventsTotal / 10);
  const baselines = baselinesData?.items ?? [];
  const anomalies = anomaliesData?.items ?? [];
  const alerts = alertsData?.items ?? [];
  const rules = rulesData ?? [];

  const handleSetBaseline = () => {
    if (!baselineResourceId.trim()) return;
    setBaseline.mutate({ resource_id: baselineResourceId }, {
      onSuccess: () => setBaselineResourceId(''),
    });
  };

  const handleCreateRule = () => {
    if (!ruleName.trim()) return;
    createRule.mutate({
      name: ruleName,
      group_by: ruleGroupBy.split(',').map(s => s.trim()).filter(Boolean),
      event_types: ruleEventTypes.split(',').map(s => s.trim()).filter(Boolean),
      time_window_seconds: parseInt(ruleTimeWindow) || 300,
      min_events: parseInt(ruleMinEvents) || 3,
    }, {
      onSuccess: () => {
        setRuleName('');
        setRuleGroupBy('');
        setRuleEventTypes('');
        setRuleTimeWindow('300');
        setRuleMinEvents('3');
      },
    });
  };

  // Z-score color scale
  const zScoreColor = (score: number): string => {
    if (score >= 3) return 'var(--critical)';
    if (score >= 2) return 'var(--high)';
    if (score >= 1.5) return 'var(--warning)';
    return 'var(--text-primary)';
  };

  return (
    <div className="space-y-6">
      {eventsError && <ErrorBanner message="Failed to load drift detection data" />}

      {/* Section Navigation */}
      <div className="flex gap-1" style={{ borderBottom: '1px solid var(--border-default)' }}>
        {(['events', 'baselines', 'anomalies', 'alerts', 'rules'] as const).map(section => (
          <button key={section} style={sectionBtnStyle(activeSection === section)} onClick={() => setActiveSection(section)}>
            {section === 'events' ? 'Drift Events' : section === 'baselines' ? 'Baselines' : section === 'anomalies' ? 'Anomalies' : section === 'alerts' ? 'Alerts' : 'Rules'}
          </button>
        ))}
      </div>

      {/* Drift Events Timeline */}
      {activeSection === 'events' && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Drift Events Timeline</h3>
            <select
              value={securityRelevanceFilter === null ? '' : securityRelevanceFilter ? 'true' : 'false'}
              onChange={e => { setSecurityRelevanceFilter(e.target.value === '' ? null : e.target.value === 'true'); setEventsPage(1); }}
              className="rounded border px-2 py-1 text-xs"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            >
              <option value="">All Events</option>
              <option value="true">Security Relevant</option>
              <option value="false">Non-Security</option>
            </select>
          </div>
          {eventsLoading ? (
            <SkeletonLoader variant="timeline" rows={5} />
          ) : events.length === 0 ? (
            <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No drift events detected
            </div>
          ) : (
            <>
              <div className="space-y-3" style={{ borderLeft: '2px solid var(--border-default)', paddingLeft: '16px' }}>
                {events.map((event: any) => (
                  <div key={event.id} className="relative pl-4 py-2 rounded" style={{ borderBottom: '1px solid var(--border-faint)' }}>
                    {/* Timeline indicator */}
                    <div
                      className="absolute -left-[22px] top-3 h-3 w-3 rounded-full"
                      style={{ backgroundColor: event.is_security_relevant ? 'var(--critical)' : 'var(--text-tertiary)' }}
                    />
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <SeverityBadge severity={event.severity} size="sm" />
                        <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                          {event.resource_id}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {event.is_security_relevant && (
                          <span className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--critical-bg, rgba(239,68,68,0.1))', color: 'var(--critical)' }}>
                            Security
                          </span>
                        )}
                        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                          <Clock className="inline h-3 w-3 mr-1" />
                          {event.detected_at ? new Date(event.detected_at).toLocaleString() : '—'}
                        </span>
                      </div>
                    </div>
                    <div className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                      <span className="font-medium">{event.field_name}</span>: {JSON.stringify(event.baseline_value)} → {JSON.stringify(event.current_value)}
                    </div>
                  </div>
                ))}
              </div>
              {eventsTotalPages > 1 && (
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Page {eventsPage} of {eventsTotalPages}</span>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setEventsPage(p => Math.max(1, p - 1))} disabled={eventsPage <= 1}>Previous</Button>
                    <Button variant="outline" size="sm" onClick={() => setEventsPage(p => Math.min(eventsTotalPages, p + 1))} disabled={eventsPage >= eventsTotalPages}>Next</Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Baselines Section */}
      {activeSection === 'baselines' && (
        <div className="space-y-4">
          <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Set Baseline</h3>
            <div className="flex items-center gap-3">
              <input
                value={baselineResourceId}
                onChange={e => setBaselineResourceId(e.target.value)}
                placeholder="Resource ID"
                className="flex-1 rounded border px-2 py-1 text-xs"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
              />
              <Button onClick={handleSetBaseline} disabled={setBaseline.isPending || !baselineResourceId.trim()} size="sm" className="gap-2">
                {setBaseline.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                Set Baseline
              </Button>
            </div>
          </div>

          <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Baselines</h3>
            {baselinesLoading ? (
              <SkeletonLoader variant="table" rows={3} columns={4} />
            ) : baselines.length === 0 ? (
              <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
                No baselines configured
              </div>
            ) : (
              <div className="space-y-2">
                {baselines.map((bl: any) => (
                  <div key={bl.id} className="rounded border p-3" style={{ borderColor: 'var(--border-default)' }}>
                    <div className="flex items-center justify-between cursor-pointer"
                      onClick={() => setExpandedBaseline(expandedBaseline === bl.id ? null : bl.id)}>
                      <div>
                        <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>{bl.resource_id}</span>
                        <span className="ml-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>{bl.resource_type}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                          {bl.updated_at ? new Date(bl.updated_at).toLocaleDateString() : '—'}
                        </span>
                        <span className="text-xs">{expandedBaseline === bl.id ? '▼' : '▶'}</span>
                      </div>
                    </div>
                    {expandedBaseline === bl.id && bl.baseline_config && (
                      <pre className="mt-3 p-3 rounded text-xs overflow-auto" style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)', maxHeight: '200px' }}>
                        {JSON.stringify(bl.baseline_config, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Anomalies Section */}
      {activeSection === 'anomalies' && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Anomaly Findings</h3>
          {anomaliesLoading ? (
            <SkeletonLoader variant="table" rows={5} columns={5} />
          ) : anomalies.length === 0 ? (
            <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No anomalies detected
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={headerCellStyle}>Resource</th>
                    <th style={headerCellStyle}>Type</th>
                    <th style={headerCellStyle}>Anomaly Score</th>
                    <th style={headerCellStyle}>Severity</th>
                    <th style={headerCellStyle}>Detected</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.map((anomaly: any) => (
                    <React.Fragment key={anomaly.id}>
                      <tr
                        style={{ cursor: 'pointer' }}
                        onClick={() => setExpandedAnomaly(expandedAnomaly === anomaly.id ? null : anomaly.id)}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                        <td style={{ ...cellStyle, maxWidth: '180px' }}>
                          <div className="truncate text-xs">{anomaly.resource_id}</div>
                        </td>
                        <td style={cellStyle}><span className="text-xs">{anomaly.resource_type}</span></td>
                        <td style={cellStyle}>
                          <span className="font-mono text-xs font-semibold" style={{ color: zScoreColor(anomaly.anomaly_score) }}>
                            {anomaly.anomaly_score?.toFixed(2)}
                          </span>
                        </td>
                        <td style={cellStyle}><SeverityBadge severity={anomaly.severity} size="sm" /></td>
                        <td style={cellStyle}>
                          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                            {anomaly.detected_at ? new Date(anomaly.detected_at).toLocaleDateString() : '—'}
                          </span>
                        </td>
                      </tr>
                      {expandedAnomaly === anomaly.id && anomaly.deviating_fields?.length > 0 && (
                        <tr>
                          <td colSpan={5} style={{ ...cellStyle, backgroundColor: 'var(--bg-elevated)', padding: '12px 16px' }}>
                            <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>Deviating Fields:</div>
                            <div className="space-y-1">
                              {anomaly.deviating_fields.map((df: any, i: number) => (
                                <div key={i} className="flex items-center gap-3 text-xs">
                                  <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{df.field}:</span>
                                  <span className="font-mono" style={{ color: zScoreColor(Math.abs((df.value - (df.expected_min + df.expected_max) / 2) / ((df.expected_max - df.expected_min) / 2 || 1))) }}>
                                    {df.value}
                                  </span>
                                  <span style={{ color: 'var(--text-tertiary)' }}>
                                    (expected: {df.expected_min} – {df.expected_max})
                                  </span>
                                </div>
                              ))}
                            </div>
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

      {/* Correlated Alerts Section */}
      {activeSection === 'alerts' && (
        <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Correlated Alerts</h3>
            <select
              value={alertStatusFilter ?? ''}
              onChange={e => setAlertStatusFilter(e.target.value || null)}
              className="rounded border px-2 py-1 text-xs"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
          {alertsLoading ? (
            <SkeletonLoader variant="table" rows={4} columns={5} />
          ) : alerts.length === 0 ? (
            <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
              No correlated alerts
            </div>
          ) : (
            <div className="space-y-2">
              {alerts.map((alert: any) => (
                <div key={alert.id} className="rounded border p-3" style={{ borderColor: 'var(--border-default)' }}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <SeverityBadge severity={alert.combined_severity} size="sm" />
                      <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                        {alert.correlation_rule_name}
                      </span>
                      <span className="text-xs px-1.5 py-0.5 rounded" style={{
                        backgroundColor: alert.status === 'open' ? 'var(--critical-bg, rgba(239,68,68,0.1))' : alert.status === 'acknowledged' ? 'rgba(234,179,8,0.1)' : 'rgba(34,197,94,0.1)',
                        color: alert.status === 'open' ? 'var(--critical)' : alert.status === 'acknowledged' ? 'var(--warning)' : 'var(--success)',
                      }}>
                        {alert.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {alert.status === 'open' && (
                        <Button variant="outline" size="sm"
                          onClick={() => updateAlertStatus.mutate({ id: alert.id, status: 'acknowledged' })}
                          disabled={updateAlertStatus.isPending}>
                          Acknowledge
                        </Button>
                      )}
                      {(alert.status === 'open' || alert.status === 'acknowledged') && (
                        <Button variant="outline" size="sm"
                          onClick={() => updateAlertStatus.mutate({ id: alert.id, status: 'resolved' })}
                          disabled={updateAlertStatus.isPending}>
                          Resolve
                        </Button>
                      )}
                    </div>
                  </div>
                  <div className="mt-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    {alert.contributing_event_ids?.length ?? 0} contributing events · {alert.created_at ? new Date(alert.created_at).toLocaleString() : '—'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Correlation Rules Section */}
      {activeSection === 'rules' && (
        <div className="space-y-4">
          <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Correlation Rules</h3>
            {rulesLoading ? (
              <SkeletonLoader variant="table" rows={3} columns={5} />
            ) : rules.length === 0 ? (
              <div className="flex h-16 items-center justify-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
                No correlation rules configured
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={headerCellStyle}>Name</th>
                      <th style={headerCellStyle}>Event Types</th>
                      <th style={headerCellStyle}>Time Window</th>
                      <th style={headerCellStyle}>Min Events</th>
                      <th style={headerCellStyle}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rules.map((rule: any) => (
                      <tr key={rule.id}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                        <td style={cellStyle}><span className="text-xs font-medium">{rule.name}</span></td>
                        <td style={{ ...cellStyle, maxWidth: '200px' }}>
                          <div className="truncate text-xs" style={{ color: 'var(--text-secondary)' }}>
                            {rule.event_types?.join(', ') ?? '—'}
                          </div>
                        </td>
                        <td style={cellStyle}><span className="text-xs font-mono">{rule.time_window_seconds}s</span></td>
                        <td style={cellStyle}><span className="text-xs font-mono">{rule.min_events}</span></td>
                        <td style={cellStyle}>
                          {rule.is_active ? (
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

          {/* Create Rule Form */}
          <div className="p-5 rounded-[var(--radius-container)] border border-[var(--border-default)] bg-[var(--bg-surface)]">
            <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Create Correlation Rule</h3>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Rule Name</label>
                <input value={ruleName} onChange={e => setRuleName(e.target.value)}
                  placeholder="e.g. Multi-drift correlation"
                  className="w-full rounded border px-2 py-1 text-xs"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
              </div>
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Group By (comma-separated)</label>
                <input value={ruleGroupBy} onChange={e => setRuleGroupBy(e.target.value)}
                  placeholder="resource_id, account_id"
                  className="w-full rounded border px-2 py-1 text-xs"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
              </div>
              <div>
                <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Event Types (comma-separated)</label>
                <input value={ruleEventTypes} onChange={e => setRuleEventTypes(e.target.value)}
                  placeholder="drift, anomaly"
                  className="w-full rounded border px-2 py-1 text-xs"
                  style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Time Window (s)</label>
                  <input value={ruleTimeWindow} onChange={e => setRuleTimeWindow(e.target.value)} type="number"
                    className="w-full rounded border px-2 py-1 text-xs"
                    style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
                </div>
                <div className="flex-1">
                  <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Min Events</label>
                  <input value={ruleMinEvents} onChange={e => setRuleMinEvents(e.target.value)} type="number"
                    className="w-full rounded border px-2 py-1 text-xs"
                    style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }} />
                </div>
              </div>
            </div>
            <div className="mt-3">
              <Button onClick={handleCreateRule} disabled={createRule.isPending || !ruleName.trim()} size="sm" className="gap-2">
                {createRule.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                Create Rule
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
