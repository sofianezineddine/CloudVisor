"use client";

/**
 * CloudVisor shim for Keep's useHydratedSession hook.
 *
 * Uses the non-HttpOnly cv_session cookie to determine if the user is authenticated.
 * The actual JWT token is in an HttpOnly cookie (inaccessible to JS).
 * User metadata is stored in localStorage (non-sensitive display data only).
 */

import { hasSessionCookie, getCookie } from '@/lib/csrf';

export function useHydratedSession() {
  // Auth check via cv_session cookie only — tokens are HttpOnly and never in localStorage (C-01 fix)
  const isAuthenticated = hasSessionCookie();

  const getUser = () => {
    if (typeof window === 'undefined') return null;
    try {
      const stored = localStorage.getItem('cloudvisor-user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  };

  const user = getUser();

  // Return a session-like object compatible with Keep UI expectations
  const session = isAuthenticated ? {
    user: {
      id: user?.id || 'cloudvisor-user',
      name: user?.name || 'CloudVisor User',
      email: user?.email || 'user@cloudvisor.io',
      image: user?.image || null,
      accessToken: 'cookie-based', // Placeholder — actual token is HttpOnly
      tenantId: user?.organization_id || 'default',
      role: user?.role || 'admin',
    },
    accessToken: 'cookie-based', // Keep UI checks this exists, but value doesn't matter
    tenantId: user?.organization_id || 'default',
    userRole: user?.role || 'admin',
  } : null;

  return {
    data: session,
    status: isAuthenticated ? 'authenticated' as const : 'unauthenticated' as const,
    update: async () => session,
  };
}
