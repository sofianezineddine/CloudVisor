'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './sidebar';
import { Header, Bar3, STICKY_HEADER_H, BAR3_H, BOTTOM_BAR_H } from './header';
import { Flashbar, FlashbarItem } from '@/components/ui/flashbar';
import { X } from 'lucide-react';
import { useScopeStore, isGlobalRoute } from '@/stores/scope';
import { usePathname } from 'next/navigation';
import { useCloudVisorQStore } from '@/stores/cloudvisor-q';
import { CloudVisorQPanel } from '@/components/ui/cloudvisor-q-panel';

// ─── Module-level sidebar state ───────────────────────────────────────────────
let _sidebarOpen: boolean | null = null;

function getInitialSidebarOpen(): boolean {
  // Always start with sidebar closed as default
  return false;
}

// ─── Scope context badge — shown below page title on scope-aware pages ────────
function ScopeContextBadge() {
  const mode = useScopeStore(s => s.mode);
  const label = useScopeStore(s => s.label);
  const accountIds = useScopeStore(s => s.accountIds);

  // Don't show if no accounts loaded yet
  if (accountIds.length === 0) return null;

  return (
    <div
      className="mb-3 inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs"
      style={{
        backgroundColor: 'rgba(236,114,17,0.08)',
        border: '1px solid rgba(236,114,17,0.25)',
        color: '#ec7211',
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: '#ec7211' }} />
      <span>
        Viewing: <strong>
          {mode === 'provider' ? `${label} (all accounts)` : label}
        </strong>
      </span>
    </div>
  );
}

// ─── Scope badge wrapper — only renders on scope-aware pages ─────────────────
// Removed per design decision — scope is shown in the header selector only
function ScopeBadgeIfNeeded() {
  return null; // Badge removed — scope visible in top nav selector
}

//  Bottom status bar 
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

//  AppLayout props 
export interface AppLayoutProps {
  children: React.ReactNode;
  breadcrumbs?: { text: string; href?: string }[];
  flashbarItems?: FlashbarItem[];
  splitPanelContent?: React.ReactNode;
  splitPanelHeader?: string;
  splitPanelOpen?: boolean;
  onSplitPanelClose?: () => void;
  // CSPM sidebar tab support
  cspmActiveTab?: string;
  onCspmTabChange?: (tab: string) => void;
}

//  AppLayout 
export function AppLayout({
  children,
  breadcrumbs,
  flashbarItems,
  splitPanelContent,
  cspmActiveTab,
  splitPanelHeader,
  splitPanelOpen,
  onSplitPanelClose,
  onCspmTabChange,
}: AppLayoutProps) {
  const pathname = usePathname();

  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    if (_sidebarOpen !== null) return _sidebarOpen;
    const open = getInitialSidebarOpen();
    _sidebarOpen = open;
    return open;
  });

  // Open sidebar automatically when a service tab is active
  // (i.e. when we are inside a service page — not on the console/home)
  React.useEffect(() => {
    const isServicePage = pathname !== '/console' && pathname !== '/' && pathname !== '/services';
    if (isServicePage && !_sidebarOpen) {
      setSidebarOpen(true);
      _sidebarOpen = true;
    }
  }, [pathname]);

  // Get Q panel state
  const qPanelOpen = useCloudVisorQStore((state) => state.isOpen);
  const qPanelWidth = useCloudVisorQStore((state) => state.width);
  const qPanelMaximized = useCloudVisorQStore((state) => state.isMaximized);

  // Determine if panel should be treated as fullscreen based on width
  const [isQPanelFullscreen, setIsQPanelFullscreen] = useState(false);

  // Hydrate Zustand persist store on client side
  useEffect(() => {
    if (typeof window !== 'undefined') {
      useCloudVisorQStore.persist.rehydrate();
    }
  }, []);

  // Update fullscreen state based on panel width
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    if (qPanelOpen) {
      const widthPercentage = (qPanelWidth / window.innerWidth) * 100;
      setIsQPanelFullscreen(qPanelMaximized || widthPercentage >= 90);
    } else {
      setIsQPanelFullscreen(false);
    }
  }, [qPanelOpen, qPanelWidth, qPanelMaximized]);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen(prev => {
      const next = !prev;
      _sidebarOpen = next;
      return next;
    });
  }, []);

  useEffect(() => {
    const handler = () => {
      if (window.innerWidth < 768 && sidebarOpen) {
        setSidebarOpen(false);
        _sidebarOpen = false;
      }
    };
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, [sidebarOpen]);

  const showSplitPanel = splitPanelOpen && splitPanelContent;

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-base)' }}>

      {/*  Bars 1 + 2 — sticky header (full width) */}
      <Header
        onSidebarToggle={toggleSidebar}
        breadcrumbs={breadcrumbs}
        sidebarOpen={sidebarOpen}
        activeTab={cspmActiveTab}
      />

      {/*  Body row: Q panel + (Bar 3 + Sidebar + Content)  */}
      <div
        className="flex w-full"
        style={{
          minHeight: `calc(100vh - ${STICKY_HEADER_H}px - ${BOTTOM_BAR_H}px)`,
        }}
      >
        {/* CloudVisor Q Panel - at the same level as content */}
        {qPanelOpen && (
          <div
            className="flex-shrink-0"
            style={{
              width: qPanelMaximized ? '100vw' : `${qPanelWidth}px`,
              position: 'sticky',
              top: `${STICKY_HEADER_H}px`,
              height: `calc(100vh - ${STICKY_HEADER_H}px - ${BOTTOM_BAR_H}px)`,
              overflowY: 'auto',
              zIndex: 30,
            }}
          >
            <CloudVisorQPanel />
          </div>
        )}

        {/* Main content area with Bar 3 - always visible, adjusts when Q panel is open */}
        <div 
          className="flex flex-col min-w-0" 
          style={{ 
            display: qPanelMaximized ? 'none' : 'flex',
            flex: 1,
            width: qPanelOpen && !qPanelMaximized 
              ? `calc(100vw - ${qPanelWidth}px)` 
              : '100%',
          }}
        >
          {/* Bar 3 - moves with content */}
          <Bar3 onSidebarToggle={toggleSidebar} breadcrumbs={breadcrumbs} activeTab={cspmActiveTab} />

          {/* Content row: Sidebar + Main content */}
          <div className="flex flex-1">
            {/*  Sidebar  sticky so it stays attached to bar 3  */}
            {sidebarOpen && (
              <>
                {/* Mobile backdrop — covers content behind the full-width sidebar */}
                <div
                  className="fixed inset-0 z-20 md:hidden"
                  style={{ top: `${STICKY_HEADER_H + BAR3_H}px`, backgroundColor: 'rgba(0,0,0,0.5)' }}
                  onClick={() => { setSidebarOpen(false); _sidebarOpen = false; }}
                />
                {/* Sidebar panel — full width on mobile, fixed 220px on desktop */}
                <div
                  className="flex-shrink-0"
                  style={{
                    position: 'sticky',
                    top: `${STICKY_HEADER_H + BAR3_H}px`,
                    height: `calc(100vh - ${STICKY_HEADER_H + BAR3_H}px - ${BOTTOM_BAR_H}px)`,
                    overflowY: 'auto',
                    zIndex: 20,
                  }}
                  // On mobile: fixed full-width overlay; on md+: sticky 220px inline
                >
                  {/* Mobile: fixed full-width overlay */}
                  <div className="md:hidden fixed left-0 right-0 z-20 overflow-y-auto"
                    style={{
                      top: `${STICKY_HEADER_H + BAR3_H}px`,
                      height: `calc(100vh - ${STICKY_HEADER_H + BAR3_H}px - ${BOTTOM_BAR_H}px)`,
                    }}
                  >
                    <Sidebar
                      onClose={() => { setSidebarOpen(false); _sidebarOpen = false; }}
                      cspmActiveTab={cspmActiveTab}
                      onCspmTabChange={onCspmTabChange}
                    />
                  </div>
                  {/* Desktop: inline sticky 220px */}
                  <div className="hidden md:block" style={{ width: '220px', height: '100%' }}>
                    <Sidebar
                      onClose={() => { setSidebarOpen(false); _sidebarOpen = false; }}
                      cspmActiveTab={cspmActiveTab}
                      onCspmTabChange={onCspmTabChange}
                    />
                  </div>
                </div>
              </>
            )}

            {/*  Main content  */}
            <div
              className="flex flex-col flex-1 min-w-0"
              style={{ paddingBottom: BOTTOM_BAR_H + 'px' }}
            >
              {/* Flashbar */}
              {flashbarItems && flashbarItems.length > 0 && (
                <div className="px-4 pt-2">
                  <Flashbar items={flashbarItems} />
                </div>
              )}

              {/* Page content — small top padding before page title */}
              <main className="flex-1 pt-3 pb-2" style={{ minWidth: 0, width: '100%' }}>
                <div className="content-wrapper">
                  <ScopeBadgeIfNeeded />
                  {children}
                </div>
              </main>

              {/* Split panel */}
              {showSplitPanel && (
                <div className="flex-shrink-0 border-t" style={{ height: '360px', backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border-default)' }}>
                  <div className="flex h-10 items-center justify-between border-b px-5" style={{ borderColor: 'var(--border-faint)' }}>
                    <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{splitPanelHeader ?? 'Details'}</span>
                    <button onClick={onSplitPanelClose} className="flex h-7 w-7 items-center justify-center rounded transition-colors" style={{ color: 'var(--text-tertiary)' }}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="h-[calc(360px-40px)] overflow-y-auto p-5">{splitPanelContent}</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/*  Bottom bar  */}
      <BottomBar />
    </div>
  );
}