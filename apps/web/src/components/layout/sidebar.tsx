'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronDown, X } from 'lucide-react';
import { SERVICES, getServiceByPath, getActiveTabFromPath, type ServiceDefinition } from '@/lib/services-registry';

// ─── Global Navigation Sections (shown when NOT inside a service) ─────────────

const navSections = [
  {
    id: 'protection',
    label: 'Security & Posture',
    items: [
      { label: 'CSPM', href: '/cspm' },
      { label: 'CWPP', href: '/cwpp' },
      { label: 'Identity (CIEM)', href: '/ciem' },
      { label: 'Kubernetes (KSPM)', href: '/kspm' },
      { label: 'Data (DSPM)', href: '/dspm' },
      { label: 'CI/CD Security', href: '/cicd' },
      { label: 'Detection (CDR)', href: '/cdr' },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    items: [
      { label: 'AIOps', href: '/aiops' },
      { label: 'CloudVisor Q', href: '/copilot', isNew: true },
    ],
  },
  {
    id: 'settings',
    label: 'Settings',
    items: [
      { label: 'Cloud Accounts', href: '/settings' },
      { label: 'Notifications', href: '/settings/notifications' },
      { label: 'Team', href: '/settings/team' },
      { label: 'API Keys', href: '/settings/api-keys' },
      { label: 'Billing', href: '/settings/billing' },
    ],
  },
];

const CONSOLE_PATHS = ['/console'];

// ─── Count Badge ──────────────────────────────────────────────────────────────

function CountBadge({ count }: { count: number }) {
  const isCritical = count > 10;
  return (
    <span
      className="ml-auto flex-shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold leading-none"
      style={{
        backgroundColor: isCritical ? 'var(--critical-bg)' : 'var(--bg-elevated)',
        color: isCritical ? 'var(--critical)' : 'var(--text-secondary)',
        border: `1px solid ${isCritical ? 'var(--critical-border)' : 'var(--border-default)'}`,
      }}
    >
      {count}
    </span>
  );
}

// ─── Service Sidebar (shown when inside a service) ────────────────────────────

function ServiceSidebar({
  service,
  activeTab,
  onClose,
  onTabChange,
}: {
  service: ServiceDefinition;
  activeTab: string;
  onClose?: () => void;
  onTabChange?: (tab: string) => void;
}) {
  const [collapsedSections, setCollapsedSections] = React.useState<Set<string>>(new Set());

  const toggleSection = (label: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  return (
    <div className="py-2">
      {service.sections.map((section, sIdx) => {
        const isCollapsed = section.label ? collapsedSections.has(section.label) : false;
        return (
          <div key={sIdx} className={sIdx > 0 ? 'mt-4' : ''}>
            {section.label && (
              <button
                onClick={() => toggleSection(section.label!)}
                className="flex w-full items-center gap-1 px-3 py-1 text-left transition-colors"
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                <ChevronDown
                  className={`h-3 w-3 transition-transform duration-150 ${isCollapsed ? '-rotate-90' : ''}`}
                  style={{ color: 'var(--text-tertiary)' }}
                />
                <h3
                  className="text-[11px] font-bold uppercase tracking-wider"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {section.label}
                </h3>
              </button>
            )}
            {!isCollapsed && (
              <ul className="mt-0.5">
                {section.tabs.map(tab => {
                  const isTabActive = activeTab === tab.id;
                  // If a tab change handler is provided (CSPM uses ?tab= params),
                  // use it instead of navigating to a new path.
                  // Only close the sidebar on mobile (onClose is the mobile close handler).
                  if (onTabChange) {
                    return (
                      <li key={tab.id}>
                        <button
                          onClick={() => {
                            onTabChange(tab.id);
                            // Only close sidebar on mobile — on desktop keep it open
                            if (typeof window !== 'undefined' && window.innerWidth < 768) {
                              onClose?.();
                            }
                          }}
                          className="group flex h-8 w-full items-center pl-4 pr-3 text-sm transition-colors text-left"
                          style={{
                            color: isTabActive ? '#0972d3' : 'var(--text-secondary)',
                            fontWeight: isTabActive ? 700 : 400,
                            backgroundColor: isTabActive ? 'var(--bg-elevated)' : 'transparent',
                          }}
                          onMouseEnter={e => {
                            if (!isTabActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)';
                          }}
                          onMouseLeave={e => {
                            if (!isTabActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                          }}
                        >
                          <span className="truncate flex-1 text-left">{tab.label}</span>
                          {tab.count !== undefined && <CountBadge count={tab.count} />}
                        </button>
                      </li>
                    );
                  }
                  const href = `${service.path}/${tab.id}`;
                  return (
                    <li key={tab.id}>
                      <Link
                        href={href}
                        onClick={() => {
                          // Only close sidebar on mobile overlay
                          if (typeof window !== 'undefined' && window.innerWidth < 768) {
                            onClose?.();
                          }
                        }}
                        className="group flex h-8 w-full items-center pl-4 pr-3 text-sm transition-colors"
                        style={{
                          color: isTabActive ? '#0972d3' : 'var(--text-secondary)',
                          fontWeight: isTabActive ? 700 : 400,
                          backgroundColor: isTabActive ? 'var(--bg-elevated)' : 'transparent',
                        }}
                        onMouseEnter={e => {
                          if (!isTabActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)';
                        }}
                        onMouseLeave={e => {
                          if (!isTabActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                        }}
                      >
                        <span className="truncate flex-1 text-left">{tab.label}</span>
                        {tab.count !== undefined && <CountBadge count={tab.count} />}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Sidebar Component ───────────────────────────────────────────────────

export interface SidebarProps {
  onClose?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onMobileClose?: () => void;
  cspmActiveTab?: string;
  onCspmTabChange?: (tab: string) => void;
}

export function Sidebar({ onClose, onMobileClose, cspmActiveTab, onCspmTabChange }: SidebarProps) {
  const pathname = usePathname();
  const [collapsedSections, setCollapsedSections] = React.useState<Set<string>>(new Set());
  const handleClose = onClose ?? onMobileClose;

  const isConsole = CONSOLE_PATHS.includes(pathname);
  const isServices = pathname === '/services';

  // Detect if we are inside a service
  const activeService = getServiceByPath(pathname);
  // For CSPM (which uses ?tab= query params), use the passed cspmActiveTab.
  // For other services that use path segments, use getActiveTabFromPath.
  const activeTab = (activeService?.id === 'cspm' && cspmActiveTab)
    ? cspmActiveTab
    : (getActiveTabFromPath(pathname) || (activeService?.defaultTab ?? ''));

  const toggleSection = (id: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <aside
      className="flex h-full w-full md:w-[220px] flex-col border-r"
      style={{ backgroundColor: 'var(--sidebar-bg, #ffffff)', borderColor: 'var(--sidebar-border, #d5dbdb)' }}
    >
      {/* Sidebar Header */}
      <div
        className="flex items-center justify-between border-b px-3"
        style={{ borderColor: 'var(--sidebar-border, #d5dbdb)', minHeight: '44px' }}
      >
        <Link
          href={activeService ? activeService.path : '/console'}
          className="text-sm font-bold transition-colors"
          style={{ color: 'var(--text-primary)' }}
          onMouseEnter={e => (e.currentTarget.style.color = '#0972d3')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-primary)')}
          onClick={handleClose}
        >
          {activeService ? activeService.label : isConsole || isServices ? 'Services' : 'Home Console'}
        </Link>
        {handleClose && (
          <button
            onClick={handleClose}
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
        {(isConsole || isServices) ? (
          /* Console/Services Sidebar */
          <ul className="py-1">
            <li>
              <Link
                href="/services"
                onClick={handleClose}
                className="flex h-8 items-center px-4 text-sm transition-colors"
                style={{
                  color: '#0972d3',
                  fontWeight: isServices ? 700 : 400,
                  backgroundColor: 'transparent',
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'; }}
              >
                Services
              </Link>
            </li>
          </ul>
        ) : activeService ? (
          /* Service-scoped sidebar — shows only this service's tabs */
          <ServiceSidebar
            service={activeService}
            activeTab={activeTab}
            onClose={handleClose}
            onTabChange={activeService.id === 'cspm' ? onCspmTabChange : undefined}
          />
        ) : (
          /* Global Navigation — shown on non-service pages (e.g. /settings) */
          navSections.map((section, idx) => {
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
                    className={`h-3 w-3 transition-transform duration-150 ${isSectionCollapsed ? '-rotate-90' : ''}`}
                    style={{ color: 'var(--text-tertiary)' }}
                  />
                  <span
                    className="text-xs font-bold uppercase tracking-wider"
                    style={{ color: 'var(--text-primary)', letterSpacing: '0.8px' }}
                  >
                    {section.label}
                  </span>
                </button>

                {!isSectionCollapsed && (
                  <ul className="pb-0.5">
                    {section.items.map(item => {
                      const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
                      return (
                        <li key={item.href}>
                          <Link
                            href={item.href}
                            onClick={handleClose}
                            className="flex h-8 items-center gap-2 pl-6 pr-3 text-sm transition-colors"
                            style={{
                              color: isActive ? '#0972d3' : 'var(--text-secondary)',
                              fontWeight: isActive ? 700 : 400,
                              backgroundColor: 'transparent',
                            }}
                            onMouseEnter={e => {
                              if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)';
                            }}
                            onMouseLeave={e => {
                              if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                            }}
                          >
                            <span className="truncate flex-1">{item.label}</span>
                            {(item as any).isNew && (
                              <span
                                className="rounded px-1 py-0.5 text-[9px] font-bold uppercase"
                                style={{ backgroundColor: '#ff9900', color: '#000' }}
                              >
                                New
                              </span>
                            )}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            );
          })
        )}
      </nav>
    </aside>
  );
}
