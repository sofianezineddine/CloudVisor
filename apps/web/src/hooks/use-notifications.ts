/**
 * React Query hooks for notification channel management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient, { NotificationChannel } from '@/lib/api/apiClient';

// ─── Query hooks ──────────────────────────────────────────────────────────────

export function useNotificationChannels() {
  return useQuery({
    queryKey: ['notifications', 'channels'],
    queryFn: () => apiClient.notifications.listChannels(),
    staleTime: 60_000, // 1 minute
  });
}

// ─── Mutation hooks ───────────────────────────────────────────────────────────

export function useCreateChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      name: string;
      channel_type: string;
      config: Record<string, unknown>;
      severity_filter?: string[];
      module_filter?: string[];
      account_filter?: string[];
      tag_filter?: Record<string, string>;
      is_active?: boolean;
    }) => apiClient.notifications.addChannel(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications', 'channels'] });
    },
  });
}

export function useUpdateChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      channelId,
      data,
    }: {
      channelId: string;
      data: {
        name?: string;
        config?: Record<string, unknown>;
        severity_filter?: string[];
        module_filter?: string[];
        account_filter?: string[];
        tag_filter?: Record<string, string>;
        is_active?: boolean;
      };
    }) => apiClient.notifications.updateChannel(channelId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications', 'channels'] });
    },
  });
}

export function useDeleteChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (channelId: string) => apiClient.notifications.removeChannel(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications', 'channels'] });
    },
  });
}

export function useTestChannel() {
  return useMutation({
    mutationFn: (data: {
      channel_id?: string;
      channel_type?: string;
      config?: Record<string, unknown>;
    }) => apiClient.notifications.testChannel(data),
  });
}
