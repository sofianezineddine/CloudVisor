'use client';

import * as React from 'react';
import {
  Search, Bell, HelpCircle, Settings, LogOut, User, Cloud,
  Users, KeyRound, ChevronDown, Terminal, Sun, Moon, Grid3x3,
  Menu, Info, ChevronRight, X, Globe, Check, Pin, PinOff,
} from 'lucide-react';
import { useAuth } from '@/hooks/use-auth';
import { useWebSocket } from '@/hooks/use-websocket';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { ScopeSelector } from '@/components/ui/scope-selector';
import { useScopeStore, isGlobalRoute } from '@/stores/scope';
import { useUserSettings } from '@/stores/user-settings';
import {
  SERVICE_CATEGORIES, ALL_SERVICES,
  loadPins, savePins, togglePin,
} from '@/lib/services-data';
import { useCloudVisorQStore } from '@/stores/cloudvisor-q';

// ─── Heights (exported so layout can use them) ────────────────────────────────
export const BAR1_H = 40;  // dark top bar
export const BAR2_H = 28;  // dark favorites bar
export const BAR3_H = 36;  // white/dark content bar (hamburger + breadcrumbs) - NOW PART OF CONTENT
export const STICKY_HEADER_H = BAR1_H + BAR2_H; // 68px - only bars 1 and 2 are sticky
export const TOTAL_HEADER_H = BAR1_H + BAR2_H + BAR3_H; // 104px - for calculations
export const BOTTOM_BAR_H = 28;

// ─── Sidebar toggle context ───────────────────────────────────────────────────
export const SidebarToggleContext = React.createContext<(() => void) | null>(null);

// ─── WebSocket indicator ──────────────────────────────────────────────────────
function LiveDot() {
  const { status } = useWebSocket();
  const color = status === 'connected' ? '#1db954' : status === 'reconnecting' ? '#ff9900' : '#d13212';
  return <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />;
}

// ─── Nav icon button ──────────────────────────────────────────────────────────
function NavBtn({ icon: Icon, label, href, onClick }: {
  icon: React.ElementType; label: string; href?: string; onClick?: () => void;
}) {
  const cls = "flex h-8 w-8 items-center justify-center transition-colors flex-shrink-0";
  const s = { color: '#ffffff' };
  const hIn = (e: React.MouseEvent) => (e.currentTarget as HTMLElement).style.backgroundColor = 'rgba(255,255,255,0.1)';
  const hOut = (e: React.MouseEvent) => (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
  if (href) return <Link href={href} className={cls} style={s} title={label} onMouseEnter={hIn} onMouseLeave={hOut}><Icon className="h-4 w-4" /></Link>;
  return <button className={cls} style={s} title={label} onClick={onClick} onMouseEnter={hIn} onMouseLeave={hOut}><Icon className="h-4 w-4" /></button>;
}

// ─── Services mega-menu ───────────────────────────────────────────────────────
function ServicesMegaMenu({ onClose, pins, onTogglePin }: {
  onClose: () => void;
  pins: string[];
  onTogglePin: (href: string) => void;
}) {
  const [activeCategory, setActiveCategory] = React.useState<string | null>(null);

  const displayedServices = activeCategory
    ? SERVICE_CATEGORIES.find(c => c.id === activeCategory)?.services ?? []
    : ALL_SERVICES.filter(s => pins.includes(s.href));

  const recentServices = ALL_SERVICES.slice(0, 8);

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div
        className="fixed left-0 z-50 flex"
        style={{
          top: `${BAR1_H}px`,
          width: '560px',
          maxHeight: `calc(100vh - ${BAR1_H}px)`,
          backgroundColor: '#1a2332',
          borderRight: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '4px 0 16px rgba(0,0,0,0.4)',
        }}
      >
        {/* Left column — categories */}
        <div
          className="w-[200px] flex-shrink-0 overflow-y-auto py-2"
          style={{ borderRight: '1px solid rgba(255,255,255,0.1)' }}
        >
          {/* Top links */}
          {[
            { label: 'Favorites', id: null },
            { label: 'All services', id: '__all__' },
          ].map(item => (
            <button
              key={item.label}
              onClick={() => {
                if (item.id === '__all__') { onClose(); window.location.href = '/services'; }
                else setActiveCategory(null);
              }}
              className="w-full px-3 py-1.5 text-left text-sm transition-colors"
              style={{
                color: activeCategory === item.id ? '#ffffff' : 'rgba(255,255,255,0.8)',
                backgroundColor: activeCategory === item.id ? 'rgba(255,255,255,0.12)' : 'transparent',
              }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = activeCategory === item.id ? 'rgba(255,255,255,0.12)' : 'transparent')}
            >
              {item.label}
            </button>
          ))}

          <div className="mx-3 my-2 h-px" style={{ backgroundColor: 'rgba(255,255,255,0.1)' }} />

          {/* Category list */}
          {SERVICE_CATEGORIES.map(cat => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className="w-full px-3 py-1.5 text-left text-sm transition-colors flex items-center gap-2"
              style={{
                color: activeCategory === cat.id ? '#ffffff' : 'rgba(255,255,255,0.8)',
                backgroundColor: activeCategory === cat.id ? 'rgba(255,255,255,0.12)' : 'transparent',
              }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = activeCategory === cat.id ? 'rgba(255,255,255,0.12)' : 'transparent')}
            >
              <span
                className="flex h-5 w-5 items-center justify-center rounded flex-shrink-0 text-[9px] font-bold"
                style={{ backgroundColor: cat.bg, color: cat.color }}
              >
                {cat.iconText}
              </span>
              <span className="truncate">{cat.label}</span>
            </button>
          ))}
        </div>

        {/* Right column — services */}
        <div className="flex-1 overflow-y-auto py-2">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="text-sm font-semibold text-white">
              {activeCategory
                ? SERVICE_CATEGORIES.find(c => c.id === activeCategory)?.label
                : 'Favorites'}
            </span>
            <button onClick={onClose} className="text-sm" style={{ color: 'rgba(255,255,255,0.6)' }}>✕</button>
          </div>

          {activeCategory === null && displayedServices.length === 0 && (
            <p className="px-4 py-3 text-xs" style={{ color: 'rgba(255,255,255,0.5)' }}>
              No pinned services yet. Hover over any service and click{' '}
              <Pin className="inline h-3 w-3" /> to pin it here.
            </p>
          )}

          {(activeCategory === null ? displayedServices : displayedServices).map(svc => {
            const isPinned = pins.includes(svc.href);
            return (
              <div
                key={svc.href}
                className="group flex items-start gap-2 px-4 py-2 transition-colors"
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                <Link
                  href={svc.href}
                  onClick={onClose}
                  className="flex-1 block"
                >
                  <div className="text-sm font-semibold" style={{ color: '#4db8ff' }}>{svc.name}</div>
                  <div className="text-xs" style={{ color: 'rgba(255,255,255,0.5)' }}>{svc.desc}</div>
                </Link>

                {/* Pin toggle */}
                <button
                  onClick={e => { e.stopPropagation(); onTogglePin(svc.href); }}
                  title={isPinned ? 'Unpin from nav bar' : 'Pin to nav bar'}
                  className="flex-shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '2px',
                    color: isPinned ? '#ff9900' : 'rgba(255,255,255,0.5)',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.color = isPinned ? '#eb5f07' : '#ffffff')}
                  onMouseLeave={e => (e.currentTarget.style.color = isPinned ? '#ff9900' : 'rgba(255,255,255,0.5)')}
                >
                  {isPinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
                </button>
              </div>
            );
          })}

          {/* Show recently visited when no category selected and no pins */}
          {activeCategory === null && displayedServices.length === 0 && (
            <>
              <div className="mx-4 my-2 h-px" style={{ backgroundColor: 'rgba(255,255,255,0.1)' }} />
              <div className="px-4 py-1 text-xs font-semibold uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.4)' }}>
                Recently visited
              </div>
              {recentServices.map(svc => (
                <Link
                  key={svc.href}
                  href={svc.href}
                  onClick={onClose}
                  className="block px-4 py-2 transition-colors"
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <div className="text-sm font-semibold" style={{ color: '#4db8ff' }}>{svc.name}</div>
                  <div className="text-xs" style={{ color: 'rgba(255,255,255,0.5)' }}>{svc.desc}</div>
                </Link>
              ))}
            </>
          )}
        </div>
      </div>
    </>
  );
}

// ─── Settings panel (language + theme) ───────────────────────────────────────
function SettingsPanel({ onClose }: { onClose: () => void }) {
  const storeTheme = useUserSettings(s => s.theme);
  const setStoreTheme = useUserSettings(s => s.setTheme);
  const [lang, setLang] = React.useState('browser');

  const applyTheme = (t: 'browser' | 'light' | 'dark') => {
    setStoreTheme(t);
  };

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div
        className="absolute right-0 top-full z-50 w-72 rounded shadow-2xl"
        style={{ backgroundColor: '#1a2332', border: '1px solid rgba(255,255,255,0.15)', marginTop: '2px' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
          <span className="text-sm font-semibold text-white">Current user settings</span>
          <button onClick={onClose} style={{ color: 'rgba(255,255,255,0.6)' }} onMouseEnter={e => (e.currentTarget.style.color = '#fff')} onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.6)')}>
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-4 space-y-5">
          {/* Language */}
          <div>
            <label className="block text-sm font-medium mb-2 text-white">Language</label>
            <select
              value={lang}
              onChange={e => setLang(e.target.value)}
              className="w-full rounded px-3 py-1.5 text-sm focus:outline-none"
              style={{ backgroundColor: '#243040', color: '#d5dbdb', border: '1px solid rgba(255,255,255,0.2)' }}
            >
              <option value="browser">Browser default</option>
              <option value="en">English</option>
              <option value="fr">Français</option>
              <option value="ar">العربية</option>
            </select>
          </div>

          {/* Visual mode */}
          <div>
            <div className="text-sm font-medium mb-2 text-white">
              Visual mode <span className="text-xs font-normal" style={{ color: 'rgba(255,255,255,0.5)' }}>- beta</span>
            </div>
            <div className="space-y-2">
              {(['browser', 'light', 'dark'] as const).map(opt => (
                <label key={opt} className="flex items-center gap-2.5 cursor-pointer">
                  <div
                    className="flex h-4 w-4 items-center justify-center rounded-full border-2 flex-shrink-0"
                    style={{ borderColor: storeTheme === opt ? '#ff9900' : 'rgba(255,255,255,0.4)', backgroundColor: storeTheme === opt ? '#ff9900' : 'transparent' }}
                    onClick={() => applyTheme(opt)}
                  >
                    {storeTheme === opt && <div className="h-1.5 w-1.5 rounded-full bg-white" />}
                  </div>
                  <span className="text-sm capitalize" style={{ color: '#d5dbdb' }} onClick={() => applyTheme(opt)}>
                    {opt === 'browser' ? 'Browser default' : opt.charAt(0).toUpperCase() + opt.slice(1)}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* See all settings link */}
          <button className="text-sm font-medium" style={{ color: '#4db8ff' }}
            onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
            onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
          >
            See all user settings
          </button>
        </div>
      </div>
    </>
  );
}

// ─── Breadcrumbs ──────────────────────────────────────────────────────────────
interface BreadcrumbItem { text: string; href?: string; }

function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  if (!items || items.length === 0) return null;
  return (
    <nav className="flex items-center gap-1" aria-label="Breadcrumb">
      {items.map((item, i) => (
        <React.Fragment key={i}>
          {i > 0 && <ChevronRight className="h-3 w-3 flex-shrink-0" style={{ color: 'var(--text-tertiary)' }} />}
          {item.href && i < items.length - 1 ? (
            <Link href={item.href} className="text-sm hover:underline" style={{ color: '#0972d3' }}>{item.text}</Link>
          ) : (
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{item.text}</span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}

// ─── Account loader — fetches connected accounts and populates scope store ────
// ─── Account loader — fetches connected accounts and populates scope store ────
// Module-level flag — persists across component remounts during navigation
let _accountsLoaded = false;

function useAccountLoader() {
  const setAccountsRef = React.useRef(useScopeStore.getState().setAccounts);
  const selectProviderRef = React.useRef(useScopeStore.getState().selectProvider);

  const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8005';

  React.useEffect(() => {
    if (_accountsLoaded) return;
    _accountsLoaded = true;

    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    // Fetch ALL connected accounts from connector (source of truth — includes GCP/Azure even if not scanned)
    // AND CSPM posture data for enrichment — in parallel
    Promise.allSettled([
      fetch(`${API_BASE}/v1/accounts`, { headers }).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/v1/cspm/posture/accounts`, { headers }).then(r => r.ok ? r.json() : null),
    ]).then(([accountsRes, cspmRes]) => {
      // Connector accounts — ALL providers regardless of scan status
      const accountsRaw = accountsRes.status === 'fulfilled' ? accountsRes.value : null;
      const connectorAccounts: any[] = accountsRaw?.data ?? accountsRaw?.accounts ?? [];

      // CSPM posture — for enrichment only (critical counts, posture scores)
      const cspmRaw = cspmRes.status === 'fulfilled' ? cspmRes.value : null;
      const cspmItems: any[] = cspmRaw?.data ?? cspmRaw ?? [];
      const cspmMap = new Map<string, any>();
      (Array.isArray(cspmItems) ? cspmItems : []).forEach((a: any) => cspmMap.set(a.account_id, a));

      let accounts: any[] = [];

      if (Array.isArray(connectorAccounts) && connectorAccounts.length > 0) {
        // Connector is source of truth — includes ALL providers
        accounts = connectorAccounts.map((a: any) => {
          const cspm = cspmMap.get(a.account_id) ?? {};
          return {
            account_id: a.account_id,
            provider: a.provider,
            name: a.name || a.account_id,
            critical_count: cspm.critical ?? 0,
            resource_count: a.resource_count ?? cspm.resource_count ?? 0,
            posture_score: cspm.posture_score ?? 0,
          };
        });
      } else if (Array.isArray(cspmItems) && cspmItems.length > 0) {
        // Fallback: use CSPM posture if connector returned nothing
        accounts = cspmItems.map((a: any) => ({
          account_id: a.account_id,
          provider: a.provider,
          name: a.account_id,
          critical_count: a.critical ?? 0,
          resource_count: a.resource_count ?? 0,
          posture_score: a.posture_score ?? 0,
        }));
      }

      if (accounts.length === 0) { _accountsLoaded = false; return; }

      // Sync refs before calling
      setAccountsRef.current = useScopeStore.getState().setAccounts;
      selectProviderRef.current = useScopeStore.getState().selectProvider;

      setAccountsRef.current(accounts);

      // Only auto-select if no valid scope is saved
      const savedScope = typeof window !== 'undefined'
        ? localStorage.getItem('cloudvisor-scope')
        : null;

      let hasSavedValidScope = false;
      if (savedScope) {
        try {
          const parsed = JSON.parse(savedScope);
          const savedIds: string[] = parsed?.accountIds ?? [];
          const allIds = accounts.map((a: any) => a.account_id);
          hasSavedValidScope = savedIds.length > 0 && savedIds.some((id: string) => allIds.includes(id));
        } catch {}
      }

      if (!hasSavedValidScope) {
        const providers = Array.from(new Set(accounts.map((a: any) => a.provider))).sort() as any[];
        if (providers.length > 0) selectProviderRef.current(providers[0]);
      }
    }).catch(() => { _accountsLoaded = false; });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

// ─── Main Header (bars 1 and 2 only - bar 3 moved to layout) ─────────────────
export function Header({
  onSidebarToggle,
  breadcrumbs,
  sidebarOpen = false,
}: {
  onSidebarToggle?: () => void;
  breadcrumbs?: BreadcrumbItem[];
  sidebarOpen?: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = React.useState(false);
  const [showMegaMenu, setShowMegaMenu] = React.useState(false);
  const [showSettings, setShowSettings] = React.useState(false);
  const [searchFocused, setSearchFocused] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [showSearchResults, setShowSearchResults] = React.useState(false);
  const [pins, setPins] = React.useState<string[]>([]);
  const userMenuRef = React.useRef<HTMLDivElement>(null);
  const settingsRef = React.useRef<HTMLDivElement>(null);
  const searchRef = React.useRef<HTMLDivElement>(null);

  const toggleQPanel = useCloudVisorQStore((state) => state.toggleOpen);

  // Filter services based on search query
  const filteredServices = React.useMemo(() => {
    if (!searchQuery.trim()) return [];
    const query = searchQuery.toLowerCase();
    return ALL_SERVICES.filter(service => 
      service.name.toLowerCase().includes(query) || 
      service.desc.toLowerCase().includes(query)
    ).slice(0, 10); // Limit to 10 results
  }, [searchQuery]);

  // Handle search input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    setShowSearchResults(value.trim().length > 0);
  };

  // Handle search result click
  const handleSearchResultClick = (href: string) => {
    setSearchQuery('');
    setShowSearchResults(false);
    router.push(href);
  };

  // Handle keyboard shortcut (Alt+S)
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
        const searchInput = document.querySelector('input[type="text"][placeholder="Search"]') as HTMLInputElement;
        if (searchInput) {
          searchInput.focus();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Load pins on mount and listen for changes from services page
  React.useEffect(() => {
    setPins(loadPins());
    const handler = () => setPins(loadPins());
    window.addEventListener('cloudvisor-pins-changed', handler);
    return () => window.removeEventListener('cloudvisor-pins-changed', handler);
  }, []);

  const handleTogglePin = (href: string) => {
    const next = togglePin(href, pins);
    setPins(next);
    savePins(next);
  };

  // Load connected accounts into scope store
  useAccountLoader();

  const isGlobal = isGlobalRoute(pathname);

  const handleLogout = async () => { setShowUserMenu(false); await logout(); router.push('/login'); };

  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) setShowUserMenu(false);
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) setShowSettings(false);
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setShowSearchResults(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const userName = user ? `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email || 'User' : 'User';
  const orgName = (user as any)?.organization_name || 'CloudVisor';

  // Bar 3 breadcrumbs: don't show "Console Home" on the console page itself
  const isConsole = pathname === '/console';

  // Pinned favorites — driven by user's saved pins
  const pinnedFavorites = pins
    .map(href => ALL_SERVICES.find(s => s.href === href))
    .filter(Boolean) as { name: string; href: string; desc: string }[];

  return (
    <>
      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* BAR 1 — dark #232f3e — logo, search, icons, account              */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      <div
        className="sticky top-0 z-50 flex w-full items-center gap-1 px-3 py-2"
        style={{ height: `${BAR1_H}px`, backgroundColor: '#131920', borderBottom: '1px solid rgba(255,255,255,0.2)' }}
      >
        {/* Logo: "Cloud" white + "Visor" orange, no icon */}
        <Link
          href="/console"
          className="flex items-center h-full px-2 flex-shrink-0 transition-colors rounded"
          onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)')}
          onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
        >
          <span className="text-sm font-bold tracking-tight select-none">
            <span style={{ color: '#ffffff' }}>Cloud</span>
            <span style={{ color: '#ff9900' }}>Visor</span>
          </span>
        </Link>

        {/* Grid / waffle icon */}
        <button
          onClick={() => setShowMegaMenu(v => !v)}
          className="flex h-8 w-8 items-center justify-center flex-shrink-0 transition-colors rounded"
          style={{ 
            color: '#ffffff', 
            backgroundColor: showMegaMenu ? 'rgba(255,255,255,0.1)' : 'transparent',
            border: '1px solid transparent'
          }}
          onMouseEnter={e => {
            e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)';
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.backgroundColor = showMegaMenu ? 'rgba(255,255,255,0.1)' : 'transparent';
            e.currentTarget.style.borderColor = 'transparent';
          }}
          title="Services"
        >
          <Grid3x3 className="h-4 w-4" />
        </button>

        {/* Search */}
        <div className="flex flex-1 items-center px-2 gap-2">
          <div
            ref={searchRef}
            className="relative flex items-center w-full max-w-[500px]"
            style={{
              backgroundColor: 'rgba(255,255,255,0.05)',
              border: searchFocused ? '1px solid #0972d3' : '1px solid rgba(255,255,255,0.15)',
              borderRadius: '20px',
              height: '32px',
              transition: 'all 0.15s',
            }}
          >
            <Search className="absolute left-3 h-4 w-4" style={{ color: 'rgba(255,255,255,0.5)' }} />
            <input
              type="text"
              placeholder="Search"
              value={searchQuery}
              onChange={handleSearchChange}
              className="w-full bg-transparent pl-10 pr-20 text-sm focus:outline-none placeholder:text-gray-500"
              style={{ color: '#ffffff', height: '100%' }}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setTimeout(() => setSearchFocused(false), 200)}
            />
            <span className="absolute right-3 text-xs hidden sm:block px-1.5 py-0.5 rounded" style={{ 
              color: 'rgba(255,255,255,0.5)',
              backgroundColor: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)'
            }}>[Alt+S]</span>
            
            {/* Search results dropdown */}
            {showSearchResults && filteredServices.length > 0 && (
              <div
                className="absolute left-0 top-full mt-1 w-full rounded shadow-lg overflow-hidden"
                style={{
                  backgroundColor: '#1a2332',
                  border: '1px solid rgba(255,255,255,0.15)',
                  maxHeight: '400px',
                  overflowY: 'auto',
                  zIndex: 100,
                }}
              >
                <div className="px-3 py-2 text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.5)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                  Services ({filteredServices.length})
                </div>
                {filteredServices.map((service) => (
                  <button
                    key={service.href}
                    onClick={() => handleSearchResultClick(service.href)}
                    className="w-full px-3 py-2 text-left transition-colors"
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <div className="text-sm font-semibold" style={{ color: '#4db8ff' }}>{service.name}</div>
                    <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.5)' }}>{service.desc}</div>
                  </button>
                ))}
              </div>
            )}
            
            {/* No results message */}
            {showSearchResults && searchQuery.trim() && filteredServices.length === 0 && (
              <div
                className="absolute left-0 top-full mt-1 w-full rounded shadow-lg"
                style={{
                  backgroundColor: '#1a2332',
                  border: '1px solid rgba(255,255,255,0.15)',
                  zIndex: 100,
                }}
              >
                <div className="px-3 py-4 text-center text-sm" style={{ color: 'rgba(255,255,255,0.5)' }}>
                  No services found for &quot;{searchQuery}&quot;
                </div>
              </div>
            )}
          </div>

          {/* Ask Q button */}
          <button
            onClick={toggleQPanel}
            className="flex items-center gap-1.5 px-2.5 h-[26px] text-xs flex-shrink-0 transition-colors"
            style={{ color: 'rgba(255,255,255,0.85)', border: '1px solid rgba(255,255,255,0.25)', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.05)', whiteSpace: 'nowrap' }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.12)')}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)')}
          >
            <span className="flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold" style={{ backgroundColor: '#ff9900', color: '#000' }}>Q</span>
            <span className="hidden md:block">Ask CloudVisor Q</span>
          </button>
        </div>

        {/* Right icons */}
        <div className="flex items-center flex-shrink-0 pr-1">
          <LiveDot />
          <NavBtn icon={Bell} label="Notifications" />
          <NavBtn icon={HelpCircle} label="Help" />

          {/* Settings — opens settings panel */}
          <div className="relative" ref={settingsRef}>
            <button
              onClick={() => setShowSettings(v => !v)}
              className="flex h-8 w-8 items-center justify-center transition-colors"
              style={{ color: showSettings ? '#ff9900' : '#ffffff' }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
              title="Settings"
            >
              <Settings className="h-4 w-4" />
            </button>
            {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
          </div>

          {/* Scope selector — hidden on global pages, shown on scope-aware pages */}
          {!isGlobal && (
            <div className="hidden md:flex items-center px-1">
              <ScopeSelector />
            </div>
          )}

          {/* Account */}
          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-0.5 px-2 h-8 text-xs transition-colors max-w-[200px]"
              style={{ color: '#ff9900', fontWeight: 600 }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
            >
              <span className="truncate hidden sm:block">{userName}</span>
              <ChevronDown className="h-3 w-3 flex-shrink-0" />
            </button>

            {showUserMenu && (
              <div className="absolute right-0 top-full z-50 w-64" style={{ backgroundColor: '#1a2332', border: '1px solid rgba(255,255,255,0.15)', boxShadow: '0 2px 8px rgba(0,0,0,0.4)' }}>
                <div className="px-4 py-3 border-b" style={{ borderColor: 'rgba(255,255,255,0.1)', backgroundColor: 'rgba(0,0,0,0.2)' }}>
                  <div className="text-xs" style={{ color: 'rgba(255,255,255,0.5)' }}>{orgName}</div>
                  <div className="text-sm font-semibold mt-0.5" style={{ color: '#ffffff' }}>{userName}</div>
                  {user?.email && <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.6)' }}>{user.email}</div>}
                </div>
                <div className="py-1">
                  {[
                    { label: 'Profile', href: '/profile', icon: User },
                    { label: 'Cloud accounts', href: '/settings', icon: Cloud },
                    { label: 'Team & access', href: '/settings/team', icon: Users },
                    { label: 'API keys', href: '/settings/api-keys', icon: KeyRound },
                  ].map(item => (
                    <Link key={item.href} href={item.href} onClick={() => setShowUserMenu(false)}
                      className="flex items-center gap-2.5 px-4 py-2 text-sm transition-colors" style={{ color: '#4db8ff' }}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <item.icon className="h-3.5 w-3.5 flex-shrink-0" style={{ color: 'rgba(255,255,255,0.5)' }} />
                      {item.label}
                    </Link>
                  ))}
                </div>
                <div className="border-t py-1" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                  <button onClick={handleLogout} className="flex w-full items-center gap-2.5 px-4 py-2 text-sm transition-colors" style={{ color: '#4db8ff' }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.08)')}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <LogOut className="h-3.5 w-3.5 flex-shrink-0" style={{ color: 'rgba(255,255,255,0.5)' }} />
                    Sign out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* BAR 2 — dark #31465f — pinned favorites (dynamic)               */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      <div
        className="sticky z-40 flex w-full items-center justify-between gap-1 px-3 py-2"
        style={{ top: `${BAR1_H}px`, height: `${BAR2_H}px`, backgroundColor: '#131920', borderBottom: '1px solid rgba(255,255,255,0.2)' }}
      >
        {/* Pinned service links */}
        <div className="flex items-center gap-0.5 overflow-x-auto flex-1" style={{ scrollbarWidth: 'none' }}>
          {pinnedFavorites.length === 0 && (
            <span className="text-xs px-2" style={{ color: '#ffffff' }}>
              No pinned services —
            </span>
          )}
          {pinnedFavorites.map(item => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.href}
                href={item.href}
                className="flex items-center px-2 h-[22px] text-xs rounded transition-colors whitespace-nowrap"
                style={{
                  color: '#ffffff',
                  backgroundColor: isActive ? 'rgba(255,255,255,0.15)' : 'transparent',
                  fontWeight: isActive ? 600 : 400,
                }}
                onMouseEnter={e => { if (!isActive) { (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'); } }}
                onMouseLeave={e => { if (!isActive) { (e.currentTarget.style.backgroundColor = 'transparent'); } }}
              >
                {item.name}
              </Link>
            );
          })}
        </div>

        {/* Edit pins shortcut */}
        <Link
          href="/services"
          className="flex-shrink-0 flex items-center gap-1 px-2 h-[22px] text-xs rounded transition-colors whitespace-nowrap"
          style={{ color: 'rgba(255,255,255,0.45)' }}
          title="Manage pinned services"
          onMouseEnter={e => { (e.currentTarget.style.color = '#ffffff'); }}
          onMouseLeave={e => { (e.currentTarget.style.color = 'rgba(255,255,255,0.45)'); }}
        >
          <Pin className="h-2.5 w-2.5" />
          <span className="hidden sm:block">Edit</span>
        </Link>
      </div>

      {/* Mega menu */}
      {showMegaMenu && (
        <ServicesMegaMenu
          onClose={() => setShowMegaMenu(false)}
          pins={pins}
          onTogglePin={handleTogglePin}
        />
      )}
    </>
  );
}

// ─── Bar 3 Component (exported for use in layout) ────────────────────────────
export function Bar3({
  onSidebarToggle,
  breadcrumbs,
}: {
  onSidebarToggle?: () => void;
  breadcrumbs?: BreadcrumbItem[];
}) {
  const pathname = usePathname();
  const isConsole = pathname === '/console';

  return (
    <div
      className="sticky flex w-full items-center justify-between border-b px-2 z-30"
      style={{ top: `${STICKY_HEADER_H}px`, height: `${BAR3_H}px`, backgroundColor: 'var(--bar3-bg)', borderColor: 'var(--bar3-border)' }}
    >
      <div className="flex items-center gap-0">
        {/* Hamburger — controls sidebar */}
        <button
          onClick={onSidebarToggle}
          className="flex h-8 w-8 items-center justify-center rounded transition-colors flex-shrink-0"
          style={{ color: 'var(--text-primary)' }}
          onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
          onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
          aria-label="Toggle sidebar"
        >
          <Menu className="h-4 w-4" />
        </button>

        {/* Breadcrumbs — only show when navigated to a sub-section (breadcrumbs.length > 1) */}
        {breadcrumbs && breadcrumbs.length > 1 && (
          <div className="ml-2">
            <Breadcrumbs items={breadcrumbs} />
          </div>
        )}
      </div>

      {/* Info icon */}
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
  );
}
