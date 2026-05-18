'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Bell,
  Flame,
  GitBranch,
  Plug,
  Network,
  LayoutDashboard,
  Settings,
  Scale,
  Copy,
  Wrench,
  Filter,
  Map,
} from 'lucide-react';
import { ProtectedRoute } from '@/components/protected-route';
import { AppLayout } from '@/components/layout';
import './aiops-theme.css';

// ─── AIOps Sidebar Tab Definitions ───────────────────────────────────────────

interface AIOpsTab {
  id: string;
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
}

const AIOPS_TABS: AIOpsTab[] = [
  { id: 'alerts', label: 'Alerts', href: '/aiops/alerts', icon: Bell },
  { id: 'incidents', label: 'Incidents', href: '/aiops/incidents', icon: Flame },
  { id: 'workflows', label: 'Workflows', href: '/aiops/workflows', icon: GitBranch },
  { id: 'providers', label: 'Providers', href: '/aiops/providers', icon: Plug },
  { id: 'topology', label: 'Topology', href: '/aiops/topology', icon: Network },
  { id: 'dashboard', label: 'Dashboard', href: '/aiops/dashboard', icon: LayoutDashboard },
  { id: 'settings', label: 'Settings', href: '/aiops/settings', icon: Settings },
  { id: 'rules', label: 'Rules', href: '/aiops/rules', icon: Scale },
  { id: 'deduplication', label: 'Deduplication', href: '/aiops/deduplication', icon: Copy },
  { id: 'maintenance', label: 'Maintenance', href: '/aiops/maintenance', icon: Wrench },
  { id: 'extraction', label: 'Extraction', href: '/aiops/extraction', icon: Filter },
  { id: 'mapping', label: 'Mapping', href: '/aiops/mapping', icon: Map },
];

// ─── AIOps Sidebar Component ─────────────────────────────────────────────────

function AIOpsSidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="flex h-full flex-col border-r"
      style={{
        width: '220px',
        backgroundColor: 'var(--color-bg-surface)',
        borderColor: 'var(--color-border)',
      }}
    >
      {/* Section Header */}
      <div
        className="flex items-center px-4 py-3 border-b"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <span
          className="text-xs font-semibold uppercase tracking-wider"
          style={{ color: 'var(--color-text-secondary)', letterSpacing: '0.05em' }}
        >
          AIOps
        </span>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex-1 overflow-y-auto py-2" style={{ scrollbarWidth: 'thin' }}>
        <ul className="space-y-0.5 px-2">
          {AIOPS_TABS.map((tab) => {
            const isActive =
              pathname === tab.href || pathname.startsWith(tab.href + '/');
            const Icon = tab.icon;

            return (
              <li key={tab.id}>
                <Link
                  href={tab.href}
                  className="group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors"
                  style={{
                    color: isActive
                      ? 'var(--color-primary)'
                      : 'var(--color-text-secondary)',
                    backgroundColor: isActive
                      ? 'rgba(74, 144, 217, 0.12)'
                      : 'transparent',
                    borderLeft: isActive
                      ? '2px solid var(--color-primary)'
                      : '2px solid transparent',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor =
                        'var(--color-bg-hover)';
                      e.currentTarget.style.color = 'var(--color-text-primary)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                      e.currentTarget.style.color = 'var(--color-text-secondary)';
                    }
                  }}
                >
                  <Icon
                    className="h-4 w-4 flex-shrink-0"
                    style={{
                      color: isActive
                        ? 'var(--color-primary)'
                        : 'var(--color-text-secondary)',
                    }}
                  />
                  <span className="truncate">{tab.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}

// ─── AIOps Layout ────────────────────────────────────────────────────────────

export default function AIOpsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="aiops-scope flex h-full" style={{ margin: '-12px -16px' }}>
          {/* AIOps Sidebar */}
          <div
            className="flex-shrink-0 hidden md:block"
            style={{
              width: '220px',
              position: 'sticky',
              top: 0,
              height: 'calc(100vh - 120px)',
              overflowY: 'auto',
            }}
          >
            <AIOpsSidebar />
          </div>

          {/* Main Content Area */}
          <main
            className="flex-1 min-w-0 p-6"
            style={{ backgroundColor: 'var(--color-bg-base)' }}
          >
            {children}
          </main>
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
