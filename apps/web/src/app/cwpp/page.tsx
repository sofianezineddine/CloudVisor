'use client';

import * as React from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { Button } from '@/components/ui/button';
import { Play, Loader2 } from 'lucide-react';
import { useScopeStore } from '@/stores/scope';
import { NoAccountsConnectedEmptyState } from '@/components/ui/no-accounts-empty-state';

// Import Tabs
import { OverviewTab } from './tabs/overview-tab';
import { FindingsTab } from './tabs/findings-tab';
import { AssetsTab } from './tabs/assets-tab';
import { PoliciesTab } from './tabs/policies-tab';
import { ReportsTab } from './tabs/reports-tab';

export default function CWPPPage() {
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
    document.title = 'CWPP - CloudVisor';
  }, []);

  return (
    <ProtectedRoute>
      <AppLayout
        breadcrumbs={[{ text: 'Home', href: '/console' }, { text: 'CWPP' }]}
        cspmActiveTab={activeTab}
        onCspmTabChange={setActiveTab}
      >
        {accountIds.length === 0 ? (
          <NoAccountsConnectedEmptyState />
        ) : (
          <>
            {activeTab === 'overview' && (
              <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h1 className="text-h1" style={{ color: 'var(--text-primary)' }}>Cloud Workload Protection</h1>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Agentless vulnerability scanning for VMs, containers, and serverless</p>
                </div>
                <Button className="gap-2">
                  <Play className="h-4 w-4" />
                  Scan All
                </Button>
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
