'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { SeverityBadge } from '@/components/ui/severity-badge';
import { Button } from '@/components/ui/button';
import { ModuleTabBar, ModuleTab } from '@/components/ui/module-tab-bar';
import { Activity, AlertTriangle, Shield, Clock, ArrowRight } from 'lucide-react';

const detections = [
  { id: 1, title: 'Unusual API call from new geographic region', severity: 'CRITICAL', identity: 'deploy-role', time: '2 min ago', mitre: 'Initial Access', status: 'active' },
  { id: 2, title: 'Mass S3 GetObject — possible data exfiltration', severity: 'CRITICAL', identity: 'analytics-role', time: '15 min ago', mitre: 'Exfiltration', status: 'active' },
  { id: 3, title: 'CloudTrail logging disabled unexpectedly', severity: 'HIGH', identity: 'admin-user', time: '1h ago', mitre: 'Defense Evasion', status: 'investigating' },
  { id: 4, title: 'New IAM role with admin policy attached', severity: 'HIGH', identity: 'dev-user', time: '3h ago', mitre: 'Privilege Escalation', status: 'resolved' },
  { id: 5, title: 'EC2 instance communicating with known malicious IP', severity: 'CRITICAL', identity: 'i-0abc123', time: '5h ago', mitre: 'Command & Control', status: 'active' },
];

const activeIncidents = [
  { title: 'Potential data exfiltration via S3', findings: 3, mitre: ['Exfiltration', 'Collection'] },
  { title: 'Compromised IAM identity', findings: 2, mitre: ['Initial Access', 'Privilege Escalation'] },
];

export default function CDRPage() {
  const [liveMode, setLiveMode] = React.useState(true);
  const [activeTab, setActiveTab] = React.useState<ModuleTab>('overview');

  React.useEffect(() => {
    document.title = 'Detection (CDR) - CloudVisor';
  }, []);

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Detection (CDR)' }]}>
        {/* Page Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>CDR — Cloud Detection & Response</h1>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Real-time threat detection and incident response
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setLiveMode(!liveMode)}
              className="flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition-colors"
              style={
                liveMode
                  ? { backgroundColor: 'var(--success-dim)', color: 'var(--success)' }
                  : { backgroundColor: 'var(--bg-surface)', color: 'var(--text-tertiary)' }
              }
            >
              <Activity className="h-3 w-3" />
              {liveMode ? 'Live' : 'Paused'}
            </button>
          </div>
        </div>

        <ModuleTabBar module="cdr" activeTab={activeTab} onTabChange={setActiveTab} />

        {activeTab === 'overview' && (<>
        {/* Active Threat Banner */}
        <div
          className="mb-6 rounded-lg border p-4"
          style={{ borderColor: 'var(--critical-border)', backgroundColor: 'var(--critical-bg)' }}
        >
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5" style={{ color: 'var(--critical)' }} />
            <div>
              <div className="text-sm font-semibold" style={{ color: 'var(--critical)' }}>
                {activeIncidents.length} active threat{activeIncidents.length > 1 ? 's' : ''} detected
              </div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Immediate action recommended
              </div>
            </div>
          </div>
        </div>

        {/* Active Incidents */}
        <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-2">
          {activeIncidents.map((incident, i) => (
            <div key={i} className="cv-container p-5">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4" style={{ color: 'var(--critical)' }} />
                  <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Active Incident</span>
                </div>
                <SeverityBadge severity="CRITICAL" size="sm" />
              </div>
              <h3 className="mb-2 text-base font-medium" style={{ color: 'var(--text-primary)' }}>
                {incident.title}
              </h3>
              <div className="mb-3 flex items-center gap-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                <span>{incident.findings} detections</span>
                <span>·</span>
                <span>{incident.mitre.join(' → ')}</span>
              </div>
              <Button variant="outline" size="sm" className="gap-1.5 text-xs">
                Investigate
                <ArrowRight className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>

        {/* Detection Timeline */}
        <div className="cv-container p-6">
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            Detection feed
          </h3>
          <div className="space-y-4">
            {detections.map((detection) => (
              <div
                key={detection.id}
                className="flex items-start gap-4 rounded-lg border p-4 transition-colors"
                style={
                  detection.status === 'active'
                    ? { borderColor: 'var(--critical-border)', backgroundColor: 'var(--critical-bg)' }
                    : { borderColor: 'var(--border-faint)' }
                }
                onMouseEnter={e => {
                  if (detection.status !== 'active') {
                    (e.currentTarget as HTMLDivElement).style.backgroundColor = 'var(--bg-elevated)';
                  }
                }}
                onMouseLeave={e => {
                  if (detection.status !== 'active') {
                    (e.currentTarget as HTMLDivElement).style.backgroundColor = 'transparent';
                  }
                }}
              >
                <div className="mt-0.5">
                  <SeverityBadge severity={detection.severity as any} />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                    {detection.title}
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {detection.time}
                    </span>
                    <span>Identity: <code className="font-mono" style={{ color: 'var(--text-secondary)' }}>{detection.identity}</code></span>
                    <span>MITRE: {detection.mitre}</span>
                  </div>
                </div>
                <span
                  className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase"
                  style={
                    detection.status === 'active'
                      ? { backgroundColor: 'var(--critical-dim)', color: 'var(--critical)' }
                      : detection.status === 'investigating'
                      ? { backgroundColor: 'var(--medium-dim)', color: 'var(--medium)' }
                      : { backgroundColor: 'var(--success-dim)', color: 'var(--success)' }
                  }
                >
                  {detection.status}
                </span>
              </div>
            ))}
          </div>
        </div>
        </>)}

        {activeTab === 'findings' && (
          <div className="cv-container p-6"><p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Findings filtered to this module coming soon.</p></div>
        )}
        {activeTab === 'policies' && (
          <div className="cv-container p-6"><p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Policy library coming soon.</p></div>
        )}
        {activeTab === 'reports' && (
          <div className="cv-container p-6"><p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Reports coming soon.</p></div>
        )}
      </AppLayout>
    </ProtectedRoute>
  );
}
