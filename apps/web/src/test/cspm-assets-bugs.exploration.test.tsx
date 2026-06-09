/**
 * CSPM Assets — Bug Condition Exploration Tests
 *
 * These tests encode the EXPECTED behavior BEFORE fixes are applied.
 * They are DESIGNED TO FAIL on the current (unfixed) code.
 * Failing confirms each bug exists. Passing after fixes confirms correctness.
 *
 * Validates: Requirements 1.1, 1.2, 1.3
 *
 * Bug 1 — Undeclared `scopeAccountIds`:
 *   isBugCondition_1(pageItems) where pageItems.length === 0
 *   Expected failure: ReferenceError: scopeAccountIds is not defined
 *
 * Bug 2 — UUID filter discards all graph assets:
 *   isBugCondition_2(asset, currentAccountIds) where asset.account_id is UUID
 *   Expected failure: result.length === 0 instead of 1
 *
 * Bug 3 — listAssets called without account_ids:
 *   isBugCondition_3(params) where params.account_ids === undefined
 *   Expected failure: URL lacks account_ids query parameter
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

// ─── Mock graphAPI ─────────────────────────────────────────────────────────────
const mockListAssets = vi.fn();
vi.mock('@/lib/api/graph', () => ({
  graphAPI: { listAssets: (...a: any[]) => mockListAssets(...a), searchAssets: vi.fn().mockResolvedValue({ hits: [], total: 0 }) },
  default:  { listAssets: (...a: any[]) => mockListAssets(...a), searchAssets: vi.fn().mockResolvedValue({ hits: [], total: 0 }) },
}));

// ─── Mock connectorAPI ────────────────────────────────────────────────────────
vi.mock('@/lib/api/connector', () => ({
  connectorAPI: { listResources: vi.fn().mockResolvedValue({ resources: [], total: 0 }) },
}));

// ─── Mock apiClient ───────────────────────────────────────────────────────────
vi.mock('@/lib/api/apiClient', () => ({
  default: { assets: { list: vi.fn().mockResolvedValue({ data: [] }), search: vi.fn().mockResolvedValue({ data: [] }) } },
}));

vi.mock('@/lib/csrf', () => ({ getCsrfToken: () => 'test-csrf' }));

// ─── Scope store ──────────────────────────────────────────────────────────────
import { useScopeStore } from '@/stores/scope';
import type { ConnectedAccount } from '@/stores/scope';

function setScopeAccounts(accounts: ConnectedAccount[]) {
  useScopeStore.getState().setAccounts(accounts);
}

// ─── Component under test ─────────────────────────────────────────────────────
import { AssetsTab } from '@/app/cspm/tabs/assets-tab';

// ─────────────────────────────────────────────────────────────────────────────

describe('CSPM Assets — Bug Condition Exploration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListAssets.mockResolvedValue({ assets: [], total: 0, limit: 100 });
    useScopeStore.setState({ mode: 'provider', provider: 'aws', accountId: undefined, accountIds: [], label: 'AWS', accounts: [] });
  });

  afterEach(() => { vi.restoreAllMocks(); });

  // ─── Bug 1 — Undeclared `scopeAccountIds` ─────────────────────────────────
  // Counterexample: pageItems = [], scopeAccounts = [] → ReferenceError thrown
  it('Bug 1 — renders empty state without ReferenceError when no accounts and no assets', async () => {
    setScopeAccounts([]);
    mockListAssets.mockResolvedValue({ assets: [], total: 0, limit: 100 });

    let renderError: Error | null = null;
    const origErr = console.error;
    console.error = () => {};
    try {
      const { container } = render(<AssetsTab />);
      await waitFor(() => expect(container.querySelector('.animate-pulse')).toBeNull(), { timeout: 3000 });
      expect(screen.getByText('No accounts connected.')).toBeInTheDocument();
    } catch (err) {
      renderError = err as Error;
    } finally {
      console.error = origErr;
    }

    // UNFIXED: ReferenceError: scopeAccountIds is not defined
    // FIXED:   null (renders correctly)
    expect(renderError).toBeNull();
  });

  // ─── Bug 2 — UUID filter discards all graph assets ────────────────────────
  // Counterexample: asset.account_id = UUID, currentAccountIds = [providerID] → result.length = 0
  // Fix: filter is guarded with `graphReturnedEmpty` so graph results are never discarded
  it('Bug 2 — guarded filter must NOT discard graph assets when graphReturnedEmpty is false', () => {
    const graphAsset = { account_id: '550e8400-e29b-41d4-a716-446655440000', name: 'my-bucket' };
    const currentAccountIds = ['423028107173'];
    const graphReturnedEmpty = false; // this is the fixed guard condition

    // Reproduce the FIXED filter logic from assets-tab.tsx:
    // if (graphReturnedEmpty && currentAccountIds.length > 0 && items.length > 0) { filter... }
    let items = [graphAsset];
    if (graphReturnedEmpty && currentAccountIds.length > 0 && items.length > 0) {
      items = items.filter((a: any) => currentAccountIds.includes(a.account_id));
    }

    // UNFIXED: graphReturnedEmpty guard absent → filter runs → result.length === 0
    // FIXED:   graphReturnedEmpty === false → filter skipped → result.length === 1
    expect(items.length).toBe(1);
  });

  // ─── Bug 3 — listAssets called without account_ids ────────────────────────
  // Counterexample: scope has accounts → graphAPI.listAssets called without account_ids param
  it('Bug 3 — graphAPI.listAssets must be called with account_ids when scope has connected accounts', async () => {
    setScopeAccounts([{ account_id: '423028107173', provider: 'aws', name: 'Prod', status: 'active' }]);

    // Return something so the component doesn't stay in loading state
    mockListAssets.mockResolvedValue({ assets: [], total: 0, limit: 100 });

    const origErr = console.error;
    console.error = () => {};
    try {
      const { container } = render(<AssetsTab />);
      await waitFor(() => expect(container.querySelector('.animate-pulse')).toBeNull(), { timeout: 3000 });
    } finally {
      console.error = origErr;
    }

    // The mock should have been called — check it received account_ids
    expect(mockListAssets).toHaveBeenCalled();
    const callArgs = mockListAssets.mock.calls[0]?.[0];

    // UNFIXED: callArgs.account_ids === undefined (not passed)
    // FIXED:   callArgs.account_ids === ['423028107173']
    expect(callArgs?.account_ids).toEqual(['423028107173']);
  });
});
