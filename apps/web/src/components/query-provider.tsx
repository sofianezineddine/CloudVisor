'use client';

import * as React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,    // 30 seconds
        gcTime: 300_000,      // 5 minutes
        retry: 1,
        refetchOnWindowFocus: false,
        // Don't throw query errors to the React error boundary — show them inline
        throwOnError: false,
      },
      mutations: {
        // Don't throw mutation errors to the React error boundary.
        // Each mutation caller is responsible for handling errors via onError
        // or by reading mutation.error. This prevents the Next.js dev overlay
        // from showing "Unhandled Runtime Error" for expected API failures.
        throwOnError: false,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient() {
  if (typeof window === 'undefined') {
    // Server: always make a new query client
    return makeQueryClient();
  }
  // Browser: reuse the same client across renders
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const queryClient = getQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
