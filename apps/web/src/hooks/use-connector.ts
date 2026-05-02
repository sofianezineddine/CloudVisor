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
import { connectorAPI, CloudAccount, CreateAccountRequest, UpdateAccountRequest } from '@/lib/api/connector';
import { useScopeStore } from '@/stores/scope';

// ─── Query key factory ────────────────────────────────────────────────────────

export const connectorKeys = {
  all:      () => ['connector'] as const,
  accounts: () => [...connectorKeys.all(), 'accounts'] as const,
  account:  (id: string) => [...connectorKeys.accounts(), id] as const,
  health:   (id: string) => [...connectorKeys.accounts(), id, 'health'] as const,
  resources: () => [...connectorKeys.all(), 'resources'] as const,
  resourcesList: (params: Record<string, unknown>) => [...connectorKeys.resources(), 'list', params] as const,
  resourcesSummary: (params: Record<string, unknown>) => [...connectorKeys.resources(), 'summary', params] as const,
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
    queryFn: () => connectorAPI.listAccounts(),
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
    mutationFn: (data: CreateAccountRequest) => connectorAPI.createAccount(data),
    onSuccess: async () => {
      // Invalidate account list so it refetches
      await queryClient.invalidateQueries({ queryKey: connectorKeys.accounts() });

      // Refresh scope store with updated account list
      try {
        const result = await connectorAPI.listAccounts();
        const accounts = (result.accounts ?? []).map((a: CloudAccount) => ({
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
        // Non-fatal — scope store will update on next header render
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
    mutationFn: (accountId: string) => connectorAPI.deleteAccount(accountId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: connectorKeys.accounts() });

      // Refresh scope store
      try {
        const result = await connectorAPI.listAccounts();
        const accounts = (result.accounts ?? []).map((a: CloudAccount) => ({
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
    mutationFn: ({ accountId, correlationId }: { accountId: string; correlationId?: string }) =>
      connectorAPI.triggerSync(accountId, correlationId),
    onSuccess: (_, { accountId }) => {
      // Refetch account status after a short delay to pick up sync_status change
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: connectorKeys.account(accountId) });
        queryClient.invalidateQueries({ queryKey: connectorKeys.accounts() });
      }, 2000);
    },
  });
}
