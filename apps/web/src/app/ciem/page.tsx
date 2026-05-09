'use client';

import * as React from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { useScopeStore } from '@/stores/scope';
import { NoAccountsConnectedEmptyState } from '@/components/ui/no-accounts-empty-state';

// Import Tabs
import { OverviewTab } from './tabs/overview-tab';
import { FindingsTab } from './tabs/findings-tab';
import { AssetsTab } from './tabs/assets-tab';
import { PoliciesTab } from './tabs/policies-tab';
import { ReportsTab } from './tabs/reports-tab';

export default function CIEMPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  
  const activeTab = searchParams.get('tab') || 'overview';
  
  const setActiveTab = (tab: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', tab);
    router.push(`${pathname}?${params.toString()}`);
  };

  const accountIds = useScopeStore(s => s.accountIds);

  React.useEffect(() => {
    document.title = 'Identity (CIEM) - CloudVisor';
  }, []);

  return (
    <ProtectedRoute>
      <AppLayout
        breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'Identity (CIEM)' }]}
        cspmActiveTab={activeTab}
        onCspmTabChange={setActiveTab}
      >
        {accountIds.length === 0 ? (
          <NoAccountsConnectedEmptyState />
        ) : (
          <>
            {/* Page header — Only shown on Overview tab */}
            {activeTab === 'overview' && (
              <div className="mb-4">
                <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>CIEM — Cloud Infrastructure Entitlements</h1>
                <p className="mt-0.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Identity and permissions management across all clouds
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
          </>
        )}
      </AppLayout>
    </ProtectedRoute>
  );
}
