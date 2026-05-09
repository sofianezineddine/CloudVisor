'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronDown, X, Search } from 'lucide-react';

// ─── Service Hub Tab Structure (Sectioned) ────────────────────────────────────

interface ServiceTab {
  id: string;
  label: string;
  count?: number;
}

interface ServiceSection {
  label: string | null;
  items: ServiceTab[];
}

const SERVICE_TABS: Record<string, ServiceSection[]> = {
  '/cspm': [
    { label: null, items: [{ id: 'overview', label: 'Overview' }] },
    { label: 'Findings & Response', items: [{ id: 'findings', label: 'Findings', count: 47 }, { id: 'incidents', label: 'Incidents', count: 2 }] },
    { label: 'Resource Inventory', items: [{ id: 'assets', label: 'Assets' }, { id: 'risk-map', label: 'Risk Explorer' }] },
    { label: 'Governance & Reports', items: [{ id: 'compliance', label: 'Compliance' }, { id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] },
    { label: 'Operations', items: [{ id: 'scan-history', label: 'Scan History' }] }
  ],
  '/cwpp': [
    { label: null, items: [{ id: 'overview', label: 'Overview' }] },
    { label: 'Protection', items: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
    { label: 'Governance', items: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] }
  ],
  '/ciem': [
    { label: null, items: [{ id: 'overview', label: 'Overview' }] },
    { label: 'Identity', items: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
    { label: 'Governance', items: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] }
  ],
  '/kspm': [
    { label: null, items: [{ id: 'overview', label: 'Overview' }] },
    { label: 'Kubernetes', items: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
    { label: 'Governance', items: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] }
  ],
  '/dspm': [
    { label: null, items: [{ id: 'overview', label: 'Overview' }] },
    { label: 'Data', items: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
    { label: 'Governance', items: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] }
  ],
  '/cicd': [
    { label: null, items: [{ id: 'overview', label: 'Overview' }] },
    { label: 'Pipeline', items: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
    { label: 'Governance', items: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] }
  ],
  '/cdr': [
    { label: null, items: [{ id: 'overview', label: 'Overview' }] },
    { label: 'Detection', items: [{ id: 'findings', label: 'Findings' }, { id: 'assets', label: 'Assets' }] },
    { label: 'Governance', items: [{ id: 'policies', label: 'Policies' }, { id: 'reports', label: 'Reports' }] }
  ],
};

// ─── Global Navigation Sections ───────────────────────────────────────────────

const navSections = [
  {
    id: 'protection',
    label: 'Security & Posture',
    items: [
      { label: 'CSPM', href: '/cspm' },
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

const CONSOLE_PATHS = ['/console'];

interface SidebarProps {
  onClose?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onMobileClose?: () => void;
  cspmActiveTab?: string;
  onCspmTabChange?: (tab: string) => void;
}

function CountBadge({ count }: { count: number }) {
  const isCritical = count > 10;
  return (
    <span className="ml-auto flex-shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold leading-none"
      style={{
        backgroundColor: isCritical ? 'var(--critical-bg)' : 'var(--bg-elevated)',
        color: isCritical ? 'var(--critical)' : 'var(--text-secondary)',
        border: `1px solid ${isCritical ? 'var(--critical-border)' : 'var(--border-default)'}`,
      }}>
      {count}
    </span>
  );
}

export function Sidebar({ onClose, onMobileClose, cspmActiveTab: activeTab, onCspmTabChange: onTabChange }: SidebarProps) {
  const pathname = usePathname();
  const [collapsedSections, setCollapsedSections] = React.useState<Set<string>>(new Set());
  const [collapsedHubSections, setCollapsedHubSections] = React.useState<Set<string>>(new Set());
  const handleClose = onClose ?? onMobileClose;

  const isConsole = CONSOLE_PATHS.includes(pathname);
  const isServices = pathname === '/services';
  
  // Detect if we are in a service hub
  const servicePath = Object.keys(SERVICE_TABS).find(path => pathname === path || pathname.startsWith(path + '/'));
  const isOnServiceHub = !!servicePath;
  const currentServiceTabs = servicePath ? SERVICE_TABS[servicePath] : [];

  const toggleSection = (id: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleHubSection = (label: string) => {
    setCollapsedHubSections(prev => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label); else next.add(label);
      return next;
    });
  };

  return (
    <aside className="flex h-full w-full md:w-[220px] flex-col border-r"
      style={{ backgroundColor: 'var(--sidebar-bg, #ffffff)', borderColor: 'var(--sidebar-border, #d5dbdb)' }}>
      
      {/* Sidebar Header */}
      <div className="flex items-center justify-between border-b px-3"
        style={{ borderColor: 'var(--sidebar-border, #d5dbdb)', minHeight: '44px' }}>
        <Link href={isConsole ? "/services" : "/console"}
          className="text-sm font-bold transition-colors"
          style={{ color: 'var(--text-primary)' }}
          onMouseEnter={e => (e.currentTarget.style.color = '#0972d3')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-primary)')}
          onClick={handleClose}>
          {servicePath === '/cspm' ? 'CSPM' : 
           servicePath === '/cwpp' ? 'CWPP' :
           servicePath === '/ciem' ? 'CIEM' :
           servicePath === '/kspm' ? 'KSPM' :
           servicePath === '/dspm' ? 'DSPM' :
           servicePath === '/cicd' ? 'CI/CD Security' :
           servicePath === '/cdr'  ? 'CDR' :
           isConsole || isServices ? 'Services' : 'Home Console'}
        </Link>
        {handleClose && (
          <button onClick={handleClose} className="flex h-6 w-6 items-center justify-center rounded transition-colors ml-auto"
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-1" style={{ scrollbarWidth: 'none' }}>
        {(isConsole || isServices) ? (
           /* Console/Services Sidebar: only "Services" link */
           <ul className="py-1">
             <li>
               <Link href="/services" onClick={handleClose}
                 className="flex h-8 items-center px-4 text-sm transition-colors"
                 style={{
                   color: '#0972d3',
                   fontWeight: isServices ? 700 : 400,
                   backgroundColor: 'transparent',
                 }}
                 onMouseEnter={e => { (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                 onMouseLeave={e => { (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'; }}>
                 Services
               </Link>
             </li>
           </ul>
        ) : isOnServiceHub && pathname === servicePath ? (
          /* Service-specific Sectioned Navigation (EC2 Pattern) with AIOps Style */
          <div className="py-2">
            {currentServiceTabs.map((section, sIdx) => {
              const isCollapsed = section.label ? collapsedHubSections.has(section.label) : false;
              return (
                <div key={sIdx} className={sIdx > 0 ? 'mt-4' : ''}>
                  {section.label && (
                    <button onClick={() => toggleHubSection(section.label!)}
                      className="flex w-full items-center gap-1 px-3 py-1 text-left transition-colors"
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                      <ChevronDown className={`h-3 w-3 transition-transform duration-150 ${isCollapsed ? '-rotate-90' : ''}`} style={{ color: 'var(--text-tertiary)' }} />
                      <h3 className="text-[11px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-primary)' }}>
                        {section.label}
                      </h3>
                    </button>
                  )}
                  {!isCollapsed && (
                    <ul className="mt-0.5">
                      {section.items.map(tab => {
                        const isTabActive = activeTab === tab.id;
                        return (
                          <li key={tab.id}>
                            <button onClick={() => onTabChange?.(tab.id)}
                              className="group flex h-8 w-full items-center pl-4 pr-3 text-sm transition-colors"
                              style={{
                                color: isTabActive ? '#0972d3' : 'var(--text-secondary)',
                                fontWeight: isTabActive ? 700 : 400,
                                backgroundColor: 'transparent',
                              }}
                              onMouseEnter={e => { if (!isTabActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                              onMouseLeave={e => { if (!isTabActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'; }}>
                              <span className="truncate flex-1 text-left">{tab.label}</span>
                              {tab.count !== undefined && <CountBadge count={tab.count} />}
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          /* Global Navigation */
          navSections.map((section, idx) => {
            const isSectionCollapsed = collapsedSections.has(section.id);
            return (
              <div key={section.id} className={idx > 0 ? 'mt-0.5' : ''}>
                <button onClick={() => toggleSection(section.id)}
                  className="flex w-full items-center gap-1 px-3 py-1 text-left transition-colors"
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}>
                  <ChevronDown className={`h-3 w-3 transition-transform duration-150 ${isSectionCollapsed ? '-rotate-90' : ''}`} style={{ color: 'var(--text-tertiary)' }} />
                  <span className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--text-primary)', letterSpacing: '0.8px' }}>
                    {section.label}
                  </span>
                </button>

                {!isSectionCollapsed && (
                  <ul className="pb-0.5">
                    {section.items.map(item => {
                      const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
                      return (
                        <li key={item.href}>
                          <Link href={item.href} onClick={handleClose}
                            className="flex h-8 items-center gap-2 pl-6 pr-3 text-sm transition-colors"
                            style={{
                              color: isActive ? '#0972d3' : 'var(--text-secondary)',
                              fontWeight: isActive ? 700 : 400,
                              backgroundColor: 'transparent',
                            }}
                            onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-elevated)'; }}
                            onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'; }}>
                            <span className="truncate flex-1">{item.label}</span>
                            {(item as any).isNew && <span className="rounded px-1 py-0.5 text-[9px] font-bold uppercase" style={{ backgroundColor: '#ff9900', color: '#000' }}>New</span>}
                            {(item as any).count !== undefined && <CountBadge count={(item as any).count} />}
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
