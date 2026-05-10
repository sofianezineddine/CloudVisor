'use client';

import * as React from 'react';
import { AppLayout } from '@/components/layout';
import { ProtectedRoute } from '@/components/protected-route';
import { MoreVertical, Loader2, Plus, RotateCcw, ExternalLink, RefreshCw, X, 
         Shield, Cloud, Server, Database, Key, Lock, GitBranch, Terminal, 
         Activity, DollarSign, Sparkles, BookOpen, Compass, Bell, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { NoAccountsConnectedEmptyState } from '@/components/ui/no-accounts-empty-state';
import { useScopeStore } from '@/stores/scope';
import { useUserSettings, DEFAULT_WIDGET_ORDER } from '@/stores/user-settings';
import { useDashboardStats, useRecentFindings, useDashboardAccounts, useDashboardResources, useTopRiskyAssets, useDashboardActivity, useModulesSummary } from '@/hooks/use-dashboard';
import { useRecentlyVisited } from '@/hooks/use-recently-visited';
import { useServiceHealth } from '@/hooks/use-service-health';
import { MetricCard } from '@/components/ui/metric-card';
import { RiskScore } from '@/components/ui/risk-score';

function Sk({ w = 'w-full', h = 'h-4' }: { w?: string; h?: string }) {
  return <div className={w + ' ' + h + ' rounded animate-pulse'} style={{ backgroundColor: 'var(--bg-elevated)' }} />;
}

// ─── Module Icons ─────────────────────────────────────────────────────────────
const ModuleIcon = ({ module, size = 20 }: { module: string; size?: number }) => {
  const iconMap: Record<string, React.ReactNode> = {
    'CSPM': <Shield size={size} />,
    'CWPP': <Server size={size} />,
    'CIEM': <Key size={size} />,
    'KSPM': <Cloud size={size} />,
    'DSPM': <Database size={size} />,
    'CDR': <Activity size={size} />,
    'CI/CD': <GitBranch size={size} />,
    'AIOps': <Sparkles size={size} />,
  };
  return <>{iconMap[module] || <Shield size={size} />}</>;
};

// ─── Draggable Widget (Fixed Height) ──────────────────────────────────────────
function Widget({
  id, title, infoHref, detailHref, actions, children, className = '',
  onDragStart, onDragOver, onDrop, isDragOver, onRefresh, onRemove,
}: {
  id: string; title: string; infoHref?: string; detailHref?: string; actions?: React.ReactNode;
  children: React.ReactNode; className?: string;
  onDragStart?: (id: string) => void;
  onDragOver?: (e: React.DragEvent) => void;
  onDrop?: (id: string) => void;
  isDragOver?: boolean;
  onRefresh?: () => void;
  onRemove?: () => void;
}) {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  
  // Fixed height for all widgets
  const FIXED_WIDGET_HEIGHT = 320;

  const handleMenuAction = (action: string) => {
    setOpen(false);
    if (action === 'Refresh' && onRefresh) {
      onRefresh();
    } else if (action === 'Remove widget' && onRemove) {
      onRemove();
    } else if (action === 'View details' && detailHref) {
      router.push(detailHref);
    }
  };

  return (
    <div
      className={'flex flex-col relative ' + className}
      style={{
        height: FIXED_WIDGET_HEIGHT + 'px',
        backgroundColor: 'var(--bg-surface)',
        border: isDragOver ? '2px dashed var(--accent)' : '1px solid var(--border-default)',
        borderRadius: '8px',
        transition: 'border-color 0.1s',
      }}
      onDragOver={e => { e.preventDefault(); onDragOver?.(e); }}
      onDrop={() => onDrop?.(id)}
    >
      <div
        className="flex items-center justify-between px-4 py-2.5 border-b flex-shrink-0"
        style={{ borderColor: 'var(--border-faint)', minHeight: '44px' }}
      >
        <div className="flex items-center gap-1.5 min-w-0">
          <span
            className="flex-shrink-0 select-none"
            style={{ color: 'var(--text-tertiary)', fontSize: '14px', lineHeight: 1, letterSpacing: '-1px', cursor: 'grab' }}
            draggable
            onDragStart={e => { e.dataTransfer.effectAllowed = 'move'; onDragStart?.(id); }}
            title="Drag to reorder"
          >
            &#10307;&#10307;
          </span>
          <span className="text-sm font-bold truncate" style={{ color: 'var(--text-primary)' }}>{title}</span>
          {infoHref && (
            <a href={infoHref} style={{ color: 'var(--text-link)', fontSize: '12px', marginLeft: '4px', textDecoration: 'none' }}
              onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
              onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
            >Info</a>
          )}
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {actions}
          <div className="relative">
            <button
              onClick={() => setOpen(o => !o)}
              className="flex h-6 w-6 items-center justify-center rounded transition-colors"
              style={{ color: 'var(--text-tertiary)' }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
            >
              <MoreVertical className="h-4 w-4" />
            </button>
            {open && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
                <div className="absolute right-0 top-full z-50 mt-1 w-44 py-1" style={{ backgroundColor: 'var(--bg-overlay)', border: '1px solid var(--border-default)', boxShadow: 'var(--shadow-popover)', borderRadius: '8px' }}>
                  {['Refresh', 'Remove widget', 'View details'].map(item => (
                    <button 
                      key={item} 
                      onClick={() => handleMenuAction(item)} 
                      className="w-full px-3 py-1.5 text-left text-sm transition-colors flex items-center gap-2" 
                      style={{ color: 'var(--text-primary)' }}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      {item === 'Refresh' && <RefreshCw className="h-3.5 w-3.5" />}
                      {item === 'Remove widget' && <X className="h-3.5 w-3.5" />}
                      {item === 'View details' && <ExternalLink className="h-3.5 w-3.5" />}
                      {item}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Widget body with overflow handling */}
      <div className="flex-1 overflow-auto" style={{ minHeight: 0 }}>
        <div className="p-4 h-full">
          {children}
        </div>
      </div>
    </div>
  );
}

function ServiceTile({ label, href, icon, color, iconComponent }: { label: string; href: string; icon?: string; color: string; iconComponent?: React.ReactNode }) {
  return (
    <Link href={href} className="flex items-center gap-2.5 py-2 border-b text-sm transition-colors"
      style={{ borderColor: 'var(--border-faint)', color: 'var(--text-link)', textDecoration: 'none' }}
      onMouseEnter={e => { (e.currentTarget.style.textDecoration = 'underline'); }}
      onMouseLeave={e => { (e.currentTarget.style.textDecoration = 'none'); }}
    >
      {iconComponent ? (
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center" style={{ color }}>
          {iconComponent}
        </span>
      ) : (
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center text-xs font-bold text-white" style={{ backgroundColor: color, borderRadius: '4px' }}>{icon}</span>
      )}
      <span className="truncate">{label}</span>
    </Link>
  );
}

export default function ConsolePage() {
  // Set browser tab title
  React.useEffect(() => {
    document.title = 'Home Console - CloudVisor';
  }, []);

  return (
    <ProtectedRoute>
      <AppLayout>
        <ConsoleGrid />
      </AppLayout>
    </ProtectedRoute>
  );
}


// ─── Console Grid with new widgets ────────────────────────────────────────────

function ConsoleGrid() {
  const widgetOrder = useUserSettings(s => s.widgetOrder);
  const removedWidgets = useUserSettings(s => s.removedWidgets);
  const setWidgetOrder = useUserSettings(s => s.setWidgetOrder);
  const removeWidget = useUserSettings(s => s.removeWidget);
  const restoreWidget = useUserSettings(s => s.restoreWidget);
  const resetLayout = useUserSettings(s => s.resetLayout);
  
  // Real data hooks
  const { data: dashboardStats, isLoading: statsLoading, refetch: refetchStats } = useDashboardStats();
  const { data: modulesSummary, isLoading: modulesLoading, refetch: refetchModules } = useModulesSummary();
  const { data: recentActivity, isLoading: activityLoading, refetch: refetchActivity } = useDashboardActivity(5);
  const { data: accountsData, isLoading: accountsLoading } = useDashboardAccounts();
  const { data: resourcesData, isLoading: resourcesLoading } = useDashboardResources();
  const { items: recentlyVisitedItems, clearRecentlyVisited, manualTrackVisit } = useRecentlyVisited();
  const { services: serviceHealthData, isLoading: healthLoading, refetch: refetchHealth } = useServiceHealth();
  
  const [dragId, setDragId] = React.useState<string | null>(null);
  const [overId, setOverId] = React.useState<string | null>(null);
  const [showAddWidgets, setShowAddWidgets] = React.useState(false);

  const handleDragStart = (id: string) => setDragId(id);
  const handleDragOver = (id: string) => setOverId(id);
  const handleDrop = (targetId: string) => {
    if (!dragId || dragId === targetId) { setDragId(null); setOverId(null); return; }
    const newOrder = [...widgetOrder];
    const fromIdx = newOrder.indexOf(dragId);
    const toIdx = newOrder.indexOf(targetId);
    if (fromIdx === -1 || toIdx === -1) { setDragId(null); setOverId(null); return; }
    newOrder.splice(fromIdx, 1);
    newOrder.splice(toIdx, 0, dragId);
    setWidgetOrder(newOrder);
    setDragId(null);
    setOverId(null);
  };

  const wProps = (id: string) => ({
    id,
    onDragStart: handleDragStart,
    onDragOver: () => handleDragOver(id),
    onDrop: handleDrop,
    isDragOver: overId === id && dragId !== id,
  });

  const services = [
    { label: 'Findings', href: '/findings', color: 'var(--critical)', iconComponent: <Shield size={16} /> },
    { label: 'Assets', href: '/assets', color: 'var(--success)', iconComponent: <Server size={16} /> },
    { label: 'CSPM', href: '/cspm', color: 'var(--accent)', iconComponent: <Shield size={16} /> },
    { label: 'CWPP', href: '/cwpp', color: 'var(--high)', iconComponent: <Server size={16} /> },
    { label: 'Identity (CIEM)', href: '/ciem', color: '#6b2fa0', iconComponent: <Key size={16} /> },
    { label: 'Kubernetes (KSPM)', href: '/kspm', color: '#326ce5', iconComponent: <Cloud size={16} /> },
    { label: 'Data (DSPM)', href: '/dspm', color: 'var(--success)', iconComponent: <Database size={16} /> },
    { label: 'Detection (CDR)', href: '/cdr', color: 'var(--critical)', iconComponent: <Activity size={16} /> },
  ];

  const modules = [
    { label: 'CSPM', href: '/cspm', color: 'var(--accent)', icon: 'CSPM' },
    { label: 'CWPP', href: '/cwpp', color: 'var(--high)', icon: 'CWPP' },
    { label: 'CIEM', href: '/ciem', color: '#6b2fa0', icon: 'CIEM' },
    { label: 'KSPM', href: '/kspm', color: '#326ce5', icon: 'KSPM' },
    { label: 'DSPM', href: '/dspm', color: 'var(--success)', icon: 'DSPM' },
    { label: 'CDR', href: '/cdr', color: 'var(--critical)', icon: 'CDR' },
    { label: 'CI/CD', href: '/cicd', color: 'var(--warning)', icon: 'CI/CD' },
    { label: 'AIOps', href: '/aiops', color: 'var(--accent)', icon: 'AIOps' },
  ];

  const widgetRefreshHandlers: Record<string, () => void> = {
    'recently-visited': () => {}, // Recently visited is automatically updated
    'cloudvisor-health': () => refetchHealth(),
    'cost-usage': () => {},
    'welcome': () => {},
    'solutions': () => {},
    'explore': () => {},
    'announcements': () => refetchActivity(),
  };

  const widgetDetailRoutes: Record<string, string> = {
    'recently-visited': '/services',
    'cloudvisor-health': '/settings',
    'cost-usage': '/billing',
    'welcome': '#',
    'solutions': '#',
    'explore': '#',
    'announcements': '#',
  };

  const widgetMap: Record<string, React.ReactNode> = {
    'recently-visited': (
      <Widget 
        key="recently-visited" 
        {...wProps('recently-visited')} 
        title="Recently visited" 
        infoHref="#" 
        detailHref={widgetDetailRoutes['recently-visited']}
        onRefresh={widgetRefreshHandlers['recently-visited']}
        onRemove={() => removeWidget('recently-visited')}
      >
        {(() => {
          return recentlyVisitedItems.length > 0 ? (
            <div className="grid grid-cols-2 gap-x-6 h-full">
              <div className="overflow-auto">
                {recentlyVisitedItems.slice(0, 4).map((item) => (
                  <ServiceTile 
                    key={item.href} 
                    label={item.label}
                    href={item.href}
                    color={item.color || 'var(--accent)'}
                    iconComponent={
                      <Shield size={16} style={{ color: item.color || 'var(--accent)' }} />
                    }
                  />
                ))}
              </div>
              <div className="overflow-auto">
                {recentlyVisitedItems.slice(4, 8).map((item) => (
                  <ServiceTile 
                    key={item.href} 
                    label={item.label}
                    href={item.href}
                    color={item.color || 'var(--accent)'}
                    iconComponent={
                      <Shield size={16} style={{ color: item.color || 'var(--accent)' }} />
                    }
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center p-4">
                <BookOpen className="h-12 w-12 mx-auto mb-2" style={{ color: 'var(--text-tertiary)' }} />
                <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>No recent visits</p>
                <p className="text-xs mb-3" style={{ color: 'var(--text-secondary)' }}>
                  Visit CloudVisor services to see them here
                </p>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  {services.slice(0, 4).map((s: any) => (
                    <Link 
                      key={s.href} 
                      href={s.href} 
                      className="p-2 rounded transition-colors text-center"
                      style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-link)' }}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                      onClick={() => {
                        console.log('Clicking service link:', s.href);
                        setTimeout(() => manualTrackVisit(s.href), 100);
                      }}
                    >
                      {s.label}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          );
        })()}
      </Widget>
    ),
    'cloudvisor-health': (
      <Widget 
        key="cloudvisor-health" 
        {...wProps('cloudvisor-health')} 
        title="CloudVisor Health" 
        infoHref="#"
        detailHref={widgetDetailRoutes['cloudvisor-health']}
        onRefresh={widgetRefreshHandlers['cloudvisor-health']}
        onRemove={() => removeWidget('cloudvisor-health')}
      >
        <div className="space-y-3 h-full overflow-auto">
          {healthLoading ? (
            // Loading skeleton
            Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between text-sm p-2 rounded" style={{ backgroundColor: 'var(--bg-elevated)' }}>
                <div className="flex items-center gap-2">
                  <Sk w="w-5" h="h-5" />
                  <Sk w="w-16" h="h-4" />
                </div>
                <Sk w="w-20" h="h-4" />
              </div>
            ))
          ) : serviceHealthData && serviceHealthData.length > 0 ? (
            // Real service health data
            serviceHealthData.map((service) => {
              const getStatusColor = (status: string) => {
                switch (status) {
                  case 'healthy': return 'var(--success)';
                  case 'degraded': return 'var(--warning)';
                  case 'down': return 'var(--critical)';
                  default: return 'var(--text-tertiary)';
                }
              };
              
              const getStatusText = (status: string, responseTime?: number) => {
                switch (status) {
                  case 'healthy': return 'Operational';
                  case 'degraded': return `Slow (${responseTime}ms)`;
                  case 'down': return 'Offline';
                  default: return 'Unknown';
                }
              };
              
              const statusColor = getStatusColor(service.status);
              const statusText = getStatusText(service.status, service.responseTime);
              
              return (
                <div key={service.name} className="flex items-center justify-between text-sm p-2 rounded transition-colors"
                  style={{ backgroundColor: 'var(--bg-elevated)' }}
                >
                  <div className="flex items-center gap-2">
                    <span style={{ color: service.color }}>
                      <ModuleIcon module={service.icon} size={18} />
                    </span>
                    <span style={{ color: 'var(--text-primary)' }}>{service.label}</span>
                  </div>
                  <span className="flex items-center gap-1.5" style={{ color: statusColor }}>
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: statusColor }} />
                    <span className="text-xs">{statusText}</span>
                  </span>
                </div>
              );
            })
          ) : (
            // Fallback to static data when health check fails
            modules.map(m => (
              <div key={m.label} className="flex items-center justify-between text-sm p-2 rounded transition-colors"
                style={{ backgroundColor: 'var(--bg-elevated)' }}
              >
                <div className="flex items-center gap-2">
                  <span style={{ color: m.color }}>
                    <ModuleIcon module={m.icon} size={18} />
                  </span>
                  <span style={{ color: 'var(--text-primary)' }}>{m.label}</span>
                </div>
                <span className="flex items-center gap-1.5" style={{ color: 'var(--text-tertiary)' }}>
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: 'var(--text-tertiary)' }} />
                  <span className="text-xs">Unknown</span>
                </span>
              </div>
            ))
          )}
        </div>
      </Widget>
    ),
    'cost-usage': (
      <Widget 
        key="cost-usage" 
        {...wProps('cost-usage')} 
        title="Cost and usage" 
        infoHref="#"
        detailHref={widgetDetailRoutes['cost-usage']}
        onRefresh={widgetRefreshHandlers['cost-usage']}
        onRemove={() => removeWidget('cost-usage')}
      >
        <div className="h-full flex flex-col">
          <div className="mb-4">
            <div className="text-3xl font-bold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
              {resourcesLoading ? (
                <Sk w="w-20" h="h-8" />
              ) : resourcesData?.total_resources ? (
                `${resourcesData.total_resources.toLocaleString()} resources`
              ) : (
                '$0.00'
              )}
            </div>
            <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {resourcesData?.total_resources ? 'Total resources monitored' : 'Current month'}
            </div>
          </div>
          <div className="flex-1 flex items-center justify-center" style={{ backgroundColor: 'var(--bg-elevated)', borderRadius: '8px' }}>
            <div className="text-center p-4">
              {resourcesLoading ? (
                <div className="space-y-2">
                  <Sk w="w-12 h-12 mx-auto" h="h-12" />
                  <Sk w="w-32" h="h-4" />
                </div>
              ) : resourcesData?.accounts && resourcesData.accounts.length > 0 ? (
                <div className="space-y-2">
                  <Cloud className="h-12 w-12 mx-auto mb-2" style={{ color: 'var(--accent)' }} />
                  <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {resourcesData.accounts.length} account{resourcesData.accounts.length !== 1 ? 's' : ''} connected
                  </p>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {resourcesData.total_resources?.toLocaleString() || 0} resources across {resourcesData.providers?.join(', ') || 'cloud providers'}
                  </p>
                </div>
              ) : (
                <div>
                  <DollarSign className="h-12 w-12 mx-auto mb-2" style={{ color: 'var(--text-tertiary)' }} />
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No cost data available</p>
                  <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>Connect cloud accounts to see usage metrics</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </Widget>
    ),
    'welcome': (
      <Widget 
        key="welcome" 
        {...wProps('welcome')} 
        title="Welcome to CloudVisor" 
        infoHref="#"
        detailHref={widgetDetailRoutes['welcome']}
        onRefresh={widgetRefreshHandlers['welcome']}
        onRemove={() => removeWidget('welcome')}
      >
        <div className="h-full flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
              Get started with CloudVisor
            </h3>
            <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
              Secure your cloud infrastructure with comprehensive security posture management
            </p>
            {accountsLoading ? (
              <div className="space-y-2">
                <Sk w="w-full" h="h-4" />
                <Sk w="w-3/4" h="h-3" />
              </div>
            ) : accountsData?.accounts && accountsData.accounts.length > 0 ? (
              <div className="mb-4 p-3 rounded" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--success)' }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: 'var(--success)' }} />
                  <span className="text-sm font-semibold" style={{ color: 'var(--success)' }}>
                    {accountsData.accounts.length} account{accountsData.accounts.length !== 1 ? 's' : ''} connected
                  </span>
                </div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  Your cloud infrastructure is being monitored
                </p>
              </div>
            ) : null}
          </div>
          <div className="space-y-2">
            {!accountsData?.accounts || accountsData.accounts.length === 0 ? (
              <Link href="/settings" className="block p-3 rounded border transition-colors"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
              >
                <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Connect your cloud accounts</div>
                <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Start monitoring your infrastructure</div>
              </Link>
            ) : (
              <Link href="/findings" className="block p-3 rounded border transition-colors"
                style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
              >
                <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>View security findings</div>
                <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Review and remediate security issues</div>
              </Link>
            )}
          </div>
        </div>
      </Widget>
    ),
    'solutions': (
      <Widget 
        key="solutions" 
        {...wProps('solutions')} 
        title="Solutions" 
        infoHref="#"
        detailHref={widgetDetailRoutes['solutions']}
        onRefresh={widgetRefreshHandlers['solutions']}
        onRemove={() => removeWidget('solutions')}
      >
        <div className="h-full overflow-auto space-y-3">
          {[
            { title: 'Cloud Security Posture', desc: 'Continuous compliance monitoring', href: '/cspm', icon: <Shield size={16} /> },
            { title: 'Workload Protection', desc: 'Runtime security for containers', href: '/cwpp', icon: <Server size={16} /> },
            { title: 'Identity Management', desc: 'Least privilege access control', href: '/ciem', icon: <Key size={16} /> },
          ].map((solution, i) => (
            <Link key={i} href={solution.href} className="block p-3 rounded border transition-colors"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
            >
              <div className="flex items-start gap-2">
                <span style={{ color: 'var(--accent)' }}>{solution.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{solution.title}</div>
                  <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{solution.desc}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </Widget>
    ),
    'explore': (
      <Widget 
        key="explore" 
        {...wProps('explore')} 
        title="Explore CloudVisor" 
        infoHref="#"
        detailHref={widgetDetailRoutes['explore']}
        onRefresh={widgetRefreshHandlers['explore']}
        onRemove={() => removeWidget('explore')}
      >
        <div className="h-full overflow-auto space-y-3">
          {[
            { title: 'Documentation', icon: <BookOpen size={16} />, href: '#' },
            { title: 'Tutorials', icon: <Compass size={16} />, href: '#' },
            { title: 'API Reference', icon: <Terminal size={16} />, href: '#' },
            { title: 'Best Practices', icon: <TrendingUp size={16} />, href: '#' },
          ].map((item, i) => (
            <Link key={i} href={item.href} className="flex items-center gap-3 p-2 rounded transition-colors"
              style={{ backgroundColor: 'var(--bg-elevated)' }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
            >
              <span style={{ color: 'var(--accent)' }}>{item.icon}</span>
              <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{item.title}</span>
            </Link>
          ))}
        </div>
      </Widget>
    ),
    'announcements': (
      <Widget 
        key="announcements" 
        {...wProps('announcements')} 
        title="Latest announcements" 
        infoHref="#"
        detailHref={widgetDetailRoutes['announcements']}
        onRefresh={widgetRefreshHandlers['announcements']}
        onRemove={() => removeWidget('announcements')}
      >
        <div className="h-full overflow-auto space-y-3">
          {activityLoading ? (
            // Loading skeleton
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="p-3 rounded border" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
                <div className="flex items-start gap-3">
                  <Sk w="w-10" h="h-4" />
                  <div className="flex-1 space-y-2">
                    <Sk w="w-3/4" h="h-4" />
                    <Sk w="w-full" h="h-3" />
                  </div>
                </div>
              </div>
            ))
          ) : recentActivity && Array.isArray(recentActivity) && recentActivity.length > 0 ? (
            // Real activity data
            recentActivity.slice(0, 3).map((activity: any, i: number) => {
              const date = activity.created_at ? new Date(activity.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Recent';
              const title = activity.title || activity.description || activity.event_type || 'System Activity';
              const description = activity.details || activity.message || 'CloudVisor system activity';
              
              return (
                <div key={activity.id || i} className="p-3 rounded border" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 text-center" style={{ width: '40px' }}>
                      <div className="text-xs font-bold" style={{ color: 'var(--text-tertiary)' }}>{date}</div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{title}</div>
                      <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{description}</div>
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            // Fallback to static announcements when no real data
            [
              { date: 'May 9', title: 'CloudVisor Q AI Assistant', desc: 'New AI-powered security assistant available' },
              { date: 'May 7', title: 'Enhanced CSPM features', desc: 'Improved compliance monitoring and reporting' },
              { date: 'May 5', title: 'Multi-cloud support expanded', desc: 'Added support for additional cloud providers' },
            ].map((item, i) => (
              <div key={i} className="p-3 rounded border" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}>
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 text-center" style={{ width: '40px' }}>
                    <div className="text-xs font-bold" style={{ color: 'var(--text-tertiary)' }}>{item.date}</div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{item.title}</div>
                    <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{item.desc}</div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </Widget>
    ),
  };

  const visibleWidgets = widgetOrder.filter(id => !removedWidgets.includes(id));

  const widgetNames: Record<string, string> = {
    'recently-visited': 'Recently Visited',
    'cloudvisor-health': 'CloudVisor Health',
    'cost-usage': 'Cost and Usage',
    'welcome': 'Welcome to CloudVisor',
    'solutions': 'Solutions',
    'explore': 'Explore CloudVisor',
    'announcements': 'Latest Announcements',
  };

  const handleResetLayout = () => {
    resetLayout();
    // Force a re-render by updating state
    window.location.reload();
  };

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold sm:text-2xl" style={{ color: 'var(--text-primary)' }}>Home Console</h1>
          <a href="#" style={{ color: 'var(--text-link)', fontSize: '12px', textDecoration: 'none' }}
            onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
            onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
          >Info</a>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleResetLayout}
            className="flex items-center gap-1.5 text-xs sm:text-sm transition-colors"
            style={{ height: '30px', padding: '0 10px', backgroundColor: 'var(--btn-normal-bg)', color: 'var(--text-link)', border: '1px solid var(--text-link)', borderRadius: '4px', cursor: 'pointer', whiteSpace: 'nowrap' }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--btn-normal-hover)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--btn-normal-bg)')}
          >
            <RotateCcw className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
            <span className="hidden sm:inline">Reset to default layout</span>
            <span className="sm:hidden">Reset</span>
          </button>
          <button
            onClick={() => setShowAddWidgets(true)}
            disabled={removedWidgets.length === 0}
            className="flex items-center gap-1.5 text-xs sm:text-sm font-bold transition-colors disabled:opacity-50"
            style={{ height: '30px', padding: '0 10px', backgroundColor: 'var(--btn-primary-bg)', color: 'var(--btn-primary-text)', border: '1px solid var(--btn-primary-bg)', borderRadius: '4px', cursor: removedWidgets.length === 0 ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap' }}
            onMouseEnter={e => { if (removedWidgets.length > 0) (e.currentTarget.style.backgroundColor = 'var(--btn-primary-hover)'); }}
            onMouseLeave={e => { if (removedWidgets.length > 0) (e.currentTarget.style.backgroundColor = 'var(--btn-primary-bg)'); }}
          >
            <Plus className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
            <span className="hidden sm:inline">Add widgets {removedWidgets.length > 0 && `(${removedWidgets.length})`}</span>
            <span className="sm:hidden">Add {removedWidgets.length > 0 && `(${removedWidgets.length})`}</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 console-grid">
        {visibleWidgets.map(id => widgetMap[id] ?? null)}
      </div>

      {showAddWidgets && (
        <>
          <div className="fixed inset-0 z-50 bg-black/50" onClick={() => setShowAddWidgets(false)} />
          <div className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 p-6" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '16px', boxShadow: 'var(--shadow-modal)' }}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Add widgets</h2>
              <button onClick={() => setShowAddWidgets(false)} className="flex h-8 w-8 items-center justify-center rounded transition-colors" style={{ color: 'var(--text-tertiary)' }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="space-y-2">
              {removedWidgets.length === 0 ? (
                <div className="py-8 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
                  All widgets are currently visible
                </div>
              ) : (
                removedWidgets.map(id => (
                  <button
                    key={id}
                    onClick={() => { restoreWidget(id); setShowAddWidgets(false); }}
                    className="w-full rounded border p-3 text-left transition-colors"
                    style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
                  >
                    <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {widgetNames[id] || id.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                    </div>
                    <div className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                      Click to restore this widget
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
