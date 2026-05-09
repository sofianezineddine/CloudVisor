'use client';

import * as React from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import {
  useCSPMStats, useCSPMScans, useTriggerScan,
} from '@/hooks/use-cspm';
import { useScopeStore } from '@/stores/scope';
import { NoAccountsConnectedEmptyState } from '@/components/ui/no-accounts-empty-state';
import { NoScanDataEmptyState } from '@/components/ui/no-scan-empty-state';
import { ModuleTabBar } from '@/components/ui/module-tab-bar';

// Import Tabs
import { OverviewTab } from './tabs/overview-tab';
import { FindingsTab } from './tabs/findings-tab';
import { IncidentsTab } from './tabs/incidents-tab';
import { AssetsTab } from './tabs/assets-tab';
import { ComplianceTab } from './tabs/compliance-tab';
import { RiskExplorerTab } from './tabs/risk-explorer-tab';
import { PoliciesTab } from './tabs/policies-tab';
import { ReportsTab } from './tabs/reports-tab';
import { ScanHistoryTab } from './tabs/scan-history-tab';

// ─── Constants ────────────────────────────────────────────────────────────────

const CSPM_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'findings', label: 'Findings' },
  { id: 'incidents', label: 'Incidents' },
  { id: 'assets', label: 'Assets' },
  { id: 'compliance', label: 'Compliance' },
  { id: 'risk-map', label: 'Risk Map' },
  { id: 'policies', label: 'Policies' },
  { id: 'reports', label: 'Reports' },
  { id: 'scan-history', label: 'Scan History' },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

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

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CSPMPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  
  const activeTab = searchParams.get('tab') || 'overview';
  
  const setActiveTab = (tab: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', tab);
    router.push(`${pathname}?${params.toString()}`);
  };

  const { data: stats, isLoading: statsLoading } = useCSPMStats();
  const { data: scansData } = useCSPMScans();
  const triggerScan = useTriggerScan();
  const [flashbarDismissed, setFlashbarDismissed] = React.useState(false);

  React.useEffect(() => {
    document.title = 'CSPM - CloudVisor';
  }, []);

  const scans = Array.isArray(scansData) ? scansData : [];
  const latestScan = scans[0];
  const scanRunning = triggerScan.isPending || latestScan?.status === 'running' || latestScan?.status === 'in_progress';

  React.useEffect(() => {
    if (scanRunning) setFlashbarDismissed(false);
  }, [scanRunning]);

  return (
    <ProtectedRoute>
      <AppLayout
        breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'CSPM' }]}
        cspmActiveTab={activeTab}
        onCspmTabChange={setActiveTab}
      >
        {/* Scan progress Flashbar */}
        {scanRunning && !flashbarDismissed && (
          <div className="mb-4 flex items-center gap-3 px-4 py-3"
            style={{
              backgroundColor: '#e8f4fd',
              border: '1px solid #a8d5f5',
              borderLeft: '4px solid #0073bb',
            }}>
            <span style={{ color: '#0073bb', fontSize: '16px' }}>ⓘ</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold mb-1" style={{ color: '#0073bb' }}>
                Scan in progress — {latestScan?.scan_type?.replace('_', ' ') ?? 'On-demand scan'}
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 overflow-hidden rounded-full" style={{ backgroundColor: '#a8d5f5', maxWidth: '200px' }}>
                  <div className="h-full rounded-full"
                    style={{ width: '60%', backgroundColor: '#0073bb', animation: 'cspm-scan-progress 1.5s ease-in-out infinite alternate' }} />
                </div>
                <span className="text-xs" style={{ color: '#0073bb' }}>Scanning resources…</span>
              </div>
            </div>
            <button onClick={() => setFlashbarDismissed(true)} className="flex-shrink-0 text-sm" style={{ color: '#0073bb' }}>✕</button>
          </div>
        )}
        <style>{`
          @keyframes cspm-scan-progress {
            from { width: 20%; margin-left: 0%; }
            to { width: 40%; margin-left: 60%; }
          }
        `}</style>

        {/* Page header — Only shown on Overview tab */}
        {activeTab === 'overview' && (
          <div className="mb-4">
            <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Cloud Security Posture Management</h1>
            <p className="mt-0.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
              {statsLoading ? 'Loading…' : stats
                ? `${stats.total_resources.toLocaleString()} resources · last scan ${timeAgo(stats.last_scan_at)}`
                : 'Monitor and remediate cloud misconfigurations'}
            </p>
          </div>
        )}

        {/* Tab Content */}
        <div className={activeTab === 'overview' ? 'mt-4' : 'mt-0'}>
          {activeTab === 'overview' && (
            <OverviewTab
              triggerScan={triggerScan}
              scanRunning={scanRunning}
            />
          )}
          {activeTab === 'findings' && <FindingsTab />}
          {activeTab === 'incidents' && <IncidentsTab />}
          {activeTab === 'assets' && <AssetsTab />}
          {activeTab === 'compliance' && <ComplianceTab />}
          {activeTab === 'risk-map' && <RiskExplorerTab />}
          {activeTab === 'policies' && <PoliciesTab />}
          {activeTab === 'reports' && <ReportsTab />}
          {activeTab === 'scan-history' && <ScanHistoryTab />}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
