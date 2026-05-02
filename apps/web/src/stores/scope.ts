/**
 * Global Scope Store — Zustand + localStorage persist
 *
 * Two levels only (NO "All accounts"):
 *   'provider' → All accounts under one cloud provider (broadest scope)
 *   'account'  → Single specific cloud account (most specific)
 *
 * account_ids is ALWAYS populated — never empty on scope-aware pages.
 * Default on login: first connected provider alphabetically.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ScopeMode = 'provider' | 'account';
export type CloudProvider = 'aws' | 'azure' | 'gcp' | 'oci';

export interface ConnectedAccount {
  account_id: string;
  provider: CloudProvider;
  name?: string;
  status?: 'pending' | 'active' | 'error' | 'auth_failed' | 'partial_sync';
  critical_count?: number;
  resource_count?: number;
  posture_score?: number;
}

export interface ScopeState {
  mode: ScopeMode;
  provider: CloudProvider;           // always set — minimum scope is a provider
  accountId?: string;                // set only when mode === 'account'
  accountIds: string[];              // resolved list — always populated
  label: string;                     // "AWS" / "Azure" / "AWS · Production (123456789012)"
  accounts: ConnectedAccount[];      // all connected accounts
}

export interface ScopeActions {
  setAccounts: (accounts: ConnectedAccount[]) => void;
  selectProvider: (provider: CloudProvider) => void;
  selectAccount: (accountId: string) => void;
}

const DEFAULT_STATE: ScopeState = {
  mode: 'provider',
  provider: 'aws',
  accountId: undefined,
  accountIds: [],
  label: 'AWS',
  accounts: [],
};

const PROVIDER_LABELS: Record<CloudProvider, string> = {
  aws: 'AWS',
  azure: 'Azure',
  gcp: 'GCP',
  oci: 'OCI',
};

function buildLabel(
  mode: ScopeMode,
  provider: CloudProvider,
  accountId: string | undefined,
  accounts: ConnectedAccount[],
): string {
  if (mode === 'provider') return PROVIDER_LABELS[provider] ?? provider.toUpperCase();
  if (mode === 'account' && accountId) {
    const acc = accounts.find(a => a.account_id === accountId);
    const name = acc?.name || accountId;
    const prov = PROVIDER_LABELS[provider] ?? provider.toUpperCase();
    return `${prov} · ${name}`;
  }
  return PROVIDER_LABELS[provider] ?? provider.toUpperCase();
}

function resolveAccountIds(
  mode: ScopeMode,
  provider: CloudProvider,
  accountId: string | undefined,
  accounts: ConnectedAccount[],
): string[] {
  if (mode === 'provider') {
    return accounts.filter(a => a.provider === provider).map(a => a.account_id);
  }
  if (mode === 'account' && accountId) return [accountId];
  // Fallback: all accounts under provider
  return accounts.filter(a => a.provider === provider).map(a => a.account_id);
}

export const useScopeStore = create<ScopeState & ScopeActions>()(
  persist(
    (set, get) => ({
      ...DEFAULT_STATE,

      setAccounts: (accounts) => {
        const { accounts: existing, mode, provider, accountId } = get();

        // Skip if accounts list hasn't changed
        const existingIds = existing.map(a => a.account_id).sort().join(',');
        const newIds = accounts.map(a => a.account_id).sort().join(',');
        if (existingIds === newIds && existing.length === accounts.length) {
          // Accounts unchanged — but recompute accountIds in case they were empty
          const currentAccountIds = get().accountIds;
          if (currentAccountIds.length === 0 && accounts.length > 0) {
            const recomputedIds = resolveAccountIds(mode, provider, accountId, accounts);
            const recomputedLabel = buildLabel(mode, provider, accountId, accounts);
            if (recomputedIds.length > 0) {
              set({ accountIds: recomputedIds, label: recomputedLabel });
            }
          }
          return;
        }

        // Determine if we need to auto-select a default scope
        const currentAccountStillExists =
          accountId && accounts.some(a => a.account_id === accountId);
        const currentProviderHasAccounts =
          accounts.some(a => a.provider === provider);

        let newMode = mode;
        let newProvider = provider;
        let newAccountId = accountId;

        if (!currentProviderHasAccounts) {
          // Current provider no longer has accounts — reset to first available provider
          const providers = Array.from(new Set(accounts.map(a => a.provider))).sort() as CloudProvider[];
          if (providers.length > 0) {
            newProvider = providers[0];
            newMode = 'provider';
            newAccountId = undefined;
          }
        } else if (mode === 'account' && !currentAccountStillExists) {
          // Selected account no longer exists — fall back to provider level
          newMode = 'provider';
          newAccountId = undefined;
        }

        const accountIds = resolveAccountIds(newMode, newProvider, newAccountId, accounts);
        const label = buildLabel(newMode, newProvider, newAccountId, accounts);

        set({ accounts, mode: newMode, provider: newProvider, accountId: newAccountId, accountIds, label });
      },

      selectProvider: (provider) => {
        const { accounts } = get();
        const accountIds = resolveAccountIds('provider', provider, undefined, accounts);
        const label = buildLabel('provider', provider, undefined, accounts);
        set({ mode: 'provider', provider, accountId: undefined, accountIds, label });
      },

      selectAccount: (accountId) => {
        const { accounts } = get();
        const acc = accounts.find(a => a.account_id === accountId);
        const provider = acc?.provider ?? get().provider;
        const accountIds = resolveAccountIds('account', provider, accountId, accounts);
        const label = buildLabel('account', provider, accountId, accounts);
        set({ mode: 'account', provider, accountId, accountIds, label });
      },
    }),
    {
      name: 'cloudvisor-scope',
      partialize: (state) => ({
        mode: state.mode,
        provider: state.provider,
        accountId: state.accountId,
        accountIds: state.accountIds,
        label: state.label,
      }),
    },
  ),
);

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Returns account_ids as comma-separated string — always populated on scope-aware pages */
export function getScopeParam(accountIds: string[]): string {
  return accountIds.join(',');
}
export const GLOBAL_ROUTES = [
  '/settings',
  '/settings/api-keys',
  '/settings/billing',
  '/settings/notifications',
  '/settings/team',
  '/rules',
  '/services',
  '/profile',
  '/login',
  '/signup',
  '/forgot-password',
  '/admin',
];

export function isGlobalRoute(pathname: string): boolean {
  return GLOBAL_ROUTES.some(r => pathname === r || pathname.startsWith(r + '/'));
}

export const PROVIDER_COLORS: Record<CloudProvider, string> = {
  aws: '#f97316',
  azure: '#0078d4',
  gcp: '#1a73e8',
  oci: '#c74634',
};

export const PROVIDER_DISPLAY: Record<CloudProvider, string> = {
  aws: 'AWS',
  azure: 'Azure',
  gcp: 'GCP',
  oci: 'OCI',
};
