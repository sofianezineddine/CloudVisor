'use client';

import React, { useState, useCallback } from 'react';
import { AdminSidebar } from './admin-sidebar';
import { AdminHeader } from './admin-header';

// ─── Heights matching main app ────────────────────────────────────────────────
export const BAR1_H = 40;   // dark top bar
export const BAR2_H = 28;   // dark sub-bar
export const BAR3_H = 36;   // white/dark content bar
export const TOTAL_H = BAR1_H + BAR2_H + BAR3_H; // 104px
export const BOTTOM_H = 28;

let _sidebarOpen: boolean | null = null;

function getInitialOpen(): boolean {
  if (typeof window === 'undefined') return false;
  return window.innerWidth >= 1280;
}

// ─── Bottom bar ───────────────────────────────────────────────────────────────
function BottomBar() {
  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-30 flex items-center justify-between px-4"
      style={{ height: `${BOTTOM_H}px`, backgroundColor: '#31465f', borderTop: '1px solid rgba(255,255,255,0.1)' }}
    >
      <div className="flex items-center gap-4">
        {['CloudShell', 'Feedback', 'Support'].map(label => (
          <button key={label} className="text-xs transition-colors" style={{ color: 'rgba(255,255,255,0.7)' }}
            onMouseEnter={e => { (e.currentTarget.style.color = '#fff'); (e.currentTarget.style.textDecoration = 'underline'); }}
            onMouseLeave={e => { (e.currentTarget.style.color = 'rgba(255,255,255,0.7)'); (e.currentTarget.style.textDecoration = 'none'); }}
          >{label}</button>
        ))}
      </div>
      <div className="flex items-center gap-3 text-xs" style={{ color: 'rgba(255,255,255,0.5)' }}>
        <span className="hidden lg:block">© 2026 CloudVisor Admin</span>
        {['Privacy', 'Terms'].map(item => (
          <button key={item} className="transition-colors" style={{ color: 'rgba(255,255,255,0.7)' }}
            onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
            onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
          >{item}</button>
        ))}
      </div>
    </div>
  );
}

// ─── AdminLayout ──────────────────────────────────────────────────────────────
export function AdminLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    if (_sidebarOpen !== null) return _sidebarOpen;
    const open = getInitialOpen();
    _sidebarOpen = open;
    return open;
  });

  const toggleSidebar = useCallback(() => {
    setSidebarOpen(prev => {
      const next = !prev;
      _sidebarOpen = next;
      return next;
    });
  }, []);

  const SIDEBAR_W = sidebarOpen ? 220 : 0;

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-base)' }}>
      {/* All 3 header bars */}
      <AdminHeader onSidebarToggle={toggleSidebar} sidebarOpen={sidebarOpen} />

      {/* Body: sidebar + content */}
      <div className="flex" style={{ minHeight: `calc(100vh - ${TOTAL_H}px - ${BOTTOM_H}px)` }}>
        {/* Sidebar — sticky, part of header */}
        {sidebarOpen && (
          <div
            className="flex-shrink-0"
            style={{
              width: '220px',
              position: 'sticky',
              top: `${TOTAL_H}px`,
              height: `calc(100vh - ${TOTAL_H}px - ${BOTTOM_H}px)`,
              overflowY: 'auto',
              zIndex: 20,
            }}
          >
            <AdminSidebar onClose={() => { setSidebarOpen(false); _sidebarOpen = false; }} />
          </div>
        )}

        {/* Main content */}
        <div className="flex flex-col flex-1 min-w-0" style={{ paddingBottom: `${BOTTOM_H}px` }}>
          <main className="flex-1 px-5 pt-4 pb-4">
            <div className="mx-auto w-full max-w-[1400px]">
              {children}
            </div>
          </main>
        </div>
      </div>

      <BottomBar />
    </div>
  );
}
