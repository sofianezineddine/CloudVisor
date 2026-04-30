/**
 * Scope hooks — convenience wrappers around the global scope store.
 * Import these in any component or hook that needs to be scope-aware.
 */

'use client';

import { useScopeStore, getScopeParam, type ConnectedAccount } from '@/stores/scope';
import { useShallow } from 'zustand/react/shallow';

/** Returns the current scope state (mode, label, accountIds) */
export function useScope() {
  return useScopeStore(
    useShallow(s => ({
      mode: s.mode,
      provider: s.provider,
      accountId: s.accountId,
      accountIds: s.accountIds,
      label: s.label,
      accounts: s.accounts,
    }))
  );
}

/** Returns the account_ids query param string (undefined = all accounts) */
export function useScopeParam(): string | undefined {
  const accountIds = useScopeStore(s => s.accountIds);
  return getScopeParam(accountIds);
}

/** Returns the resolved list of account IDs (empty = all) */
export function useScopeAccountIds(): string[] {
  return useScopeStore(s => s.accountIds);
}

/** Returns the human-readable scope label */
export function useScopeLabel(): string {
  return useScopeStore(s => s.label);
}

/** Returns all connected accounts */
export function useScopeAccounts(): ConnectedAccount[] {
  return useScopeStore(s => s.accounts);
}

/** Returns scope actions */
export function useScopeActions() {
  return useScopeStore(
    useShallow(s => ({
      setAccounts: s.setAccounts,
      selectProvider: s.selectProvider,
      selectAccount: s.selectAccount,
    }))
  );
}

/**
 * Returns query params object to spread into any API call.
 * Usage: apiClient.get('/findings', { params: { ...filters, ...scopeParams() } })
 */
export function useScopeQueryParams(): Record<string, string> {
  const accountIds = useScopeStore(s => s.accountIds);
  const param = getScopeParam(accountIds);
  return param ? { account_ids: param } : {};
}
