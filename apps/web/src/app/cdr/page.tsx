'use client';

import * as React from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';

// Import Tabs
import { OverviewTab } from './tabs/overview-tab';
import { FindingsTab } from './tabs/findings-tab';
import { AssetsTab } from './tabs/assets-tab';
import { PoliciesTab } from './tabs/policies-tab';
import { ReportsTab } from './tabs/reports-tab';

export default function CDRPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  
  const activeTab = searchParams.get('tab') || 'overview';
  
  const setActiveTab = (tab: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', tab);
    router.push(`${pathname}?${params.toString()}`);
  };

  React.useEffect(() => {
    document.title = 'Detection (CDR) - CloudVisor';
  }, []);

  return (
    <ProtectedRoute>
      <AppLayout
        breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Detection (CDR)' }]}
        cspmActiveTab={activeTab}
        onCspmTabChange={setActiveTab}
      >
      {/* Page header — Only shown on Overview tab */}
      {activeTab === 'overview' && (
        <div className="mb-4">
          <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>CDR — Cloud Detection & Response</h1>
          <p className="mt-0.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
            Real-time threat detection and incident response
          </p>
        </div>
      )}

      {/* Tab Content */}
      <div className={activeTab === 'overview' ? 'mt-4' : 'mt-0'}>
        {activeTab === 'overview' && <OverviewTab />}
        {activeTab === 'findings' && <FindingsTab />}
        {activeTab === 'assets' && <AssetsTab />}
        {activeTab === 'policies' && <PoliciesTab />}
        {activeTab === 'reports' && <ReportsTab />}
      </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
