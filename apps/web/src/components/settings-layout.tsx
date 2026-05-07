'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Header, Bar3, STICKY_HEADER_H, BAR3_H, BOTTOM_BAR_H } from '@/components/layout/header';
import {
  User,
  CreditCard,
  Key,
  History,
  Bell,
  Users,
  Cloud,
  ShieldOff,
  Webhook,
} from 'lucide-react';

const settingsSections = [
  {
    id: 'account',
    label: 'Account',
    items: [
      { id: 'profile', label: 'Profile', href: '/settings/profile', icon: User },
      { id: 'billing', label: 'Billing & Payments', href: '/settings/billing', icon: CreditCard },
      { id: 'api-keys', label: 'API Keys', href: '/settings/api-keys', icon: Key },
      { id: 'activity', label: 'Activity Log', href: '/settings/activity', icon: History },
    ],
  },
  {
    id: 'workspace',
    label: 'Workspace',
    items: [
      { id: 'cloud-accounts', label: 'Cloud Accounts', href: '/settings/cloud-accounts', icon: Cloud },
      { id: 'team', label: 'Team', href: '/settings/team', icon: Users },
      { id: 'notifications', label: 'Notifications', href: '/settings/notifications', icon: Bell },
      { id: 'webhooks', label: 'Webhooks', href: '/settings/webhooks', icon: Webhook },
      { id: 'suppressions', label: 'Suppression Rules', href: '/settings/suppressions', icon: ShieldOff },
    ],
  },
];

const BREADCRUMBS = [
  { text: 'Home', href: '/console' },
  { text: 'Settings' },
];

interface SettingsLayoutProps {
  children: React.ReactNode;
}

function BottomBar() {
  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-30 flex items-center justify-between px-3 py-1"
      style={{ height: BOTTOM_BAR_H + 'px', backgroundColor: '#131920', borderTop: '1px solid rgba(255,255,255,0.2)' }}
    >
      <div className="flex items-center gap-4">
        {['Feedback', 'Console Mobile App'].map(label => (
          <button key={label} className="flex items-center gap-1 text-xs transition-colors" style={{ color: '#ffffff' }}
            onMouseEnter={e => { (e.currentTarget.style.textDecoration = 'underline'); }}
            onMouseLeave={e => { (e.currentTarget.style.textDecoration = 'none'); }}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-3 text-xs" style={{ color: 'rgba(255,255,255,0.7)' }}>
        <span className="hidden lg:block">© 2026 CloudVisor, Inc. or its affiliates.</span>
        {['Privacy', 'Terms', 'Cookie preferences'].map(item => (
          <button key={item} className="transition-colors" style={{ color: '#ffffff' }}
            onMouseEnter={e => { (e.currentTarget.style.textDecoration = 'underline'); }}
            onMouseLeave={e => { (e.currentTarget.style.textDecoration = 'none'); }}
          >{item}</button>
        ))}
      </div>
    </div>
  );
}

export function SettingsLayout({ children }: SettingsLayoutProps) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = React.useState(true); // Start with sidebar open

  // Close sidebar on mobile when route changes
  React.useEffect(() => {
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  }, [pathname]);

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-base)' }}>
      {/* Header */}
      <Header
        onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}
        breadcrumbs={BREADCRUMBS}
        sidebarOpen={sidebarOpen}
      />

      {/* Body */}
      <div
        className="flex w-full"
        style={{
          minHeight: `calc(100vh - ${STICKY_HEADER_H}px - ${BOTTOM_BAR_H}px)`,
        }}
      >
        {/* Bar 3 - breadcrumb bar */}
        <div className="w-full">
          <Bar3 onSidebarToggle={() => setSidebarOpen(!sidebarOpen)} breadcrumbs={BREADCRUMBS} />

          {/* Content row: Sidebar + Main content */}
          <div className="flex">
            {/* Settings Sidebar - Only show when open */}
            {sidebarOpen && (
              <aside
                className="flex-shrink-0 border-r transition-all duration-200 ease-in-out"
                style={{
                  width: '220px',
                  borderColor: 'var(--border-default)',
                  backgroundColor: 'var(--bg-surface)',
                  position: 'sticky',
                  top: `${STICKY_HEADER_H + BAR3_H}px`,
                  height: `calc(100vh - ${STICKY_HEADER_H + BAR3_H}px - ${BOTTOM_BAR_H}px)`,
                  overflowY: 'auto',
                }}
              >
                <div className="p-4">
                  {/* Navigation */}
                  <nav className="space-y-6">
                    {settingsSections.map((section) => (
                      <div key={section.id}>
                        <h3
                          className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider"
                          style={{ color: 'var(--text-tertiary)' }}
                        >
                          {section.label}
                        </h3>
                        <ul className="space-y-1">
                          {section.items.map((item) => {
                            const Icon = item.icon;
                            const isActive = pathname === item.href;
                            return (
                              <li key={item.id}>
                                <Link
                                  href={item.href}
                                  className={cn(
                                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors'
                                  )}
                                  style={
                                    isActive
                                      ? {
                                          backgroundColor: 'var(--accent-dim)',
                                          color: 'var(--accent)',
                                        }
                                      : { color: 'var(--text-secondary)' }
                                  }
                                  onMouseEnter={(e) => {
                                    if (!isActive) {
                                      e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
                                      e.currentTarget.style.color = 'var(--text-primary)';
                                    }
                                  }}
                                  onMouseLeave={(e) => {
                                    if (!isActive) {
                                      e.currentTarget.style.backgroundColor = 'transparent';
                                      e.currentTarget.style.color = 'var(--text-secondary)';
                                    }
                                  }}
                                >
                                  <Icon className="h-4 w-4 flex-shrink-0" />
                                  {item.label}
                                </Link>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    ))}
                  </nav>
                </div>
              </aside>
            )}

            {/* Main Content */}
            <main
              className="flex-1 overflow-auto"
              style={{
                paddingBottom: BOTTOM_BAR_H + 'px',
              }}
            >
              <div className="mx-auto max-w-7xl px-4 py-4">{children}</div>
            </main>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <BottomBar />
    </div>
  );
}
