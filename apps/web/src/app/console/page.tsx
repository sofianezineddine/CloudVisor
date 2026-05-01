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
        border: isDragOver ? '2px dashed #0972d3' : '1px solid var(--border-default)',
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
  const accountIds = useScopeStore(s => s.accountIds);

  // Set browser tab title
  React.useEffect(() => {
    document.title = 'Home Console - CloudVisor';
  }, []);

  return (
    <ProtectedRoute>
      <AppLayout breadcrumbs={[{ text: 'Home Console' }]}>
        {accountIds.length === 0 ? (
          <NoAccountsConnectedEmptyState />
        ) : (
          <ConsoleGrid />
        )}
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
    { label: 'Findings', href: '/findings', color: '#d13212', iconComponent: <Shield size={16} /> },
    { label: 'Assets', href: '/assets', color: '#1a6b3c', iconComponent: <Server size={16} /> },
    { label: 'CSPM', href: '/cspm', color: '#0073bb', iconComponent: <Shield size={16} /> },
    { label: 'CWPP', href: '/cwpp', color: '#d45b07', iconComponent: <Server size={16} /> },
    { label: 'Identity (CIEM)', href: '/ciem', color: '#6b2fa0', iconComponent: <Key size={16} /> },
    { label: 'Kubernetes (KSPM)', href: '/kspm', color: '#326ce5', iconComponent: <Cloud size={16} /> },
    { label: 'Data (DSPM)', href: '/dspm', color: '#1a6b3c', iconComponent: <Database size={16} /> },
    { label: 'Detection (CDR)', href: '/cdr', color: '#d13212', iconComponent: <Activity size={16} /> },
  ];

  const modules = [
    { label: 'CSPM', href: '/cspm', color: '#0073bb', icon: 'CSPM' },
    { label: 'CWPP', href: '/cwpp', color: '#d45b07', icon: 'CWPP' },
    { label: 'CIEM', href: '/ciem', color: '#6b2fa0', icon: 'CIEM' },
    { label: 'KSPM', href: '/kspm', color: '#326ce5', icon: 'KSPM' },
    { label: 'DSPM', href: '/dspm', color: '#1a6b3c', icon: 'DSPM' },
    { label: 'CDR', href: '/cdr', color: '#d13212', icon: 'CDR' },
    { label: 'CI/CD', href: '/cicd', color: '#8d6605', icon: 'CI/CD' },
    { label: 'AIOps', href: '/aiops', color: '#0073bb', icon: 'AIOps' },
  ];

  const widgetRefreshHandlers: Record<string, () => void> = {
    'recently-visited': () => {},
    'cloudvisor-health': () => {},
    'cost-usage': () => {},
    'welcome': () => {},
    'solutions': () => {},
    'explore': () => {},
    'announcements': () => {},
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
        <div className="grid grid-cols-2 gap-x-6 h-full">
          <div className="overflow-auto">{services.slice(0, 4).map((s: any) => <ServiceTile key={s.href} {...s} />)}</div>
          <div className="overflow-auto">{services.slice(4).map((s: any) => <ServiceTile key={s.href} {...s} />)}</div>
        </div>
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
          {modules.map(m => (
            <div key={m.label} className="flex items-center justify-between text-sm p-2 rounded transition-colors"
              style={{ backgroundColor: 'var(--bg-elevated)' }}
            >
              <div className="flex items-center gap-2">
                <span style={{ color: m.color }}>
                  <ModuleIcon module={m.icon} size={18} />
                </span>
                <span style={{ color: 'var(--text-primary)' }}>{m.label}</span>
              </div>
              <span className="flex items-center gap-1.5" style={{ color: 'var(--success)' }}>
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: 'var(--success)' }} />
                <span className="text-xs">Operational</span>
              </span>
            </div>
          ))}
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
              $0.00
            </div>
            <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>Current month</div>
          </div>
          <div className="flex-1 flex items-center justify-center" style={{ backgroundColor: 'var(--bg-elevated)', borderRadius: '8px' }}>
            <div className="text-center p-4">
              <DollarSign className="h-12 w-12 mx-auto mb-2" style={{ color: 'var(--text-tertiary)' }} />
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No cost data available</p>
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
          </div>
          <div className="space-y-2">
            <Link href="/settings" className="block p-3 rounded border transition-colors"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)' }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
            >
              <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Connect your cloud accounts</div>
              <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Start monitoring your infrastructure</div>
            </Link>
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
          {[
            { date: 'Apr 26', title: 'New CSPM features released', desc: 'Enhanced compliance monitoring' },
            { date: 'Apr 24', title: 'CloudVisor 2.0 is here', desc: 'Major platform update' },
            { date: 'Apr 22', title: 'Security best practices guide', desc: 'New documentation available' },
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
          ))}
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
            style={{ height: '30px', padding: '0 10px', backgroundColor: '#ff9900', color: '#ffffff', border: '1px solid #ff9900', borderRadius: '4px', cursor: removedWidgets.length === 0 ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap' }}
            onMouseEnter={e => { if (removedWidgets.length > 0) (e.currentTarget.style.backgroundColor = '#ec7211'); }}
            onMouseLeave={e => { if (removedWidgets.length > 0) (e.currentTarget.style.backgroundColor = '#ff9900'); }}
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
