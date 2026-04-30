'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, Users, CreditCard, BarChart3,
  Settings, Activity, AlertTriangle, Cloud, ChevronDown, X,
} from 'lucide-react';

const navSections = [
  {
    id: 'overview',
    label: 'Overview',
    items: [
      { label: 'Dashboard', href: '/admin/dashboard', icon: LayoutDashboard },
    ],
  },
  {
    id: 'management',
    label: 'Management',
    items: [
      { label: 'Clients', href: '/admin/clients', icon: Users },
      { label: 'Billing', href: '/admin/billing', icon: CreditCard },
      { label: 'Cloud Accounts', href: '/admin/cloud-accounts', icon: Cloud },
    ],
  },
  {
    id: 'monitoring',
    label: 'Monitoring',
    items: [
      { label: 'Analytics', href: '/admin/analytics', icon: BarChart3 },
      { label: 'Platform Health', href: '/admin/platform-health', icon: Activity },
      { label: 'Security Events', href: '/admin/security-events', icon: AlertTriangle },
    ],
  },
  {
    id: 'config',
    label: 'Configuration',
    items: [
      { label: 'Settings', href: '/admin/settings', icon: Settings },
    ],
  },
];

interface AdminSidebarProps {
  onClose?: () => void;
}

export function AdminSidebar({ onClose }: AdminSidebarProps) {
  const pathname = usePathname();
  const [collapsedSections, setCollapsedSections] = React.useState<Set<string>>(new Set());

  const toggleSection = (id: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  // Auto-expand section with active route
  React.useEffect(() => {
    for (const section of navSections) {
      const hasActive = section.items.some(
        item => pathname === item.href || pathname.startsWith(item.href + '/')
      );
      if (hasActive) {
        setCollapsedSections(prev => {
          if (!prev.has(section.id)) return prev;
          const next = new Set(prev);
          next.delete(section.id);
          return next;
        });
      }
    }
  }, [pathname]);

  return (
    <aside
      className="flex h-full w-[220px] flex-col border-r"
      style={{ backgroundColor: 'var(--sidebar-bg)', borderColor: 'var(--sidebar-border)' }}
    >
      {/* Sidebar header */}
      <div
        className="flex items-center justify-between border-b px-3"
        style={{ borderColor: 'var(--sidebar-border)', minHeight: '44px' }}
      >
        <Link href="/admin/dashboard"
          className="text-sm font-semibold transition-colors"
          style={{ color: 'var(--text-primary)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-link)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-primary)')}
          onClick={onClose}
        >
          Admin Console
        </Link>
        {onClose && (
          <button onClick={onClose}
            className="flex h-6 w-6 items-center justify-center rounded transition-colors ml-auto"
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-1" style={{ scrollbarWidth: 'none' }}>
        {navSections.map((section, idx) => {
          const isSectionCollapsed = collapsedSections.has(section.id);
          return (
            <div key={section.id} className={idx > 0 ? 'mt-0.5' : ''}>
              <button
                onClick={() => toggleSection(section.id)}
                className="flex w-full items-center gap-1 px-3 py-1 text-left transition-colors"
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                <ChevronDown
                  className={`h-3 w-3 flex-shrink-0 transition-transform duration-150 ${isSectionCollapsed ? '-rotate-90' : ''}`}
                  style={{ color: 'var(--text-tertiary)' }}
                />
                <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)', letterSpacing: '0.8px' }}>
                  {section.label}
                </span>
              </button>

              {!isSectionCollapsed && (
                <ul className="pb-0.5">
                  {section.items.map(item => {
                    const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
                    const Icon = item.icon;
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          onClick={onClose}
                          className="flex h-8 items-center gap-2 pl-5 pr-3 text-sm transition-colors"
                          style={{
                            color: 'var(--text-link)',
                            fontWeight: isActive ? 700 : 400,
                            backgroundColor: isActive ? 'var(--bg-elevated)' : 'transparent',
                            borderLeft: isActive ? '3px solid #ec7211' : '3px solid transparent',
                          }}
                          onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                          onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'; }}
                        >
                          <Icon className="h-3.5 w-3.5 flex-shrink-0" style={{ color: isActive ? '#ec7211' : 'var(--text-tertiary)' }} strokeWidth={1.75} />
                          <span className="truncate">{item.label}</span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
