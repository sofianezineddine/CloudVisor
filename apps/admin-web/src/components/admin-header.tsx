'use client';

import React from 'react';
import { useAdminAuth } from '@/hooks/use-admin-auth';
import {
  Bell, HelpCircle, Settings, LogOut, ChevronDown,
  Grid3x3, Search, Menu, Info, Sun, Moon, Shield,
} from 'lucide-react';
import { BAR1_H, BAR2_H, BAR3_H } from './admin-layout';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

// ─── Theme toggle ─────────────────────────────────────────────────────────────
function ThemeToggle() {
  const [dark, setDark] = React.useState(false);
  React.useEffect(() => {
    setDark(document.documentElement.getAttribute('data-theme') === 'dark');
  }, []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.setAttribute('data-theme', next ? 'dark' : 'light');
  };
  return (
    <button onClick={toggle} className="flex h-8 w-8 items-center justify-center transition-colors"
      style={{ color: 'rgba(255,255,255,0.8)' }}
      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)')}
      onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
      title={dark ? 'Light mode' : 'Dark mode'}
    >
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}

// ─── Nav icon button ──────────────────────────────────────────────────────────
function NavBtn({ icon: Icon, label, onClick }: { icon: React.ElementType; label: string; onClick?: () => void }) {
  return (
    <button className="flex h-8 w-8 items-center justify-center transition-colors flex-shrink-0"
      style={{ color: 'rgba(255,255,255,0.8)' }}
      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)')}
      onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
      title={label} onClick={onClick}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}

// ─── Breadcrumbs ──────────────────────────────────────────────────────────────
function Breadcrumbs({ pathname }: { pathname: string }) {
  // Build breadcrumb from pathname: /admin/dashboard → []  /admin/clients → [Admin, Clients]
  const parts = pathname.split('/').filter(Boolean); // ['admin', 'dashboard'] or ['admin', 'clients']
  if (parts.length <= 1) return null;

  const crumbs = parts.slice(1).map((part, i) => ({
    text: part.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    href: i < parts.length - 2 ? '/' + parts.slice(0, i + 2).join('/') : undefined,
  }));

  if (crumbs.length <= 1) return null; // Don't show on dashboard root

  return (
    <nav className="flex items-center gap-1 text-sm">
      <Link href="/admin/dashboard" className="transition-colors hover:underline" style={{ color: 'var(--text-link)' }}>
        Admin
      </Link>
      {crumbs.map((crumb, i) => (
        <React.Fragment key={i}>
          <span style={{ color: 'var(--text-tertiary)' }}>›</span>
          <span style={{ color: 'var(--text-primary)' }}>{crumb.text}</span>
        </React.Fragment>
      ))}
    </nav>
  );
}

// ─── AdminHeader ──────────────────────────────────────────────────────────────
export function AdminHeader({
  onSidebarToggle,
  sidebarOpen = false,
}: {
  onSidebarToggle?: () => void;
  sidebarOpen?: boolean;
}) {
  const { user, logout } = useAdminAuth();
  const pathname = usePathname();
  const [showUserMenu, setShowUserMenu] = React.useState(false);
  const [searchFocused, setSearchFocused] = React.useState(false);
  const userMenuRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) setShowUserMenu(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const userName = (user as any)?.name || (user as any)?.email || 'Admin';
  const userInitial = userName[0]?.toUpperCase() || 'A';

  // Pinned admin quick links for bar 2
  const quickLinks = [
    { label: 'Overview', href: '/admin/dashboard' },
    { label: 'Clients', href: '/admin/clients' },
    { label: 'Billing', href: '/admin/billing' },
    { label: 'Analytics', href: '/admin/analytics' },
  ];

  return (
    <>
      {/* ── BAR 1: dark top bar ──────────────────────────────────────────── */}
      <div
        className="sticky top-0 z-50 flex w-full items-center gap-1"
        style={{ height: `${BAR1_H}px`, backgroundColor: '#232f3e' }}
      >
        {/* Logo */}
        <Link href="/admin/dashboard"
          className="flex items-center h-full px-3 flex-shrink-0 transition-colors"
          onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)')}
          onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
        >
          <span className="text-sm font-bold tracking-tight select-none">
            <span style={{ color: '#ffffff' }}>Cloud</span>
            <span style={{ color: '#ff9900' }}>Visor</span>
            <span className="ml-1.5 text-[10px] font-semibold px-1.5 py-0.5 rounded" style={{ backgroundColor: 'rgba(255,153,0,0.2)', color: '#ff9900' }}>ADMIN</span>
          </span>
        </Link>

        {/* Grid icon */}
        <button
          className="flex h-full w-9 items-center justify-center flex-shrink-0 transition-colors"
          style={{ color: 'rgba(255,255,255,0.8)' }}
          onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)')}
          onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
        >
          <Grid3x3 className="h-4 w-4" />
        </button>

        {/* Search */}
        <div className="flex flex-1 items-center px-2">
          <div
            className="relative flex items-center w-full max-w-[400px]"
            style={{
              backgroundColor: searchFocused ? 'rgba(255,255,255,0.15)' : '#31465f',
              border: searchFocused ? '1px solid rgba(255,255,255,0.5)' : '1px solid transparent',
              borderRadius: '4px',
              height: '28px',
              transition: 'all 0.1s',
            }}
          >
            <Search className="absolute left-2 h-3.5 w-3.5" style={{ color: 'rgba(255,255,255,0.5)' }} />
            <input
              type="text"
              placeholder="Search clients, users..."
              className="w-full bg-transparent pl-7 pr-3 text-sm focus:outline-none"
              style={{ color: 'rgba(255,255,255,0.9)', height: '28px' }}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
            />
          </div>
        </div>

        {/* Right icons */}
        <div className="flex items-center flex-shrink-0 pr-1">
          <NavBtn icon={Bell} label="Notifications" />
          <NavBtn icon={HelpCircle} label="Help" />
          <NavBtn icon={Settings} label="Settings" />
          <ThemeToggle />

          {/* User dropdown */}
          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-1 px-2 h-8 text-xs transition-colors"
              style={{ color: '#ff9900', fontWeight: 600 }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
            >
              <span className="hidden sm:block truncate max-w-[140px]">{userName}</span>
              <ChevronDown className="h-3 w-3 flex-shrink-0" />
            </button>

            {showUserMenu && (
              <div className="absolute right-0 top-full z-50 w-56"
                style={{ backgroundColor: 'var(--bg-overlay)', border: '1px solid var(--border-default)', boxShadow: 'var(--shadow-popover)' }}
              >
                <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}>
                  <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Signed in as</div>
                  <div className="text-sm font-semibold mt-0.5" style={{ color: 'var(--text-primary)' }}>{userName}</div>
                </div>
                <div className="py-1">
                  <Link href="/admin/settings" onClick={() => setShowUserMenu(false)}
                    className="flex items-center gap-2.5 px-4 py-2 text-sm transition-colors"
                    style={{ color: 'var(--text-link)' }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <Settings className="h-3.5 w-3.5" style={{ color: 'var(--text-tertiary)' }} />
                    Admin Settings
                  </Link>
                </div>
                <div className="border-t py-1" style={{ borderColor: 'var(--border-faint)' }}>
                  <button onClick={() => { setShowUserMenu(false); logout(); }}
                    className="flex w-full items-center gap-2.5 px-4 py-2 text-sm transition-colors"
                    style={{ color: 'var(--text-link)' }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <LogOut className="h-3.5 w-3.5" style={{ color: 'var(--text-tertiary)' }} />
                    Sign out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── BAR 2: dark sub-bar with quick links ─────────────────────────── */}
      <div
        className="sticky z-40 flex w-full items-center gap-0.5 px-3"
        style={{ top: `${BAR1_H}px`, height: `${BAR2_H}px`, backgroundColor: '#31465f', borderBottom: '1px solid rgba(255,255,255,0.1)' }}
      >
        {quickLinks.map(item => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
          return (
            <Link key={item.href} href={item.href}
              className="flex items-center px-2 h-[22px] text-xs rounded transition-colors whitespace-nowrap"
              style={{
                color: isActive ? '#ffffff' : 'rgba(255,255,255,0.7)',
                backgroundColor: isActive ? 'rgba(255,255,255,0.15)' : 'transparent',
                fontWeight: isActive ? 600 : 400,
              }}
              onMouseEnter={e => { if (!isActive) { (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'); (e.currentTarget.style.color = '#ffffff'); } }}
              onMouseLeave={e => { if (!isActive) { (e.currentTarget.style.backgroundColor = 'transparent'); (e.currentTarget.style.color = 'rgba(255,255,255,0.7)'); } }}
            >
              {item.label}
            </Link>
          );
        })}
      </div>

      {/* ── BAR 3: white/dark bar with hamburger + breadcrumbs ───────────── */}
      <div
        className="sticky z-40 flex w-full items-center justify-between border-b px-2"
        style={{ top: `${BAR1_H + BAR2_H}px`, height: `${BAR3_H}px`, backgroundColor: 'var(--bar3-bg)', borderColor: 'var(--bar3-border)' }}
      >
        <div className="flex items-center gap-2">
          <button
            onClick={onSidebarToggle}
            className="flex h-7 w-7 items-center justify-center rounded transition-colors flex-shrink-0"
            style={{ color: 'var(--text-primary)' }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
            aria-label="Toggle sidebar"
          >
            <Menu className="h-4 w-4" />
          </button>
          <Breadcrumbs pathname={pathname} />
        </div>
        <button
          className="flex h-7 w-7 items-center justify-center rounded transition-colors"
          style={{ color: 'var(--text-tertiary)' }}
          onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
          onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
          title="Page information"
        >
          <Info className="h-4 w-4" />
        </button>
      </div>
    </>
  );
}
