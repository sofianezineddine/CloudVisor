'use client';

/**
 * ScopeSelector — Global 2-level account scope dropdown.
 * Lives in the top nav bar on scope-aware pages only.
 *
 * Level 1: Provider (e.g. "AWS") — shows all accounts under that provider
 * Level 2: Single account (e.g. "AWS · Production (123456789012)")
 *
 * NO "All accounts" option — it does not exist.
 */

import * as React from 'react';
import { ChevronDown, Check } from 'lucide-react';
import { useScopeStore, PROVIDER_COLORS, PROVIDER_DISPLAY, type CloudProvider, type ConnectedAccount } from '@/stores/scope';
import { useShallow } from 'zustand/react/shallow';

function ProviderIcon({ provider, size = 14 }: { provider: CloudProvider; size?: number }) {
  return (
    <span
      className="inline-flex items-center justify-center rounded-sm flex-shrink-0 text-white font-bold"
      style={{
        width: size + 4,
        height: size + 4,
        backgroundColor: PROVIDER_COLORS[provider],
        fontSize: size * 0.6,
      }}
    >
      {PROVIDER_DISPLAY[provider][0]}
    </span>
  );
}

export function ScopeSelector() {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  const { mode, provider, accountId, label, accounts } = useScopeStore(
    useShallow(s => ({
      mode: s.mode,
      provider: s.provider,
      accountId: s.accountId,
      label: s.label,
      accounts: s.accounts,
    }))
  );
  const { selectProvider, selectAccount } = useScopeStore(
    useShallow(s => ({
      selectProvider: s.selectProvider,
      selectAccount: s.selectAccount,
    }))
  );

  // Close on outside click
  React.useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Group accounts by provider
  const byProvider = React.useMemo(() => {
    const map = new Map<CloudProvider, ConnectedAccount[]>();
    for (const acc of accounts) {
      if (!map.has(acc.provider)) map.set(acc.provider, []);
      map.get(acc.provider)!.push(acc);
    }
    return map;
  }, [accounts]);

  const providers = Array.from(byProvider.keys()).sort();

  const isProviderSelected = (p: CloudProvider) => mode === 'provider' && provider === p;
  const isAccountSelected = (id: string) => mode === 'account' && accountId === id;

  return (
    <div ref={ref} className="relative flex-shrink-0">
      {/* Trigger button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs font-medium transition-colors"
        style={{
          backgroundColor: open ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.05)',
          color: 'rgba(255,255,255,0.95)',
          border: '1px solid rgba(255,255,255,0.25)',
          minWidth: '120px',
          maxWidth: '220px',
        }}
        onMouseEnter={e => { if (!open) (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.12)'); }}
        onMouseLeave={e => { if (!open) (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'); }}
      >
        <ProviderIcon provider={provider} />
        <span className="flex-1 truncate text-left">{label}</span>
        <ChevronDown
          className={`h-3 w-3 flex-shrink-0 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
          style={{ color: 'rgba(255,255,255,0.8)' }}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className="absolute right-0 top-full z-50 mt-1 rounded-lg overflow-hidden scope-selector-dropdown"
          style={{
            width: '300px',
            backgroundColor: '#1a2332',
            border: '1px solid rgba(255,255,255,0.2)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          }}
        >
          {/* Header */}
          <div
            className="px-3 py-2 border-b"
            style={{ 
              borderColor: 'rgba(255,255,255,0.15)', 
              backgroundColor: '#1c2433',
              color: 'rgba(255,255,255,0.7)'
            }}
          >
            <span className="text-xs font-semibold uppercase tracking-wider">
              Scope selector
            </span>
          </div>

          <div className="py-1 max-h-72 overflow-y-auto">
            {providers.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm" style={{ color: 'rgba(255,255,255,0.6)' }}>
                No cloud accounts connected yet.
              </div>
            ) : (
              providers.map(prov => {
                const provAccounts = byProvider.get(prov)!;
                return (
                  <React.Fragment key={prov}>
                    {/* Provider separator label */}
                    <div className="px-3 pt-2 pb-0.5 flex items-center gap-2">
                      <div className="h-px flex-1" style={{ backgroundColor: 'rgba(255,255,255,0.15)' }} />
                      <span className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.6)' }}>
                        {PROVIDER_DISPLAY[prov]}
                      </span>
                      <div className="h-px flex-1" style={{ backgroundColor: 'rgba(255,255,255,0.15)' }} />
                    </div>

                    {/* Level 1 — Provider row (all accounts under this provider) */}
                    <button
                      onClick={() => { selectProvider(prov); setOpen(false); }}
                      className="flex w-full items-center gap-2.5 px-3 py-2 text-sm transition-colors"
                      style={{ backgroundColor: isProviderSelected(prov) ? '#1c2433' : 'transparent' }}
                      onMouseEnter={e => { if (!isProviderSelected(prov)) (e.currentTarget.style.backgroundColor = '#1c2433'); }}
                      onMouseLeave={e => { if (!isProviderSelected(prov)) (e.currentTarget.style.backgroundColor = 'transparent'); }}
                    >
                      <ProviderIcon provider={prov} />
                      <div className="flex-1 text-left">
                        <span className="font-medium" style={{ color: 'rgba(255,255,255,0.95)' }}>
                          {PROVIDER_DISPLAY[prov]} (all accounts)
                        </span>
                        <span className="ml-1.5 text-xs" style={{ color: 'rgba(255,255,255,0.6)' }}>
                          {provAccounts.length} account{provAccounts.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      {isProviderSelected(prov) && (
                        <Check className="h-3.5 w-3.5 flex-shrink-0" style={{ color: '#FF9900' }} />
                      )}
                    </button>

                    {/* Level 2 — Individual accounts */}
                    {provAccounts.map(acc => (
                      <button
                        key={acc.account_id}
                        onClick={() => { selectAccount(acc.account_id); setOpen(false); }}
                        className="flex w-full items-center gap-2.5 pl-8 pr-3 py-1.5 text-sm transition-colors"
                        style={{ backgroundColor: isAccountSelected(acc.account_id) ? '#1c2433' : 'transparent' }}
                        onMouseEnter={e => { if (!isAccountSelected(acc.account_id)) (e.currentTarget.style.backgroundColor = '#1c2433'); }}
                        onMouseLeave={e => { if (!isAccountSelected(acc.account_id)) (e.currentTarget.style.backgroundColor = 'transparent'); }}
                      >
                        <div className="flex-1 text-left min-w-0">
                          <div className="truncate text-sm flex items-center gap-1.5" style={{ color: 'rgba(255,255,255,0.95)' }}>
                            {acc.name || acc.account_id}
                            {acc.status === 'error' || acc.status === 'auth_failed' ? (
                              <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: '#d13212' }} title={acc.status} />
                            ) : acc.status === 'partial_sync' ? (
                              <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: '#ff9900' }} title="partial sync" />
                            ) : acc.status === 'active' ? (
                              <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: '#1a6b3c' }} title="active" />
                            ) : null}
                          </div>
                          <div className="font-mono text-xs truncate" style={{ color: 'rgba(255,255,255,0.7)' }}>
                            {acc.account_id}
                          </div>
                        </div>
                        {(acc.critical_count ?? 0) > 0 && (
                          <span
                            className="flex-shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
                            style={{ 
                              backgroundColor: 'rgba(209,50,18,0.2)', 
                              color: '#ff6b6b', 
                              border: '1px solid rgba(209,50,18,0.4)' 
                            }}
                          >
                            {acc.critical_count}
                          </span>
                        )}
                        {isAccountSelected(acc.account_id) && (
                          <Check className="h-3.5 w-3.5 flex-shrink-0 ml-1" style={{ color: '#FF9900' }} />
                        )}
                      </button>
                    ))}
                  </React.Fragment>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
