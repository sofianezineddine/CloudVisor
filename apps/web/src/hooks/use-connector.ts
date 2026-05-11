'use client';

/**
 * React Query hooks for the Connector service.
 *
 * All hooks are scope-aware — they automatically filter by the current
 * provider/account selection from the global scope store.
 *
 * Use these instead of calling connectorAPI directly in components.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { connectorAPI, CloudAccount, CreateAccountRequest, UpdateAccountRequest, CloudAccountCredentials } from '@/lib/api/connector';
import apiClient from '@/lib/api/apiClient';
import { useScopeStore } from '@/stores/scope';

// ─── Query key factory ────────────────────────────────────────────────────────

export const connectorKeys = {
  all:      () => ['connector'] as const,
  accounts: () => [...connectorKeys.all(), 'accounts'] as const,
  account:  (id: string) => [...connectorKeys.accounts(), id] as const,
  health:   (id: string) => [...connectorKeys.accounts(), id, 'health'] as const,
  syncStatus: (id: string) => [...connectorKeys.accounts(), id, 'sync-status'] as const,
  scanHistory: (id: string, params?: Record<string, unknown>) => [...connectorKeys.accounts(), id, 'scans', params] as const,
  resources: () => [...connectorKeys.all(), 'resources'] as const,
  resourcesList: (params: Record<string, unknown>) => [...connectorKeys.resources(), 'list', params] as const,
  resourcesSummary: (params: Record<string, unknown>) => [...connectorKeys.resources(), 'summary', params] as const,
  resourceCatalog: () => [...connectorKeys.resources(), 'catalog'] as const,
  onboarding: (provider: string) => [...connectorKeys.all(), 'onboarding', provider] as const,
};

// ─── Account hooks ────────────────────────────────────────────────────────────

/**
 * List all cloud accounts for the authenticated organization.
 * Automatically refreshes every 30 seconds to pick up sync status changes.
 */
export function useCloudAccounts() {
  return useQuery({
    queryKey: connectorKeys.accounts(),
    // Use gateway /v1/accounts instead of connector directly
    queryFn: async () => {
      try {
        const resp = await apiClient.accounts.list({ limit: 200 });
        const accounts = (resp?.data as any[]) ?? [];
        return { accounts, total: accounts.length };
      } catch {
        // Fallback to connector direct if gateway unavailable
        return connectorAPI.listAccounts();
      }
    },
    staleTime: 15_000,
    refetchInterval: 30_000,
    select: (data) => data.accounts ?? [],
  });
}

/**
 * Get a single cloud account by ID.
 */
export function useCloudAccount(accountId: string | null) {
  return useQuery({
    queryKey: connectorKeys.account(accountId ?? ''),
    queryFn: () => connectorAPI.getAccount(accountId!),
    enabled: !!accountId,
    staleTime: 15_000,
  });
}

/**
 * Get detailed health metrics for a cloud account.
 */
export function useAccountHealth(accountId: string | null) {
  return useQuery({
    queryKey: connectorKeys.health(accountId ?? ''),
    queryFn: () => connectorAPI.getAccountHealth(accountId!),
    enabled: !!accountId,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

// ─── Resource hooks ───────────────────────────────────────────────────────────

/**
 * List discovered resources, scoped to the current provider/account selection.
 */
export function useCloudResources(params?: {
  resource_type?: string;
  region?: string;
  search?: string;
  is_public?: boolean;
  environment?: string;
  limit?: number;
  offset?: number;
}) {
  const accountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const provider = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
  const accountIds = useScopeStore(s => s.accountIds);

  const effectiveParams = {
    ...params,
    account_id: accountId,
    provider: !accountId ? provider : undefined,
  };

  return useQuery({
    queryKey: connectorKeys.resourcesList({ ...effectiveParams, _scope: accountIds }),
    queryFn: () => connectorAPI.listResources(effectiveParams),
    staleTime: 30_000,
    enabled: accountIds.length > 0,
    select: (data) => data.resources ?? [],
  });
}

/**
 * Get resource count summary grouped by provider and type.
 */
export function useResourcesSummary() {
  const accountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  const provider = useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
  const accountIds = useScopeStore(s => s.accountIds);

  return useQuery({
    queryKey: connectorKeys.resourcesSummary({ accountId, provider, _scope: accountIds }),
    queryFn: () => connectorAPI.getResourcesSummary(accountId, provider),
    staleTime: 60_000,
    enabled: accountIds.length > 0,
  });
}

// ─── Onboarding hooks ─────────────────────────────────────────────────────────

/**
 * Fetch onboarding instructions/template for a provider.
 * Cached indefinitely — instructions don't change.
 */
export function useOnboardingInstructions(provider: string | null) {
  return useQuery({
    queryKey: connectorKeys.onboarding(provider ?? ''),
    queryFn: async () => {
      if (!provider) return null;
      switch (provider) {
        case 'aws':   return connectorAPI.getAwsTemplate();
        case 'azure': return connectorAPI.getAzureInstructions();
        case 'gcp':   return connectorAPI.getGcpInstructions();
        case 'oci':   return connectorAPI.getOciInstructions();
        default:      return null;
      }
    },
    enabled: !!provider,
    staleTime: Infinity,
    gcTime: Infinity,
  });
}

// ─── Mutation hooks ───────────────────────────────────────────────────────────

/**
 * Connect a new cloud account.
 * On success: invalidates account list + updates scope store.
 */
export function useConnectAccount() {
  const queryClient = useQueryClient();
  const setAccounts = useScopeStore(s => s.setAccounts);

  return useMutation({
    // Use gateway /v1/accounts instead of connector directly
    mutationFn: (data: CreateAccountRequest) => apiClient.accounts.create(data as any),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: connectorKeys.accounts() });
      try {
        const resp = await apiClient.accounts.list({ limit: 200 });
        const accounts = ((resp?.data as any[]) ?? []).map((a: any) => ({
          account_id: a.account_id,
          provider: a.provider,
          name: a.name || a.account_id,
          status: a.status,
          critical_count: 0,
          resource_count: a.resource_count ?? 0,
          posture_score: 0,
        }));
        if (accounts.length > 0) setAccounts(accounts);
      } catch {
        // Non-fatal
      }
    },
  });
}

/**
 * Update cloud account configuration (name, region, polling interval).
 */
export function useUpdateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateAccountRequest }) =>
      connectorAPI.updateAccount(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: connectorKeys.accounts() });
      queryClient.invalidateQueries({ queryKey: connectorKeys.account(id) });
    },
  });
}

/**
 * Delete a cloud account.
 * On success: invalidates account list + updates scope store.
 */
export function useDeleteAccount() {
  const queryClient = useQueryClient();
  const setAccounts = useScopeStore(s => s.setAccounts);

  return useMutation({
    // Use gateway /v1/accounts/{id} instead of connector directly
    mutationFn: (accountId: string) => apiClient.accounts.delete(accountId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: connectorKeys.accounts() });
      try {
        const resp = await apiClient.accounts.list({ limit: 200 });
        const accounts = ((resp?.data as any[]) ?? []).map((a: any) => ({
          account_id: a.account_id,
          provider: a.provider,
          name: a.name || a.account_id,
          status: a.status,
          critical_count: 0,
          resource_count: a.resource_count ?? 0,
          posture_score: 0,
        }));
        setAccounts(accounts);
      } catch {
        // Non-fatal
      }
    },
  });
}

/**
 * Trigger an immediate on-demand sync for an account.
 */
export function useTriggerAccountSync() {
  const queryClient = useQueryClient();
  return useMutation({
    // Use gateway /v1/accounts/{id}/scan instead of connector directly
    mutationFn: ({ accountId }: { accountId: string; correlationId?: string }) =>
      apiClient.accounts.triggerScan(accountId),
    onSuccess: (_, { accountId }) => {
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: connectorKeys.account(accountId) });
        queryClient.invalidateQueries({ queryKey: connectorKeys.accounts() });
      }, 2000);
    },
  });
}


// ─── Sync Status hook ─────────────────────────────────────────────────────────

/**
 * Poll live sync progress for an account.
 * Refetches every 3 seconds while a sync is in progress, stops when idle.
 * Used by the "Run scan" button to show live progress in a Flashbar.
 */
export function useSyncStatus(accountId: string | null, enabled = false) {
  return useQuery({
    queryKey: connectorKeys.syncStatus(accountId ?? ''),
    queryFn: () => connectorAPI.getSyncStatus(accountId!),
    enabled: !!accountId && enabled,
    staleTime: 2_000,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Keep polling while a sync is running
      if (data?.current_sync?.status === 'running') return 3_000;
      return false; // Stop polling when idle/completed
    },
  });
}

// ─── Scan History hook ────────────────────────────────────────────────────────

/**
 * Fetch paginated scan history for an account.
 */
export function useScanHistory(accountId: string | null, params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: connectorKeys.scanHistory(accountId ?? '', params),
    queryFn: () => connectorAPI.getScanHistory(accountId!, params),
    enabled: !!accountId,
    staleTime: 30_000,
  });
}

// ─── Credential Rotation hook ─────────────────────────────────────────────────

/**
 * Rotate credentials for an existing cloud account.
 * On success: invalidates account queries so the UI reflects the new status.
 */
export function useRotateCredentials() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, credentials }: { accountId: string; credentials: CloudAccountCredentials }) =>
      connectorAPI.rotateCredentials(accountId, credentials),
    onSuccess: (_, { accountId }) => {
      queryClient.invalidateQueries({ queryKey: connectorKeys.account(accountId) });
      queryClient.invalidateQueries({ queryKey: connectorKeys.health(accountId) });
      queryClient.invalidateQueries({ queryKey: connectorKeys.accounts() });
    },
  });
}

// ─── Resource Type Catalog hook ───────────────────────────────────────────────

/**
 * Fetch the complete resource type catalog (all supported types per provider).
 * Cached indefinitely — the catalog doesn't change at runtime.
 * Used to populate resource-type filter dropdowns in the asset explorer.
 */
export function useResourceTypeCatalog() {
  return useQuery({
    queryKey: connectorKeys.resourceCatalog(),
    queryFn: () => connectorAPI.getResourceTypeCatalog(),
    staleTime: Infinity,
    gcTime: Infinity,
  });
}
