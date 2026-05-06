'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { ChevronDown, X, Search } from 'lucide-react';

// ─── CSPM sub-tabs shown in sidebar when on /cspm ────────────────────────────
const CSPM_TABS = [
  { id: 'overview',          label: 'Overview' },
  { id: 'misconfigurations', label: 'Misconfigurations' },
  { id: 'compliance',        label: 'Compliance' },
  { id: 'policies',          label: 'Policies' },
  { id: 'inventory',         label: 'Inventory' },
  { id: 'reports',           label: 'Reports' },
  { id: 'scan-history',      label: 'Scan History' },
];

// ─── Navigation structure ─────────────────────────────────────────────────────

const homeSidebarItems = [
  { label: 'Services', href: '/services' },
];

const consoleSidebarItems = [
  { label: 'Services', href: '/services' },
];

const navSections = [
  {
    id: 'overview',
    label: 'Overview',
    items: [
      { label: 'Home Console', href: '/console' },
      { label: 'Risk Explorer', href: '/risk-map' },
    ],
  },
  {
    id: 'security',
    label: 'Security',
    items: [
      { label: 'Findings', href: '/findings', count: 47 },
      { label: 'Incidents', href: '/incidents', count: 2 },
      { label: 'Assets', href: '/assets' },
      { label: 'Compliance', href: '/compliance' },
    ],
  },
  {
    id: 'protection',
    label: 'Protection',
    items: [
      { label: 'CSPM', href: '/cspm', hasTabs: true },
      { label: 'CWPP', href: '/cwpp', count: 12 },
      { label: 'Identity (CIEM)', href: '/ciem' },
      { label: 'Kubernetes (KSPM)', href: '/kspm' },
      { label: 'Data (DSPM)', href: '/dspm' },
      { label: 'CI/CD Security', href: '/cicd' },
      { label: 'Detection (CDR)', href: '/cdr', count: 2 },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    items: [
      { label: 'AIOps', href: '/aiops' },
      { label: 'AI Copilot', href: '/copilot', isNew: true },
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

const HOME_PATHS = ['/console', '/services'];
const CONSOLE_PATHS = ['/console'];

interface SidebarProps {
  onClose?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onMobileClose?: () => void;
  // Active CSPM tab — passed from CSPM page
  cspmActiveTab?: string;
  onCspmTabChange?: (tab: string) => void;
}

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

export function Sidebar({ onClose, onMobileClose, cspmActiveTab, onCspmTabChange }: SidebarProps) {
  const pathname = usePathname();
  const [collapsedSections, setCollapsedSections] = React.useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = React.useState('');
  const handleClose = onClose ?? onMobileClose;

  const isHome = HOME_PATHS.includes(pathname);
  const isConsole = CONSOLE_PATHS.includes(pathname);
  const isOnCspm = pathname === '/cspm' || pathname.startsWith('/cspm/');

  // Filter navigation items based on search query
  const filteredSections = React.useMemo(() => {
    if (!searchQuery.trim()) return navSections;
    
    const query = searchQuery.toLowerCase();
    return navSections.map(section => ({
      ...section,
      items: section.items.filter(item => 
        item.label.toLowerCase().includes(query)
      )
    })).filter(section => section.items.length > 0);
  }, [searchQuery]);

  const toggleSection = (id: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

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
      className="flex h-full w-full md:w-[220px] flex-col border-r"
      style={{
        backgroundColor: 'var(--sidebar-bg, #ffffff)',
        borderColor: 'var(--sidebar-border, #d5dbdb)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between border-b px-3"
        style={{ borderColor: 'var(--sidebar-border, #d5dbdb)', minHeight: '44px' }}
      >
        <Link
          href={isConsole ? "/services" : "/console"}
          className="text-sm font-semibold transition-colors"
          style={{ color: 'var(--text-primary)' }}
          onMouseEnter={e => (e.currentTarget.style.color = '#0972d3')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-primary)')}
          onClick={handleClose}
        >
          {isOnCspm ? 'CSPM' : isConsole ? 'Services' : 'Home Console'}
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

      {/* Search Bar - AWS Style */}
      {!isOnCspm && !isConsole && !isHome && (
        <div className="border-b px-3 py-2" style={{ borderColor: 'var(--sidebar-border, #d5dbdb)' }}>
          <div className="relative">
            <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2" style={{ color: 'var(--text-tertiary)' }} />
            <input
              type="text"
              placeholder="Search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded border px-7 py-1.5 text-sm focus:outline-none focus:ring-1"
              style={{
                backgroundColor: 'var(--bg-surface)',
                borderColor: 'var(--border-default)',
                color: 'var(--text-primary)',
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
              onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border-default)')}
            />
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-1" style={{ scrollbarWidth: 'none' }}>
        {isOnCspm ? (
          <div>
            {/* CSPM tabs — no back link, no section header */}
            <ul className="pt-1">
              {CSPM_TABS.map(tab => {
                const isTabActive = cspmActiveTab === tab.id;
                return (
                  <li key={tab.id}>
                    <button
                      onClick={() => onCspmTabChange?.(tab.id)}
                      className="flex h-8 w-full items-center pl-4 pr-3 text-sm transition-colors"
                      style={{
                        color: isTabActive ? 'var(--text-primary)' : '#0972d3',
                        fontWeight: isTabActive ? 700 : 400,
                        backgroundColor: isTabActive ? 'rgba(236,114,17,0.08)' : 'transparent',
                        borderLeft: isTabActive ? '3px solid #ec7211' : '3px solid transparent',
                      }}
                      onMouseEnter={e => { if (!isTabActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                      onMouseLeave={e => { if (!isTabActive) (e.currentTarget as HTMLElement).style.backgroundColor = isTabActive ? 'rgba(236,114,17,0.08)' : 'transparent'; }}
                    >
                      {tab.label}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ) : isConsole ? (
          <ul className="py-1">
            {consoleSidebarItems.map(item => {
              const isActive = pathname === item.href;
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={handleClose}
                    className="flex h-8 items-center px-4 text-sm transition-colors"
                    style={{
                      color: '#0972d3',
                      fontWeight: isActive ? 700 : 400,
                      backgroundColor: isActive ? 'var(--bg-elevated)' : 'transparent',
                      borderLeft: isActive ? '3px solid #ec7211' : '3px solid transparent',
                    }}
                    onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                    onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'; }}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        ) : isHome ? (
          <ul className="py-1">
            {homeSidebarItems.map(item => {
              const isActive = pathname === item.href;
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={handleClose}
                    className="flex h-8 items-center px-4 text-sm transition-colors"
                    style={{
                      color: '#0972d3',
                      fontWeight: isActive ? 700 : 400,
                      backgroundColor: isActive ? 'var(--bg-elevated)' : 'transparent',
                      borderLeft: isActive ? '3px solid #ec7211' : '3px solid transparent',
                    }}
                    onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                    onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'; }}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        ) : (
          filteredSections.map((section, idx) => {
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
                      const hasTabs = (item as any).hasTabs && isActive;

                      return (
                        <React.Fragment key={item.href}>
                          <li>
                            <Link
                              href={item.href}
                              onClick={handleClose}
                              className="flex h-8 items-center gap-2 pl-6 pr-3 text-sm transition-colors"
                              style={{
                                color: '#0972d3',
                                fontWeight: isActive ? 700 : 400,
                                backgroundColor: isActive ? 'var(--bg-elevated)' : 'transparent',
                                borderLeft: isActive ? '3px solid #ec7211' : '3px solid transparent',
                              }}
                              onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                              onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'; }}
                            >
                              <span className="truncate flex-1">{item.label}</span>
                              {(item as any).isNew && (
                                <span className="rounded px-1 py-0.5 text-[9px] font-bold uppercase" style={{ backgroundColor: '#ff9900', color: '#000' }}>New</span>
                              )}
                              {(item as any).count !== undefined && <CountBadge count={(item as any).count} />}
                            </Link>
                          </li>

                          {/* CSPM sub-tabs — shown inline when on /cspm */}
                          {hasTabs && CSPM_TABS.map(tab => {
                            const isTabActive = cspmActiveTab === tab.id;
                            return (
                              <li key={tab.id}>
                                <button
                                  onClick={() => onCspmTabChange?.(tab.id)}
                                  className="flex h-7 w-full items-center pl-10 pr-3 text-xs transition-colors"
                                  style={{
                                    color: isTabActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                                    fontWeight: isTabActive ? 700 : 400,
                                    backgroundColor: isTabActive ? 'rgba(236,114,17,0.08)' : 'transparent',
                                    borderLeft: isTabActive ? '3px solid #ec7211' : '3px solid transparent',
                                  }}
                                  onMouseEnter={e => { if (!isTabActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                                  onMouseLeave={e => { if (!isTabActive) (e.currentTarget as HTMLElement).style.backgroundColor = isTabActive ? 'rgba(236,114,17,0.08)' : 'transparent'; }}
                                >
                                  {tab.label}
                                </button>
                              </li>
                            );
                          })}
                        </React.Fragment>
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
