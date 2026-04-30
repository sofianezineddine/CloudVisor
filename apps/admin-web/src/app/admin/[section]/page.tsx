'use client';

import React from 'react';
import { AdminLayout } from '@/components/admin-layout';
import { AdminProtectedRoute } from '@/components/admin-protected-route';
import { CreditCard, BarChart3, Activity, AlertTriangle, Cloud, Settings } from 'lucide-react';

const pages: Record<string, { icon: React.ElementType; title: string; desc: string }> = {
  billing: { icon: CreditCard, title: 'Billing & Subscriptions', desc: 'Manage client billing and subscription plans' },
  analytics: { icon: BarChart3, title: 'Platform Analytics', desc: 'Usage metrics and platform performance data' },
  'platform-health': { icon: Activity, title: 'Platform Health', desc: 'Service status and infrastructure monitoring' },
  'security-events': { icon: AlertTriangle, title: 'Security Events', desc: 'Platform-level security alerts and audit logs' },
  'cloud-accounts': { icon: Cloud, title: 'Cloud Accounts Overview', desc: 'All connected cloud accounts across clients' },
  settings: { icon: Settings, title: 'Admin Settings', desc: 'Platform configuration and admin preferences' },
};

export default function AdminPlaceholderPage({ params }: { params: { section: string } }) {
  const page = pages[params.section];
  if (!page) return (
    <AdminProtectedRoute>
      <AdminLayout>
        <div className="admin-card p-12 text-center">
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Page not found</p>
        </div>
      </AdminLayout>
    </AdminProtectedRoute>
  );

  const Icon = page.icon;

  return (
    <AdminProtectedRoute>
      <AdminLayout>
        <div className="mb-5">
          <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{page.title}</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>{page.desc}</p>
        </div>

        <div className="admin-card p-12 text-center">
          <Icon className="mx-auto mb-3 h-10 w-10" style={{ color: 'var(--text-tertiary)' }} />
          <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{page.title}</p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>This section is coming soon</p>
        </div>
      </AdminLayout>
    </AdminProtectedRoute>
  );
}
