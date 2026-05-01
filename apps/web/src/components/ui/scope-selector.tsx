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
          backgroundColor: open ? 'rgba(255,255,255,0.15)' : 'transparent',
          color: 'rgba(255,255,255,0.95)',
          border: '1px solid rgba(255,255,255,0.25)',
          minWidth: '120px',
          maxWidth: '220px',
        }}
        onMouseEnter={e => { if (!open) (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'); }}
        onMouseLeave={e => { if (!open) (e.currentTarget.style.backgroundColor = 'transparent'); }}
      >
        <ProviderIcon provider={provider} />
        <span className="flex-1 truncate text-left">{label}</span>
        <ChevronDown
          className={`h-3 w-3 flex-shrink-0 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
          style={{ color: 'rgba(255,255,255,0.6)' }}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className="absolute right-0 top-full z-50 mt-1 rounded-lg overflow-hidden"
          style={{
            width: '300px',
            backgroundColor: '#1a2332',
            border: '1px solid rgba(255,255,255,0.15)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
          }}
        >
          {/* Header */}
          <div
            className="px-3 py-2 border-b"
            style={{ borderColor: 'var(--border-faint)', backgroundColor: 'var(--bg-elevated)' }}
          >
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
              Scope selector
            </span>
          </div>

          <div className="py-1 max-h-72 overflow-y-auto">
            {providers.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
                No cloud accounts connected yet.
              </div>
            ) : (
              providers.map(prov => {
                const provAccounts = byProvider.get(prov)!;
                return (
                  <React.Fragment key={prov}>
                    {/* Provider separator label */}
                    <div className="px-3 pt-2 pb-0.5 flex items-center gap-2">
                      <div className="h-px flex-1" style={{ backgroundColor: 'var(--border-faint)' }} />
                      <span className="text-xs font-semibold" style={{ color: 'var(--text-tertiary)' }}>
                        {PROVIDER_DISPLAY[prov]}
                      </span>
                      <div className="h-px flex-1" style={{ backgroundColor: 'var(--border-faint)' }} />
                    </div>

                    {/* Level 1 — Provider row (all accounts under this provider) */}
                    <button
                      onClick={() => { selectProvider(prov); setOpen(false); }}
                      className="flex w-full items-center gap-2.5 px-3 py-2 text-sm transition-colors"
                      style={{ backgroundColor: isProviderSelected(prov) ? 'var(--bg-elevated)' : 'transparent' }}
                      onMouseEnter={e => { if (!isProviderSelected(prov)) (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)'); }}
                      onMouseLeave={e => { if (!isProviderSelected(prov)) (e.currentTarget.style.backgroundColor = 'transparent'); }}
                    >
                      <ProviderIcon provider={prov} />
                      <div className="flex-1 text-left">
                        <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                          {PROVIDER_DISPLAY[prov]} (all accounts)
                        </span>
                        <span className="ml-1.5 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                          {provAccounts.length} account{provAccounts.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      {isProviderSelected(prov) && (
                        <Check className="h-3.5 w-3.5 flex-shrink-0" style={{ color: '#ec7211' }} />
                      )}
                    </button>

                    {/* Level 2 — Individual accounts */}
                    {provAccounts.map(acc => (
                      <button
                        key={acc.account_id}
                        onClick={() => { selectAccount(acc.account_id); setOpen(false); }}
                        className="flex w-full items-center gap-2.5 pl-8 pr-3 py-1.5 text-sm transition-colors"
                        style={{ backgroundColor: isAccountSelected(acc.account_id) ? 'var(--bg-elevated)' : 'transparent' }}
                        onMouseEnter={e => { if (!isAccountSelected(acc.account_id)) (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)'); }}
                        onMouseLeave={e => { if (!isAccountSelected(acc.account_id)) (e.currentTarget.style.backgroundColor = 'transparent'); }}
                      >
                        <div className="flex-1 text-left min-w-0">
                          <div className="truncate text-sm" style={{ color: 'var(--text-primary)' }}>
                            {acc.name || acc.account_id}
                          </div>
                          <div className="font-mono text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>
                            {acc.account_id}
                          </div>
                        </div>
                        {(acc.critical_count ?? 0) > 0 && (
                          <span
                            className="flex-shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
                            style={{ backgroundColor: 'var(--critical-bg)', color: 'var(--critical)', border: '1px solid var(--critical-border)' }}
                          >
                            {acc.critical_count}
                          </span>
                        )}
                        {isAccountSelected(acc.account_id) && (
                          <Check className="h-3.5 w-3.5 flex-shrink-0 ml-1" style={{ color: '#ec7211' }} />
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
